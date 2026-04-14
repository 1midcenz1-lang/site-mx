import os
import sqlite3
import uuid
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
RECEIPTS_DIR = os.path.join(UPLOAD_DIR, "receipts")
VIDEOS_DIR = os.path.join(UPLOAD_DIR, "videos")
SAMPLES_DIR = os.path.join(UPLOAD_DIR, "samples")

PAYMENT_TEXT_IRANI = (
    "کانال ایرانی دارای 100 فیلم با کیفیت میباشد\n\n"
    "هزینه عضویت کانال ایرانی 100 هزارتومن میباشد، حق عضویت رو به شماره کارت پایین واریز کنید\n\n"
    "6063731090274433\n"
    "معین . اب\n\n"
    "فیش واریزی رو به صورت عکس فیش اینجا ارسال کنید و منتظر تایید بمانید ( چند دقیقه تا چند ساعت طول میکشه )"
)

PAYMENT_TEXT_KHAREJI = (
    "کانال خارجی دارای 100 فیلم با کیفیت میباشد\n\n"
    "هزینه عضویت کانال خارجی 100 هزارتومن میباشد، حق عضویت رو به شماره کارت پایین واریز کنید\n\n"
    "6063731090274433\n"
    "معین . اب\n\n"
    "فیش واریزی رو به صورت عکس فیش اینجا ارسال کنید و منتظر تایید بمانید ( چند دقیقه تا چند ساعت طول میکشه )"
)

CLIENT_WAITING_REVIEW_TEXT = (
    "درحال بررسی پرداختت هستیم «چند ساعت» طول میکشه لطفا تا اتمام این فرایند هیچ پیامی ارسال نکنید\n\n"
    "ربات پیام ها رو سین میکنه و جواب میده لطفا بعد از ارسال فیش، منتظر ادمین بمونید تا در اولین فرصت فیلم ها رو ارسال کنه، بعضی وقت ها این فرایند چند ساعت طول میکشه\n\n"
    "ساعت 2 شب تا 10 صبح فیلم ارسال نمیشه لطفا صبور باشید ( ربات پیام ها رو سین میکنه )"
)

CLIENT_APPROVED_TEXT = (
    "مرسی که خرید کردید.\n"
    "عضویت شما تایید شد و دسترسی دسته انتخابی فعال شد.\n\n"
    "اگر دوباره خواستید خریدی بکنید برای فعال سازی باید دقیقا کلمه دوباره رو ارسال کنید"
)

ALLOWED_RECEIPT_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_ARCHIVE_EXTENSIONS = {"zip"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-now")
app.config["ADMIN_USER"] = os.environ.get("ADMIN_USER", "admin")
app.config["ADMIN_PASS"] = os.environ.get("ADMIN_PASS", "mx9091")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1GB


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="mx-watch")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA synchronous=NORMAL")
        g.db.execute("PRAGMA temp_store=MEMORY")
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(SAMPLES_DIR, exist_ok=True)

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            device_id TEXT NOT NULL,
            is_banned INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            payment_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS purchase_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            requested_category_id INTEGER NOT NULL,
            receipt_path TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            admin_note TEXT,
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (requested_category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS user_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            source_request_id INTEGER,
            UNIQUE(user_id, category_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (source_request_id) REFERENCES purchase_requests(id)
        );

        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            source_type TEXT NOT NULL,
            file_path TEXT,
            external_url TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL UNIQUE,
            username TEXT,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            visit_count INTEGER NOT NULL DEFAULT 0,
            purchase_count INTEGER NOT NULL DEFAULT 0,
            report_count INTEGER NOT NULL DEFAULT 0,
            is_banned INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            reporter_name TEXT,
            report_type TEXT NOT NULL,
            report_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS category_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            device_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(category_id, device_id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );
        """
    )

    user_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(users)").fetchall()]
    if "is_banned" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0")
    visitor_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(visitors)").fetchall()]
    if "username" not in visitor_cols:
        cursor.execute("ALTER TABLE visitors ADD COLUMN username TEXT")
    report_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(reports)").fetchall()]
    if "reporter_name" not in report_cols:
        cursor.execute("ALTER TABLE reports ADD COLUMN reporter_name TEXT")

    db.commit()
    db.close()


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def register_visit(device_id: str, db=None):
    if not device_id:
        return
    local_db = db or get_db()
    existing = local_db.execute(
        "SELECT id, visit_count FROM visitors WHERE device_id=?",
        (device_id,),
    ).fetchone()
    if existing:
        local_db.execute(
            "UPDATE visitors SET last_seen_at=?, visit_count=visit_count+1 WHERE id=?",
            (now_iso(), existing["id"]),
        )
    else:
        local_db.execute(
            """
            INSERT INTO visitors(device_id, username, first_seen_at, last_seen_at, visit_count)
            VALUES(?,?,?,?,?)
            """,
            (device_id, None, now_iso(), now_iso(), 1),
        )
    local_db.commit()


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged"):
            return redirect(url_for("admin_login"))
        return func(*args, **kwargs)

    return wrapper


@app.route("/")
def home():
    db = get_db()
    categories = db.execute("SELECT * FROM categories ORDER BY id").fetchall()
    return render_template("home.html", categories=categories)


@app.route("/samples/<slug>")
def sample_archive(slug):
    candidates = [
        os.path.join(SAMPLES_DIR, f"{slug}_nemone.zip"),
        os.path.join(SAMPLES_DIR, f"{slug}_sample.zip"),
        os.path.join(BASE_DIR, f"{slug}_nemone.zip"),
    ]
    path = next((item for item in candidates if os.path.exists(item)), None)
    if not path:
        abort(404)
    return send_file(path, as_attachment=True)


@app.post("/api/register-visit")
def api_register_visit():
    payload = request.get_json(silent=True) or {}
    device_id = (payload.get("device_id") or "").strip()
    if not device_id:
        return jsonify({"ok": False, "message": "شناسه دستگاه لازم است."}), 400

    register_visit(device_id)
    visitor = get_db().execute(
        "SELECT is_banned FROM visitors WHERE device_id=?",
        (device_id,),
    ).fetchone()
    if visitor and visitor["is_banned"]:
        return jsonify({"ok": False, "message": "این دستگاه مسدود شده است."}), 403
    return jsonify({"ok": True})


@app.route("/buy/<slug>")
def buy_page(slug):
    db = get_db()
    category = db.execute("SELECT * FROM categories WHERE slug=?", (slug,)).fetchone()
    if not category:
        abort(404)
    return render_template("buy.html", category=category)


@app.post("/api/submit-request")
def submit_request():
    device_id = request.form.get("device_id", "").strip()
    category_id = request.form.get("category_id", "").strip()
    receipt = request.files.get("receipt")

    if not device_id or not category_id:
        return jsonify({"ok": False, "message": "شناسه دستگاه و فیش الزامی هستند."}), 400

    db = get_db()
    register_visit(device_id, db=db)
    category = db.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()
    if not category:
        return jsonify({"ok": False, "message": "دسته‌بندی نامعتبر است."}), 400

    visitor = db.execute("SELECT * FROM visitors WHERE device_id=?", (device_id,)).fetchone()
    if visitor and visitor["is_banned"]:
        return jsonify({"ok": False, "message": "این دستگاه توسط ادمین مسدود شده است."}), 403

    user = db.execute("SELECT * FROM users WHERE device_id=?", (device_id,)).fetchone()

    if user is None:
        alias = device_id.replace("-", "")[:12] or uuid.uuid4().hex[:12]
        full_name = f"user-{alias}"
        pseudo_phone = f"device-{alias}"
        db.execute(
            "INSERT INTO users(full_name,phone,device_id,created_at,updated_at) VALUES(?,?,?,?,?)",
            (full_name, pseudo_phone, device_id, now_iso(), now_iso()),
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE device_id=?", (device_id,)).fetchone()
    else:
        if user["is_banned"]:
            return jsonify({"ok": False, "message": "این دستگاه توسط ادمین مسدود شده است."}), 403
        db.execute(
            "UPDATE users SET updated_at=? WHERE id=?",
            (now_iso(), user["id"]),
        )

    pending_request = db.execute(
        """
        SELECT id FROM purchase_requests
        WHERE user_id=? AND status='pending'
        ORDER BY id DESC LIMIT 1
        """,
        (user["id"],),
    ).fetchone()
    if pending_request:
        return jsonify(
            {
                "ok": True,
                "message": CLIENT_WAITING_REVIEW_TEXT,
                "next_url": "/my-videos",
                "pending_exists": True,
            }
        )

    if not receipt:
        return jsonify({"ok": False, "message": "فیش الزامی است."}), 400

    if not allowed_file(receipt.filename, ALLOWED_RECEIPT_EXTENSIONS):
        return jsonify({"ok": False, "message": "فرمت عکس فیش معتبر نیست."}), 400

    receipt_name = secure_filename(receipt.filename)
    final_name = f"{uuid.uuid4().hex}_{receipt_name}"
    final_path = os.path.join(RECEIPTS_DIR, final_name)
    receipt.save(final_path)

    db.execute(
        """
        INSERT INTO purchase_requests(
            user_id,requested_category_id,receipt_path,status,created_at
        ) VALUES(?,?,?,?,?)
        """,
        (user["id"], category["id"], final_name, "pending", now_iso()),
    )
    db.execute(
        "UPDATE visitors SET purchase_count=purchase_count+1, last_seen_at=? WHERE device_id=?",
        (now_iso(), device_id),
    )
    db.commit()

    return jsonify(
        {
            "ok": True,
            "message": CLIENT_WAITING_REVIEW_TEXT,
            "next_url": "/my-videos",
        }
    )


@app.get("/api/purchase-status")
def purchase_status():
    device_id = request.args.get("device_id", "").strip()
    if not device_id:
        return jsonify({"ok": False, "message": "شناسه دستگاه لازم است."}), 400

    db = get_db()
    user = db.execute("SELECT id FROM users WHERE device_id=?", (device_id,)).fetchone()
    if not user:
        return jsonify({"ok": True, "has_pending": False})

    pending = db.execute(
        "SELECT id FROM purchase_requests WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
        (user["id"],),
    ).fetchone()
    return jsonify({"ok": True, "has_pending": bool(pending), "message": CLIENT_WAITING_REVIEW_TEXT})


@app.route("/my-videos")
def my_videos_page():
    return render_template("my_videos.html")


@app.get("/api/my-videos")
def api_my_videos():
    device_id = request.args.get("device_id", "").strip()

    if not device_id:
        return jsonify({"ok": False, "message": "شناسه دستگاه لازم است."}), 400

    db = get_db()
    register_visit(device_id, db=db)
    visitor = db.execute("SELECT * FROM visitors WHERE device_id=?", (device_id,)).fetchone()
    if visitor and visitor["is_banned"]:
        return jsonify({"ok": False, "message": "این دستگاه مسدود شده است."}), 403
    user = db.execute("SELECT * FROM users WHERE device_id=? ORDER BY id DESC", (device_id,)).fetchone()
    if not user:
        return jsonify({"ok": False, "message": "برای این دستگاه خریدی ثبت نشده است."}), 404
    if user["is_banned"]:
        return jsonify({"ok": False, "message": "این دستگاه مسدود شده است."}), 403

    rows = db.execute(
        """
        SELECT c.id as category_id, c.title as category_title, c.slug,
               v.id as video_id, v.title as video_title, v.source_type, v.external_url
        FROM user_access ua
        JOIN categories c ON c.id = ua.category_id
        LEFT JOIN videos v ON v.category_id = c.id
        WHERE ua.user_id = ?
        ORDER BY c.id, v.id
        """,
        (user["id"],),
    ).fetchall()

    grouped = {}
    for row in rows:
        key = row["category_id"]
        if key not in grouped:
            grouped[key] = {
                "id": row["category_id"],
                "title": row["category_title"],
                "slug": row["slug"],
                "videos": [],
            }
        if row["video_id"]:
            token = _serializer().dumps(
                {
                    "uid": user["id"],
                    "vid": row["video_id"],
                    "did": device_id,
                }
            )
            grouped[key]["videos"].append(
                {
                    "id": row["video_id"],
                    "title": row["video_title"],
                    "watch_url": url_for("watch_video", token=token),
                    "type": row["source_type"],
                }
            )

    return jsonify(
        {
            "ok": True,
            "approved_text": CLIENT_APPROVED_TEXT,
            "categories": list(grouped.values()),
        }
    )


@app.get("/watch/<token>")
def watch_video(token):
    device_id = request.args.get("device_id", "").strip()
    if not device_id:
        abort(403)

    try:
        payload = _serializer().loads(token, max_age=7200)
    except BadSignature:
        abort(403)

    if payload.get("did") != device_id:
        abort(403)

    db = get_db()
    row = db.execute(
        """
        SELECT v.*, ua.user_id
        FROM videos v
        JOIN user_access ua ON ua.category_id = v.category_id
        WHERE v.id = ? AND ua.user_id = ?
        """,
        (payload.get("vid"), payload.get("uid")),
    ).fetchone()

    if not row:
        abort(404)

    if row["source_type"] == "url":
        return redirect(row["external_url"])

    if not row["file_path"]:
        abort(404)

    full_path = os.path.join(VIDEOS_DIR, row["file_path"])
    if not os.path.exists(full_path):
        abort(404)
    return send_file(full_path, as_attachment=True)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == app.config["ADMIN_USER"] and password == app.config["ADMIN_PASS"]:
            session["admin_logged"] = True
            return redirect(url_for("admin_dashboard"))

        flash("نام کاربری یا رمز اشتباه است.")

    return render_template("admin_login.html")


@app.route("/admin/logout")
@app.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    requests_rows = db.execute(
        """
        SELECT pr.*, u.device_id, c.title as requested_category
        FROM purchase_requests pr
        JOIN users u ON u.id = pr.user_id
        JOIN categories c ON c.id = pr.requested_category_id
        ORDER BY pr.id DESC
        """
    ).fetchall()

    categories = db.execute("SELECT * FROM categories ORDER BY id").fetchall()
    videos = db.execute(
        """
        SELECT v.*, c.title as category_title
        FROM videos v
        JOIN categories c ON c.id = v.category_id
        ORDER BY v.id DESC
        """
    ).fetchall()

    reports = db.execute(
        "SELECT * FROM reports ORDER BY id DESC LIMIT 300"
    ).fetchall()
    visitors = db.execute(
        "SELECT * FROM visitors ORDER BY last_seen_at DESC LIMIT 500"
    ).fetchall()
    stats = {
        "total_visitors": db.execute("SELECT COUNT(*) AS c FROM visitors").fetchone()["c"],
        "total_purchases": db.execute("SELECT COUNT(*) AS c FROM purchase_requests").fetchone()["c"],
        "total_reports": db.execute("SELECT COUNT(*) AS c FROM reports").fetchone()["c"],
    }

    return render_template(
        "admin_dashboard.html",
        requests_rows=requests_rows,
        categories=categories,
        videos=videos,
        reports=reports,
        visitors=visitors,
        stats=stats,
    )


@app.post("/admin/api/requests/<int:request_id>/approve")
@admin_required
def admin_approve_request(request_id):
    category_ids = request.form.getlist("category_ids")
    if not category_ids:
        return jsonify({"ok": False, "message": "حداقل یک دسته انتخاب کنید."}), 400

    db = get_db()
    req = db.execute("SELECT * FROM purchase_requests WHERE id=?", (request_id,)).fetchone()
    if not req:
        return jsonify({"ok": False, "message": "درخواست پیدا نشد."}), 404

    for cat_id in category_ids:
        db.execute(
            """
            INSERT OR IGNORE INTO user_access(user_id, category_id, created_at, source_request_id)
            VALUES(?,?,?,?)
            """,
            (req["user_id"], int(cat_id), now_iso(), request_id),
        )

    db.execute(
        "UPDATE purchase_requests SET status='approved', reviewed_at=? WHERE id=?",
        (now_iso(), request_id),
    )
    db.commit()
    return jsonify({"ok": True})


@app.post("/admin/api/requests/<int:request_id>/reject")
@admin_required
def admin_reject_request(request_id):
    db = get_db()
    req = db.execute("SELECT * FROM purchase_requests WHERE id=?", (request_id,)).fetchone()
    if not req:
        return jsonify({"ok": False, "message": "درخواست پیدا نشد."}), 404

    db.execute(
        "UPDATE purchase_requests SET status='rejected', reviewed_at=? WHERE id=?",
        (now_iso(), request_id),
    )
    db.commit()
    return jsonify({"ok": True})


@app.post("/api/report")
def submit_report():
    report_type = request.form.get("report_type", "").strip()
    report_text = request.form.get("report_text", "").strip()
    device_id = request.form.get("device_id", "").strip()
    allowed_types = {"مستحجن", "کلاهبرداری"}

    if report_type not in allowed_types or not report_text or not device_id:
        return jsonify({"ok": False, "message": "اطلاعات ریپورت کامل نیست."}), 400

    db = get_db()
    register_visit(device_id, db=db)
    visitor = db.execute("SELECT * FROM visitors WHERE device_id=?", (device_id,)).fetchone()
    if visitor and visitor["is_banned"]:
        return jsonify({"ok": False, "message": "این دستگاه مسدود شده است."}), 403

    db.execute(
        "INSERT INTO reports(device_id, reporter_name, report_type, report_text, created_at) VALUES(?,?,?,?,?)",
        (device_id, None, report_type, report_text, now_iso()),
    )
    db.execute(
        "UPDATE visitors SET report_count=report_count+1, last_seen_at=? WHERE device_id=?",
        (now_iso(), device_id),
    )
    db.commit()
    return jsonify({"ok": True, "message": "ریپورت ثبت شد و برای ادمین ارسال شد."})


@app.get("/api/category-likes")
def category_likes():
    device_id = request.args.get("device_id", "").strip()
    db = get_db()
    counts = db.execute(
        """
        SELECT category_id, COUNT(*) AS c
        FROM category_likes
        GROUP BY category_id
        """
    ).fetchall()

    liked = []
    if device_id:
        liked_rows = db.execute(
            "SELECT category_id FROM category_likes WHERE device_id=?",
            (device_id,),
        ).fetchall()
        liked = [row["category_id"] for row in liked_rows]

    return jsonify(
        {
            "ok": True,
            "counts": {str(row["category_id"]): row["c"] for row in counts},
            "liked": liked,
        }
    )


@app.post("/api/category-likes/toggle")
def toggle_category_like():
    payload = request.get_json(silent=True) or {}
    device_id = (payload.get("device_id") or "").strip()
    category_id = payload.get("category_id")

    if not device_id or not category_id:
        return jsonify({"ok": False, "message": "شناسه دستگاه و دسته لازم است."}), 400

    db = get_db()
    category = db.execute("SELECT id FROM categories WHERE id=?", (category_id,)).fetchone()
    if not category:
        return jsonify({"ok": False, "message": "دسته پیدا نشد."}), 404

    existing = db.execute(
        "SELECT id FROM category_likes WHERE category_id=? AND device_id=?",
        (category_id, device_id),
    ).fetchone()

    if existing:
        db.execute("DELETE FROM category_likes WHERE id=?", (existing["id"],))
        liked = False
    else:
        db.execute(
            "INSERT INTO category_likes(category_id, device_id, created_at) VALUES(?,?,?)",
            (category_id, device_id, now_iso()),
        )
        liked = True

    db.commit()
    count = db.execute(
        "SELECT COUNT(*) AS c FROM category_likes WHERE category_id=?",
        (category_id,),
    ).fetchone()["c"]
    return jsonify({"ok": True, "liked": liked, "count": count})


@app.post("/admin/api/categories")
@admin_required
def admin_create_category():
    title = request.form.get("title", "").strip()
    slug = request.form.get("slug", "").strip().lower()
    payment_text = request.form.get("payment_text", "").strip()

    if not title or not slug or not payment_text:
        return jsonify({"ok": False, "message": "همه فیلدها الزامی هستند."}), 400

    db = get_db()
    exists = db.execute("SELECT id FROM categories WHERE slug=?", (slug,)).fetchone()
    if exists:
        return jsonify({"ok": False, "message": "slug تکراری است."}), 400

    db.execute(
        "INSERT INTO categories(slug,title,payment_text,created_at) VALUES(?,?,?,?)",
        (slug, title, payment_text, now_iso()),
    )
    db.commit()
    return jsonify({"ok": True})


@app.post("/admin/api/categories/<int:category_id>/delete")
@admin_required
def admin_delete_category(category_id):
    db = get_db()
    cat = db.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()
    if not cat:
        return jsonify({"ok": False, "message": "دسته پیدا نشد."}), 404

    video_files = db.execute(
        "SELECT file_path FROM videos WHERE category_id=? AND file_path IS NOT NULL",
        (category_id,),
    ).fetchall()
    for row in video_files:
        full = os.path.join(VIDEOS_DIR, row["file_path"])
        if os.path.exists(full):
            try:
                os.remove(full)
            except OSError:
                pass

    db.execute("DELETE FROM videos WHERE category_id=?", (category_id,))
    db.execute("DELETE FROM user_access WHERE category_id=?", (category_id,))
    db.execute("DELETE FROM purchase_requests WHERE requested_category_id=?", (category_id,))
    db.execute("DELETE FROM categories WHERE id=?", (category_id,))
    db.commit()
    return jsonify({"ok": True})


@app.post("/admin/api/videos")
@admin_required
def admin_create_video():
    category_id = request.form.get("category_id", "").strip()
    title = request.form.get("title", "").strip()
    external_url = request.form.get("external_url", "").strip()
    video_file = request.files.get("video_file")

    if not category_id or not title:
        return jsonify({"ok": False, "message": "دسته و عنوان لازم است."}), 400

    source_type = None
    file_path = None

    if video_file and video_file.filename:
        if not allowed_file(video_file.filename, ALLOWED_ARCHIVE_EXTENSIONS):
            return jsonify({"ok": False, "message": "فقط فایل zip معتبر است."}), 400
        filename = secure_filename(video_file.filename)
        final_name = f"{uuid.uuid4().hex}_{filename}"
        final_path = os.path.join(VIDEOS_DIR, final_name)
        video_file.save(final_path)
        source_type = "file"
        file_path = final_name
    elif external_url:
        source_type = "url"
    else:
        return jsonify({"ok": False, "message": "یا فایل zip بده یا لینک."}), 400

    db = get_db()
    cat = db.execute("SELECT id FROM categories WHERE id=?", (category_id,)).fetchone()
    if not cat:
        return jsonify({"ok": False, "message": "دسته پیدا نشد."}), 404

    db.execute(
        """
        INSERT INTO videos(category_id,title,source_type,file_path,external_url,created_at)
        VALUES(?,?,?,?,?,?)
        """,
        (category_id, title, source_type, file_path, external_url or None, now_iso()),
    )
    db.commit()
    return jsonify({"ok": True})


@app.post("/admin/api/visitors/<int:visitor_id>/ban")
@admin_required
def admin_ban_visitor(visitor_id):
    db = get_db()
    visitor = db.execute("SELECT * FROM visitors WHERE id=?", (visitor_id,)).fetchone()
    if not visitor:
        return jsonify({"ok": False, "message": "کاربر پیدا نشد."}), 404

    db.execute("UPDATE visitors SET is_banned=1 WHERE id=?", (visitor_id,))
    db.execute("UPDATE users SET is_banned=1 WHERE device_id=?", (visitor["device_id"],))
    db.commit()
    return jsonify({"ok": True})


@app.post("/admin/api/visitors/<int:visitor_id>/unban")
@admin_required
def admin_unban_visitor(visitor_id):
    db = get_db()
    visitor = db.execute("SELECT * FROM visitors WHERE id=?", (visitor_id,)).fetchone()
    if not visitor:
        return jsonify({"ok": False, "message": "کاربر پیدا نشد."}), 404

    db.execute("UPDATE visitors SET is_banned=0 WHERE id=?", (visitor_id,))
    db.execute("UPDATE users SET is_banned=0 WHERE device_id=?", (visitor["device_id"],))
    db.commit()
    return jsonify({"ok": True})


@app.post("/admin/api/device-ban")
@admin_required
def admin_ban_by_device():
    device_id = request.form.get("device_id", "").strip()
    if not device_id:
        return jsonify({"ok": False, "message": "شناسه دستگاه لازم است."}), 400

    db = get_db()
    db.execute("UPDATE visitors SET is_banned=1 WHERE device_id=?", (device_id,))
    db.execute("UPDATE users SET is_banned=1 WHERE device_id=?", (device_id,))
    db.commit()
    return jsonify({"ok": True})


@app.get("/admin/receipt/<filename>")
@admin_required
def admin_view_receipt(filename):
    full = os.path.join(RECEIPTS_DIR, filename)
    if not os.path.exists(full):
        abort(404)
    return send_file(full)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
