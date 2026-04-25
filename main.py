import os
import re
import secrets
import sqlite3
import string
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from functools import wraps

from flask import (
    Flask,
    abort,
    flash,
    g,
    has_app_context,
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
    "مرسى كه خريد كرديد.\n"
    "توجه كنيد خريد شما در اينجا فقط با همين دستگاه قابل نمايشه اگر دسته بندى براى شما فعال نشده لطفا تا تاييد ادمين صبر كنيد\n"
    "توجه كنيد درصورتى كه فيش فيك ارسال كنيد وضعيتتون ثابت ميمونه و ممكن است بن بشيد.\n"
    "اكر دوباره خواستيد خريدى بكنيد ميتونيد مجدد دريافت ويديو رو بزنيد و دسته بندى ديكرى را بخريد."
)

ALLOWED_RECEIPT_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_ARCHIVE_EXTENSIONS = {"zip"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-now")
app.config["ADMIN_USER"] = os.environ.get("ADMIN_USER", "admin")
app.config["ADMIN_PASS"] = os.environ.get("ADMIN_PASS", "mx9091")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024 * 1024  # 10GB


TEHRAN_TZ = ZoneInfo("Asia/Tehran")
ONLINE_SECONDS = 120
DOWNLOAD_ACTIVE_SECONDS = 180
DEFAULT_SITE_UPDATE_MODE = False
DEFAULT_SITE_DOMAIN_MOVE_MODE = False
DEFAULT_SITE_DOMAIN_MOVE_TARGET = "https://mxdomain.liara.run"
DEFAULT_UTC_ADJUST_HOURS = 4
DEFAULT_MAX_DEVICES_PER_USER = 2


def tehran_now_iso() -> str:
    return datetime.now(TEHRAN_TZ).isoformat()


def format_tehran(iso_value: str | None) -> str:
    if not iso_value:
        return "-"
    try:
        dt = datetime.fromisoformat(iso_value)
    except Exception:
        return iso_value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    adjusted = dt.astimezone(TEHRAN_TZ) - timedelta(hours=get_utc_adjust_hours())
    return adjusted.strftime("%Y-%m-%d %H:%M:%S")

def to_tehran_adjusted(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(TEHRAN_TZ) - timedelta(hours=get_utc_adjust_hours())

def tehran_day_range_utc_iso(offset_days: int = 0) -> tuple[str, str]:
    now_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))

    # 👇 دقیقاً همون منطق format_tehran
    now_adj = to_tehran_adjusted(now_utc) + timedelta(days=offset_days)

    day_start_adj = now_adj.replace(hour=0, minute=0, second=0, microsecond=0)
    next_day_adj = day_start_adj + timedelta(days=1)

    # برگردوندن به UTC واقعی
    adjust_hours = get_utc_adjust_hours()
    start_utc = (day_start_adj + timedelta(hours=adjust_hours)).astimezone(ZoneInfo("UTC"))
    end_utc = (next_day_adj + timedelta(hours=adjust_hours)).astimezone(ZoneInfo("UTC"))

    return start_utc.replace(tzinfo=None).isoformat(), end_utc.replace(tzinfo=None).isoformat()


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="mx-watch")


def _read_setting_from_db(key: str):
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def get_setting(key: str, default_value: str) -> str:
    if has_app_context():
        db = g.get("db")
        if db is not None:
            row = db.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
            return row["value"] if row else default_value
    db_value = _read_setting_from_db(key)
    return db_value if db_value is not None else default_value


def setting_bool(key: str, default_value: bool = False) -> bool:
    return get_setting(key, "1" if default_value else "0") == "1"


def setting_int(key: str, default_value: int) -> int:
    raw = get_setting(key, str(default_value))
    try:
        return int(raw)
    except Exception:
        return default_value


def get_utc_adjust_hours() -> int:
    return setting_int("utc_adjust_hours", DEFAULT_UTC_ADJUST_HOURS)


def generate_access_code(length: int = 16) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_mongo_client():
    if "mongo_client" in app.extensions:
        return app.extensions["mongo_client"]
    uri = os.environ.get("MONGO_URI", "mongodb://mg:mani2244@195.177.255.54:27017/")
    db_name = os.environ.get("MONGO_DB_NAME", "site_mx")
    try:
        pymongo_mod = __import__("pymongo")
        client = pymongo_mod.MongoClient(uri, serverSelectionTimeoutMS=1500)
        app.extensions["mongo_client"] = client
        app.extensions["mongo_db_name"] = db_name
        return client
    except Exception:
        app.extensions["mongo_client"] = None
        return None


def mongo_upsert(collection_name: str, filter_doc: dict, update_doc: dict):
    client = get_mongo_client()
    if not client:
        return
    try:
        db_name = app.extensions.get("mongo_db_name", "site_mx")
        client[db_name][collection_name].update_one(filter_doc, {"$set": update_doc}, upsert=True)
    except Exception:
        return


def mongo_db():
    client = get_mongo_client()
    if not client:
        return None
    return client[app.extensions.get("mongo_db_name", "site_mx")]


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
            user_id INTEGER,
            reporter_name TEXT,
            report_type TEXT NOT NULL,
            report_text TEXT NOT NULL,
            admin_reply TEXT,
            replied_at TEXT,
            user_seen_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS category_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            device_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(category_id, device_id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS user_video_seen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            seen_at TEXT NOT NULL,
            UNIQUE(user_id, category_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS presence_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            page_key TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(device_id, page_key)
        );

        CREATE TABLE IF NOT EXISTS download_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            user_id INTEGER,
            video_id INTEGER,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS testimonials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            display_name TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            admin_note TEXT,
            reviewed_at TEXT,
            is_seed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS auth_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            access_code TEXT NOT NULL UNIQUE,
            note TEXT,
            is_banned INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS auth_user_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auth_user_id INTEGER NOT NULL,
            device_id TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            UNIQUE(auth_user_id, device_id),
            FOREIGN KEY (auth_user_id) REFERENCES auth_users(id)
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_purchase_requests_user_status
            ON purchase_requests(user_id, status, id);
        CREATE INDEX IF NOT EXISTS idx_purchase_requests_user_created
            ON purchase_requests(user_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_user_access_user
            ON user_access(user_id, category_id);
        CREATE INDEX IF NOT EXISTS idx_videos_category
            ON videos(category_id, id);
        CREATE INDEX IF NOT EXISTS idx_category_likes_category
            ON category_likes(category_id);
        CREATE INDEX IF NOT EXISTS idx_presence_updated
            ON presence_sessions(updated_at);
        CREATE INDEX IF NOT EXISTS idx_download_updated
            ON download_sessions(updated_at);
        CREATE INDEX IF NOT EXISTS idx_auth_user_devices_user
            ON auth_user_devices(auth_user_id);
        """
    )

    user_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(users)").fetchall()]
    if "is_banned" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0")
    visitor_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(visitors)").fetchall()]
    if "username" not in visitor_cols:
        cursor.execute("ALTER TABLE visitors ADD COLUMN username TEXT")
    if "user_agent" not in visitor_cols:
        cursor.execute("ALTER TABLE visitors ADD COLUMN user_agent TEXT")
    if "browser_name" not in visitor_cols:
        cursor.execute("ALTER TABLE visitors ADD COLUMN browser_name TEXT")
    if "os_name" not in visitor_cols:
        cursor.execute("ALTER TABLE visitors ADD COLUMN os_name TEXT")
    if "device_model" not in visitor_cols:
        cursor.execute("ALTER TABLE visitors ADD COLUMN device_model TEXT")
    auth_user_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(auth_users)").fetchall()]
    if "access_code" not in auth_user_cols:
        cursor.execute("ALTER TABLE auth_users ADD COLUMN access_code TEXT")
    if "note" not in auth_user_cols:
        cursor.execute("ALTER TABLE auth_users ADD COLUMN note TEXT")
    null_code_rows = cursor.execute("SELECT id FROM auth_users WHERE access_code IS NULL OR access_code=''").fetchall()
    for row in null_code_rows:
        while True:
            new_code = generate_access_code(16)
            exists = cursor.execute("SELECT id FROM auth_users WHERE access_code=?", (new_code,)).fetchone()
            if exists:
                continue
            cursor.execute("UPDATE auth_users SET access_code=?, updated_at=? WHERE id=?", (new_code, datetime.utcnow().isoformat(), row["id"]))
            break
    duplicate_rows = cursor.execute(
        """
        SELECT access_code FROM auth_users
        WHERE access_code IS NOT NULL AND access_code<>''
        GROUP BY access_code
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    for dup in duplicate_rows:
        rows = cursor.execute(
            "SELECT id FROM auth_users WHERE access_code=? ORDER BY id ASC",
            (dup["access_code"],),
        ).fetchall()
        for item in rows[1:]:
            while True:
                new_code = generate_access_code(16)
                exists = cursor.execute("SELECT id FROM auth_users WHERE access_code=?", (new_code,)).fetchone()
                if exists:
                    continue
                cursor.execute("UPDATE auth_users SET access_code=?, updated_at=? WHERE id=?", (new_code, datetime.utcnow().isoformat(), item["id"]))
                break
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_users_access_code
        ON auth_users(access_code)
        """
    )

    report_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(reports)").fetchall()]
    if "reporter_name" not in report_cols:
        cursor.execute("ALTER TABLE reports ADD COLUMN reporter_name TEXT")
    if "user_id" not in report_cols:
        cursor.execute("ALTER TABLE reports ADD COLUMN user_id INTEGER")
    if "admin_reply" not in report_cols:
        cursor.execute("ALTER TABLE reports ADD COLUMN admin_reply TEXT")
    if "replied_at" not in report_cols:
        cursor.execute("ALTER TABLE reports ADD COLUMN replied_at TEXT")
    if "user_seen_at" not in report_cols:
        cursor.execute("ALTER TABLE reports ADD COLUMN user_seen_at TEXT")
    testimonial_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(testimonials)").fetchall()]
    if "status" not in testimonial_cols:
        cursor.execute("ALTER TABLE testimonials ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
    if "admin_note" not in testimonial_cols:
        cursor.execute("ALTER TABLE testimonials ADD COLUMN admin_note TEXT")
    if "reviewed_at" not in testimonial_cols:
        cursor.execute("ALTER TABLE testimonials ADD COLUMN reviewed_at TEXT")

    default_settings = {
        "site_update_mode": "1" if DEFAULT_SITE_UPDATE_MODE else "0",
        "site_domain_move_mode": "1" if DEFAULT_SITE_DOMAIN_MOVE_MODE else "0",
        "site_domain_move_target": DEFAULT_SITE_DOMAIN_MOVE_TARGET,
        "utc_adjust_hours": str(DEFAULT_UTC_ADJUST_HOURS),
        "max_devices_per_user": str(DEFAULT_MAX_DEVICES_PER_USER),
        "maintenance_fallback_url": "http://mxdomain.top:5000",
    }
    for key, value in default_settings.items():
        cursor.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES(?,?,?)
            ON CONFLICT(key) DO NOTHING
            """,
            (key, value, datetime.utcnow().isoformat()),
        )

    db.commit()
    db.close()


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def parse_user_agent(user_agent: str) -> dict[str, str]:
    ua = user_agent or ""
    ua_low = ua.lower()
    browser_name = "Unknown"
    if "crios" in ua_low:
        browser_name = "Chrome iOS"
    elif "chrome/" in ua_low:
        browser_name = "Chrome"
    elif "firefox/" in ua_low:
        browser_name = "Firefox"
    elif "safari/" in ua_low and "chrome/" not in ua_low:
        browser_name = "Safari"

    os_name = "Unknown"
    if "iphone" in ua_low or "ipad" in ua_low:
        os_name = "iOS"
    elif "android" in ua_low:
        os_name = "Android"
    elif "windows" in ua_low:
        os_name = "Windows"
    elif "mac os x" in ua_low:
        os_name = "macOS"

    device_model = "Desktop"
    if "iphone" in ua_low:
        device_model = "iPhone"
    elif "ipad" in ua_low:
        device_model = "iPad"
    elif "android" in ua_low:
        device_model = "Android"
    return {"browser_name": browser_name, "os_name": os_name, "device_model": device_model}


def register_visit(device_id: str, db=None):
    if not device_id:
        return
    local_db = db or get_db()
    ua = request.headers.get("User-Agent", "")
    ua_meta = parse_user_agent(ua)
    should_commit = db is None
    existing = local_db.execute(
        "SELECT id, visit_count, last_seen_at FROM visitors WHERE device_id=?",
        (device_id,),
    ).fetchone()
    updated = False
    if existing:
        try:
            last_seen = datetime.fromisoformat(existing["last_seen_at"])
        except Exception:
            last_seen = None
        now = datetime.utcnow()
        should_update = last_seen is None or (now - last_seen).total_seconds() >= 120
        if should_update:
            local_db.execute(
                """
                UPDATE visitors
                SET last_seen_at=?, visit_count=visit_count+1, user_agent=?, browser_name=?, os_name=?, device_model=?
                WHERE id=?
                """,
                (now_iso(), ua, ua_meta["browser_name"], ua_meta["os_name"], ua_meta["device_model"], existing["id"]),
            )
            updated = True
    else:
        local_db.execute(
            """
            INSERT INTO visitors(device_id, username, first_seen_at, last_seen_at, visit_count)
            VALUES(?,?,?,?,?)
            """,
            (device_id, None, now_iso(), now_iso(), 1),
        )
        local_db.execute(
            """
            UPDATE visitors SET user_agent=?, browser_name=?, os_name=?, device_model=?
            WHERE device_id=?
            """,
            (ua, ua_meta["browser_name"], ua_meta["os_name"], ua_meta["device_model"], device_id),
        )
        updated = True
    if should_commit and updated:
        local_db.commit()
    mongo_upsert(
        "visitors",
        {"device_id": device_id},
        {
            "device_id": device_id,
            "last_seen_at": now_iso(),
            "user_agent": ua,
            "browser_name": ua_meta["browser_name"],
            "os_name": ua_meta["os_name"],
            "device_model": ua_meta["device_model"],
        },
    )


def cleanup_live_sessions(db):
    cutoff = (datetime.utcnow() - timedelta(seconds=DOWNLOAD_ACTIVE_SECONDS)).isoformat()
    db.execute("DELETE FROM download_sessions WHERE updated_at < ?", (cutoff,))
    presence_cutoff = (datetime.utcnow() - timedelta(seconds=ONLINE_SECONDS)).isoformat()
    db.execute("DELETE FROM presence_sessions WHERE updated_at < ?", (presence_cutoff,))


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged"):
            return redirect(url_for("admin_login"))
        return func(*args, **kwargs)

    return wrapper


def current_auth_user(db=None):
    access_code = session.get("auth_access_code")
    mdb = mongo_db()
    if access_code and mdb is not None:
        doc = mdb["auth_users"].find_one({"access_code": access_code})
        if doc:
            doc["id"] = str(doc.get("_id"))
            return doc
    auth_user_id = session.get("auth_user_id")
    if not auth_user_id:
        return None
    local_db = db or get_db()
    return local_db.execute("SELECT * FROM auth_users WHERE id=?", (auth_user_id,)).fetchone()


def get_device_id_from_request(payload: dict | None = None) -> str:
    if payload and payload.get("device_id"):
        return str(payload.get("device_id")).strip()
    form_val = request.form.get("device_id", "").strip()
    if form_val:
        return form_val
    query_val = request.args.get("device_id", "").strip()
    if query_val:
        return query_val
    return request.cookies.get("mx_device_id", "").strip()


def require_auth_for_api(db, payload: dict | None = None):
    auth_user = current_auth_user(db=db)
    if not auth_user:
        return None, jsonify({"ok": False, "message": "ابتدا وارد حساب شوید.", "login_required": True}), 401
    device_id = get_device_id_from_request(payload=payload)
    if not device_id:
        return None, jsonify({"ok": False, "message": "شناسه دستگاه پیدا نشد.", "login_required": True}), 401
    mdb = mongo_db()
    if mdb is not None and auth_user.get("access_code"):
        bind = mdb["auth_user_devices"].find_one({"access_code": auth_user["access_code"], "device_id": device_id})
        if not bind:
            return None, jsonify({"ok": False, "message": "دستگاه شما برای این اکانت مجاز نیست.", "login_required": True}), 403
    else:
        bind = db.execute(
            "SELECT id FROM auth_user_devices WHERE auth_user_id=? AND device_id=?",
            (auth_user["id"], device_id),
        ).fetchone()
        if not bind:
            return None, jsonify({"ok": False, "message": "دستگاه شما برای این اکانت مجاز نیست.", "login_required": True}), 403
    return (auth_user, device_id), None, None


def bind_device_to_auth_user(auth_user_id: int, device_id: str, db):
    mdb = mongo_db()
    if mdb is not None and isinstance(auth_user_id, str):
        max_devices = setting_int("max_devices_per_user", DEFAULT_MAX_DEVICES_PER_USER)
        existing = mdb["auth_user_devices"].find_one({"access_code": auth_user_id, "device_id": device_id})
        if existing:
            mdb["auth_user_devices"].update_one(
                {"_id": existing["_id"]},
                {"$set": {"last_seen_at": now_iso()}},
            )
            return True, ""
        count = mdb["auth_user_devices"].count_documents({"access_code": auth_user_id})
        if count >= max_devices:
            return False, f"این اکانت فقط روی {max_devices} دستگاه مجاز است."
        mdb["auth_user_devices"].insert_one(
            {
                "access_code": auth_user_id,
                "device_id": device_id,
                "first_seen_at": now_iso(),
                "last_seen_at": now_iso(),
            }
        )
        return True, ""

    max_devices = setting_int("max_devices_per_user", DEFAULT_MAX_DEVICES_PER_USER)
    existing = db.execute(
        "SELECT id FROM auth_user_devices WHERE auth_user_id=? AND device_id=?",
        (auth_user_id, device_id),
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE auth_user_devices SET last_seen_at=? WHERE id=?",
            (now_iso(), existing["id"]),
        )
        return True, ""

    count = db.execute(
        "SELECT COUNT(*) AS c FROM auth_user_devices WHERE auth_user_id=?",
        (auth_user_id,),
    ).fetchone()["c"]
    if count >= max_devices:
        return False, f"این اکانت فقط روی {max_devices} دستگاه مجاز است."

    db.execute(
        """
        INSERT INTO auth_user_devices(auth_user_id, device_id, first_seen_at, last_seen_at)
        VALUES(?,?,?,?)
        """,
        (auth_user_id, device_id, now_iso(), now_iso()),
    )
    return True, ""


def is_iphone_user_agent(user_agent: str) -> bool:
    ua = user_agent or ""
    return bool(re.search(r"iphone|ipod", ua, flags=re.IGNORECASE))


def is_chrome_ios_user_agent(user_agent: str) -> bool:
    ua = user_agent or ""
    return bool(re.search(r"crios", ua, flags=re.IGNORECASE))


@app.before_request
def site_global_modes():
    endpoint = request.endpoint or ""
    path = request.path or "/"
    public_exempt_endpoints = {
        "static",
        "admin_login",
        "admin_logout",
        "admin_dashboard",
        "admin_live_stats",
        "admin_backup_db",
        "admin_view_receipt",
        "acme_challenge",
        "site_update_page",
        "site_domain_move_page",
        "iphone_chrome_required_page",
        "api_system_status",
    }
    if endpoint in public_exempt_endpoints:
        return None
    if path.startswith("/admin"):
        return None

    site_update_mode = setting_bool("site_update_mode", DEFAULT_SITE_UPDATE_MODE)
    site_domain_move_mode = setting_bool("site_domain_move_mode", DEFAULT_SITE_DOMAIN_MOVE_MODE)
    site_domain_target = get_setting("site_domain_move_target", DEFAULT_SITE_DOMAIN_MOVE_TARGET)

    if site_update_mode:
        if path.startswith("/api/"):
            return jsonify({"ok": False, "message": "سایت در حال بروزرسانی است."}), 503
        return redirect(url_for("site_update_page"))

    if site_domain_move_mode:
        if path.startswith("/api/"):
            return jsonify(
                {
                    "ok": False,
                    "message": "سایت به دامنه جدید منتقل شده است.",
                    "target_url": site_domain_target,
                }
            ), 503
        return redirect(url_for("site_domain_move_page"))

    user_agent = request.headers.get("User-Agent", "")
    if is_iphone_user_agent(user_agent) and not is_chrome_ios_user_agent(user_agent):
        if path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "ok": False,
                        "message": "در iPhone فقط مرورگر Chrome مجاز است.",
                        "need_chrome_ios": True,
                    }
                ),
                403,
            )
        if path != "/iphone-chrome-required":
            return redirect(url_for("iphone_chrome_required_page", next=request.url))


@app.route("/")
def home():
    db = get_db()
    categories = db.execute("SELECT * FROM categories ORDER BY id").fetchall()
    testimonials = db.execute(
        """
        SELECT t.display_name, t.content, t.created_at,
               (
                   SELECT GROUP_CONCAT(c.title, ' | ')
                   FROM user_access ua
                   JOIN categories c ON c.id = ua.category_id
                   WHERE ua.user_id = t.user_id
               ) AS category_titles
        FROM testimonials t
        WHERE t.status='approved'
        ORDER BY t.id DESC
        LIMIT 160
        """
    ).fetchall()
    return render_template("home.html", categories=categories, testimonials=testimonials)


@app.route("/site-update")
def site_update_page():
    fallback_url = get_setting("maintenance_fallback_url", "http://mxdomain.top:5000")
    return render_template("site_update.html", fallback_url=fallback_url)


@app.route("/site-domain-moved")
def site_domain_move_page():
    target_url = get_setting("site_domain_move_target", DEFAULT_SITE_DOMAIN_MOVE_TARGET)
    return render_template("site_domain_moved.html", target_url=target_url)


@app.get("/api/system-status")
def api_system_status():
    return jsonify(
        {
            "ok": True,
            "site_update_mode": setting_bool("site_update_mode", DEFAULT_SITE_UPDATE_MODE),
            "site_domain_move_mode": setting_bool("site_domain_move_mode", DEFAULT_SITE_DOMAIN_MOVE_MODE),
            "site_domain_move_target": get_setting("site_domain_move_target", DEFAULT_SITE_DOMAIN_MOVE_TARGET),
        }
    )


@app.route("/iphone-chrome-required")
def iphone_chrome_required_page():
    next_url = request.args.get("next", url_for("home"))
    open_url = request.args.get("open", "")
    return render_template("iphone_chrome_required.html", next_url=next_url, open_url=open_url)


@app.get("/login")
def login_page():
    next_url = request.args.get("next", url_for("home"))
    if session.get("auth_user_id") or session.get("auth_access_code"):
        return redirect(next_url)
    return render_template("login.html", next_url=next_url)


@app.post("/api/auth/login")
def api_auth_login():
    payload = request.get_json(silent=True) or {}
    access_code = (payload.get("access_code") or "").strip().upper()
    device_id = get_device_id_from_request(payload)
    if not access_code or len(access_code) != 16 or not device_id:
        return jsonify({"ok": False, "message": "کد ۱۶ کاراکتری و شناسه دستگاه الزامی است."}), 400

    mdb = mongo_db()
    if mdb is not None:
        user = mdb["auth_users"].find_one({"access_code": access_code})
        if not user:
            return jsonify({"ok": False, "message": "کد وارد شده اشتباه است."}), 401
        ok, msg = bind_device_to_auth_user(access_code, device_id, None)
        if not ok:
            return jsonify({"ok": False, "message": msg}), 403
        mdb["auth_users"].update_one({"access_code": access_code}, {"$set": {"updated_at": now_iso()}})
        session["auth_access_code"] = access_code
        session.pop("auth_user_id", None)
        return jsonify({"ok": True, "access_code": access_code})

    db = get_db()
    user = db.execute("SELECT * FROM auth_users WHERE access_code=?", (access_code,)).fetchone()
    if not user:
        return jsonify({"ok": False, "message": "کد وارد شده اشتباه است."}), 401
    ok, msg = bind_device_to_auth_user(user["id"], device_id, db)
    if not ok:
        return jsonify({"ok": False, "message": msg}), 403
    db.execute("UPDATE auth_users SET updated_at=? WHERE id=?", (now_iso(), user["id"]))
    db.commit()
    session["auth_user_id"] = user["id"]
    return jsonify({"ok": True, "access_code": user["access_code"]})


@app.post("/api/auth/create-code")
def api_auth_create_code():
    payload = request.get_json(silent=True) or {}
    device_id = get_device_id_from_request(payload)
    if not device_id:
        return jsonify({"ok": False, "message": "شناسه دستگاه لازم است."}), 400

    mdb = mongo_db()
    if mdb is not None:
        for _ in range(10):
            access_code = generate_access_code(16)
            exists = mdb["auth_users"].find_one({"access_code": access_code})
            if exists:
                continue
            mdb["auth_users"].insert_one(
                {
                    "access_code": access_code,
                    "note": "first_purchase",
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                }
            )
            ok, msg = bind_device_to_auth_user(access_code, device_id, None)
            if not ok:
                return jsonify({"ok": False, "message": msg}), 403
            session["auth_access_code"] = access_code
            session.pop("auth_user_id", None)
            return jsonify(
                {
                    "ok": True,
                    "access_code": access_code,
                    "message": "کد شما ساخته شد. حتما آن را نگه دارید؛ در غیر این صورت دسترسی شما قطع می‌شود.",
                }
            )
        return jsonify({"ok": False, "message": "فعلا امکان ساخت کد نیست. دوباره تلاش کنید."}), 500

    db = get_db()
    auth_cols = [r["name"] for r in db.execute("PRAGMA table_info(auth_users)").fetchall()]
    for _ in range(10):
        access_code = generate_access_code(16)
        exists = db.execute("SELECT id FROM auth_users WHERE access_code=?", (access_code,)).fetchone()
        if exists:
            continue
        if "username" in auth_cols and "password_hash" in auth_cols:
            db.execute(
                "INSERT INTO auth_users(access_code, note, created_at, updated_at, username, password_hash) VALUES(?,?,?,?,?,?)",
                (access_code, "first_purchase", now_iso(), now_iso(), f"code_{access_code[:8]}", "legacy"),
            )
        else:
            db.execute(
                "INSERT INTO auth_users(access_code, note, created_at, updated_at) VALUES(?,?,?,?)",
                (access_code, "first_purchase", now_iso(), now_iso()),
            )
        user = db.execute("SELECT * FROM auth_users WHERE access_code=?", (access_code,)).fetchone()
        ok, msg = bind_device_to_auth_user(user["id"], device_id, db)
        if not ok:
            return jsonify({"ok": False, "message": msg}), 403
        db.commit()
        session["auth_user_id"] = user["id"]
        return jsonify(
            {
                "ok": True,
                "access_code": access_code,
                "message": "کد شما ساخته شد. حتما آن را نگه دارید؛ در غیر این صورت دسترسی شما قطع می‌شود.",
            }
        )
    return jsonify({"ok": False, "message": "فعلا امکان ساخت کد نیست. دوباره تلاش کنید."}), 500


@app.get("/api/auth/status")
def api_auth_status():
    device_id = get_device_id_from_request()
    db = get_db()
    user = current_auth_user(db=db)
    if not user:
        return jsonify({"ok": True, "logged_in": False})
    mdb = mongo_db()
    if mdb is not None and user.get("access_code"):
        has_device = mdb["auth_user_devices"].find_one({"access_code": user["access_code"], "device_id": device_id})
    else:
        has_device = db.execute(
            "SELECT id FROM auth_user_devices WHERE auth_user_id=? AND device_id=?",
            (user["id"], device_id),
        ).fetchone()
    return jsonify(
        {
            "ok": True,
            "logged_in": bool(has_device),
            "access_code": user["access_code"],
            "max_devices": setting_int("max_devices_per_user", DEFAULT_MAX_DEVICES_PER_USER),
        }
    )


@app.get("/api/auth/my-code")
def api_auth_my_code():
    db = get_db()
    auth_result, err_resp, err_status = require_auth_for_api(db)
    if err_resp is not None:
        return err_resp, err_status
    auth_user, _device_id = auth_result
    return jsonify({"ok": True, "access_code": auth_user["access_code"]})


@app.post("/api/auth/logout")
def api_auth_logout():
    session.pop("auth_user_id", None)
    session.pop("auth_access_code", None)
    return jsonify({"ok": True})


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


@app.post("/api/presence")
def api_presence():
    payload = request.get_json(silent=True) or {}
    device_id = (payload.get("device_id") or "").strip()
    page_key = (payload.get("page_key") or "unknown").strip()[:80]
    if not device_id:
        return jsonify({"ok": False, "message": "شناسه دستگاه لازم است."}), 400
    db = get_db()
    register_visit(device_id, db=db)
    cleanup_live_sessions(db)
    db.execute(
        """
        INSERT INTO presence_sessions(device_id, page_key, updated_at)
        VALUES(?,?,?)
        ON CONFLICT(device_id, page_key) DO UPDATE SET updated_at=excluded.updated_at
        """,
        (device_id, page_key or "unknown", now_iso()),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/buy/<slug>")
def buy_page(slug):
    if not session.get("auth_user_id") and not session.get("auth_access_code"):
        return redirect(url_for("login_page", next=request.full_path.rstrip("?")))
    db = get_db()
    category = db.execute("SELECT * FROM categories WHERE slug=?", (slug,)).fetchone()
    if not category:
        abort(404)
    return render_template("buy.html", category=category)


@app.post("/api/submit-request")
def submit_request():
    device_id = get_device_id_from_request()
    category_id = request.form.get("category_id", "").strip()
    receipt = request.files.get("receipt")

    if not device_id or not category_id:
        return jsonify({"ok": False, "message": "شناسه دستگاه و فیش الزامی هستند."}), 400

    db = get_db()
    auth_result, err_resp, err_status = require_auth_for_api(db)
    if err_resp is not None:
        return err_resp, err_status
    auth_user, _bound_device_id = auth_result

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
                "ok": False,
                "message": CLIENT_WAITING_REVIEW_TEXT,
                "next_url": "/my-videos",
                "pending_exists": True,
            }
        ), 409

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
    mongo_upsert(
        "purchase_requests",
        {"id": int(db.execute("SELECT last_insert_rowid() AS i").fetchone()["i"])},
        {
            "device_id": device_id,
            "user_id": user["id"],
            "category_id": category["id"],
            "status": "pending",
            "created_at": now_iso(),
        },
    )

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

    latest = db.execute(
        """
        SELECT status, admin_note, reviewed_at, created_at
        FROM purchase_requests
        WHERE user_id=?
        ORDER BY id DESC LIMIT 1
        """,
        (user["id"],),
    ).fetchone()
    has_pending = bool(latest and latest["status"] == "pending")
    is_rejected = bool(latest and latest["status"] == "rejected")
    return jsonify(
        {
            "ok": True,
            "latest_status": (latest["status"] if latest else None),
            "has_pending": has_pending,
            "is_rejected": is_rejected,
            "message": CLIENT_WAITING_REVIEW_TEXT,
            "rejected_note": (latest["admin_note"] if is_rejected else None),
            "reviewed_at": (latest["reviewed_at"] if latest else None),
            "created_at": (latest["created_at"] if latest else None),
        }
    )


@app.route("/my-videos")
def my_videos_page():
    return render_template("my_videos.html")


@app.route("/messages")
def messages_page():
    return render_template("messages.html")


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

    total_categories = db.execute(
        "SELECT COUNT(*) AS c FROM user_access WHERE user_id=?",
        (user["id"],),
    ).fetchone()["c"]

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
                    "external_url": row["external_url"],
                }
            )

    return jsonify(
        {
            "ok": True,
            "approved_text": CLIENT_APPROVED_TEXT,
            "categories": list(grouped.values()),
            "total_categories": total_categories,
        }
    )


@app.get("/api/my-videos/summary")
def api_my_videos_summary():
    device_id = request.args.get("device_id", "").strip()
    if not device_id:
        return jsonify({"ok": True, "total_categories": 0, "seen_categories": 0, "unseen_categories": 0})

    db = get_db()
    user = db.execute("SELECT id FROM users WHERE device_id=? ORDER BY id DESC", (device_id,)).fetchone()
    if not user:
        return jsonify({"ok": True, "total_categories": 0, "seen_categories": 0, "unseen_categories": 0})

    total = db.execute("SELECT COUNT(*) AS c FROM user_access WHERE user_id=?", (user["id"],)).fetchone()["c"]
    seen = db.execute("SELECT COUNT(*) AS c FROM user_video_seen WHERE user_id=?", (user["id"],)).fetchone()["c"]
    unseen = max(total - seen, 0)
    return jsonify({"ok": True, "total_categories": total, "seen_categories": seen, "unseen_categories": unseen})


@app.post("/api/my-videos/mark-seen")
def api_mark_videos_seen():
    payload = request.get_json(silent=True) or {}
    device_id = (payload.get("device_id") or "").strip()
    if not device_id:
        return jsonify({"ok": False, "message": "شناسه دستگاه لازم است."}), 400

    db = get_db()
    user = db.execute("SELECT id FROM users WHERE device_id=? ORDER BY id DESC", (device_id,)).fetchone()
    if not user:
        return jsonify({"ok": True, "marked": 0})

    category_ids = db.execute("SELECT category_id FROM user_access WHERE user_id=?", (user["id"],)).fetchall()
    marked = 0
    for row in category_ids:
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO user_video_seen(user_id, category_id, seen_at)
            VALUES(?,?,?)
            """,
            (user["id"], row["category_id"], now_iso()),
        )
        if cursor.rowcount:
            marked += 1
    db.commit()
    return jsonify({"ok": True, "marked": marked})


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

    cleanup_live_sessions(db)
    db.execute(
        "INSERT INTO download_sessions(device_id, user_id, video_id, updated_at) VALUES(?,?,?,?)",
        (device_id, payload.get("uid"), payload.get("vid"), now_iso()),
    )
    db.commit()

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
    cleanup_live_sessions(db)
    q = (request.args.get("q") or "").strip()
    try:
        visitors_limit = max(50, min(1000, int(request.args.get("limit") or "300")))
    except Exception:
        visitors_limit = 300
    today_start, tomorrow_start = tehran_day_range_utc_iso()
    yesterday_start, today_start_for_yesterday = tehran_day_range_utc_iso(offset_days=-1)
    requests_rows = db.execute(
        """
        SELECT pr.*, u.id AS user_id, u.device_id, c.title as requested_category
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
        """
        SELECT r.*, u.id AS user_id
        FROM reports r
        LEFT JOIN users u ON u.id = r.user_id
        ORDER BY r.id DESC LIMIT 300
        """
    ).fetchall()
    testimonials = db.execute(
        """
        SELECT t.*, 
               (
                   SELECT GROUP_CONCAT(c.title, ' | ')
                   FROM user_access ua
                   JOIN categories c ON c.id = ua.category_id
                   WHERE ua.user_id = t.user_id
               ) AS category_titles
        FROM testimonials t
        ORDER BY t.id DESC
        LIMIT 250
        """
    ).fetchall()
    visitors_query = """
        SELECT * FROM visitors
        WHERE (? = '' OR device_id LIKE ? OR COALESCE(username,'') LIKE ? OR COALESCE(browser_name,'') LIKE ? OR COALESCE(os_name,'') LIKE ?)
        ORDER BY last_seen_at DESC
        LIMIT ?
    """
    visitors = db.execute(
        visitors_query,
        (q, f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", visitors_limit),
    ).fetchall()
    auth_users = db.execute(
        """
        SELECT au.*, COUNT(aud.id) AS device_count, MAX(aud.last_seen_at) AS last_device_seen
        FROM auth_users au
        LEFT JOIN auth_user_devices aud ON aud.auth_user_id = au.id
        WHERE (? = '' OR au.access_code LIKE ?)
        GROUP BY au.id
        ORDER BY au.updated_at DESC
        LIMIT ?
        """,
        (q, f"%{q}%", visitors_limit),
    ).fetchall()
    user_categories_rows = db.execute(
        """
        SELECT ua.user_id, GROUP_CONCAT(c.title, ' | ') AS category_titles
        FROM user_access ua
        JOIN categories c ON c.id = ua.category_id
        GROUP BY ua.user_id
        """
    ).fetchall()
    user_categories = {row["user_id"]: row["category_titles"] for row in user_categories_rows}
    online_total = db.execute(
        "SELECT COUNT(DISTINCT device_id) AS c FROM presence_sessions"
    ).fetchone()["c"]
    downloading_now = db.execute(
        "SELECT COUNT(DISTINCT device_id) AS c FROM download_sessions"
    ).fetchone()["c"]
    online_by_page_rows = db.execute(
        """
        SELECT page_key, COUNT(DISTINCT device_id) AS c
        FROM presence_sessions
        GROUP BY page_key
        ORDER BY c DESC, page_key ASC
        """ 
    ).fetchall()
    online_by_page = {row["page_key"]: row["c"] for row in online_by_page_rows}
    stats = {
        "total_visitors": db.execute("SELECT COUNT(*) AS c FROM visitors").fetchone()["c"],
        "total_purchases": db.execute("SELECT COUNT(*) AS c FROM purchase_requests").fetchone()["c"],
        "total_reports": db.execute("SELECT COUNT(*) AS c FROM reports").fetchone()["c"],
        "approved_receipts": db.execute("SELECT COUNT(*) AS c FROM purchase_requests WHERE status='approved'").fetchone()["c"],
        "rejected_receipts": db.execute("SELECT COUNT(*) AS c FROM purchase_requests WHERE status='rejected'").fetchone()["c"],
        "pending_receipts": db.execute("SELECT COUNT(*) AS c FROM purchase_requests WHERE status='pending'").fetchone()["c"],
        "online_total": online_total,
        "downloading_now": downloading_now,
        "active_last_minute": db.execute(
            "SELECT COUNT(DISTINCT device_id) AS c FROM presence_sessions WHERE updated_at>=?",
            ((datetime.utcnow() - timedelta(seconds=60)).isoformat(),),
        ).fetchone()["c"],
        "today_purchases": db.execute(
            "SELECT COUNT(*) AS c FROM purchase_requests WHERE created_at>=? AND created_at<?",
            (today_start, tomorrow_start),
        ).fetchone()["c"],
        "today_approved": db.execute(
            "SELECT COUNT(*) AS c FROM purchase_requests WHERE status='approved' AND created_at>=? AND created_at<?",
            (today_start, tomorrow_start),
        ).fetchone()["c"],
        "today_rejected": db.execute(
            "SELECT COUNT(*) AS c FROM purchase_requests WHERE status='rejected' AND created_at>=? AND created_at<?",
            (today_start, tomorrow_start),
        ).fetchone()["c"],
        "today_visitors": db.execute(
            "SELECT COUNT(*) AS c FROM visitors WHERE last_seen_at>=? AND last_seen_at<?",
            (today_start, tomorrow_start),
        ).fetchone()["c"],
        "yesterday_purchases": db.execute(
            "SELECT COUNT(*) AS c FROM purchase_requests WHERE created_at>=? AND created_at<?",
            (yesterday_start, today_start_for_yesterday),
        ).fetchone()["c"],
        "yesterday_approved": db.execute(
            "SELECT COUNT(*) AS c FROM purchase_requests WHERE status='approved' AND created_at>=? AND created_at<?",
            (yesterday_start, today_start_for_yesterday),
        ).fetchone()["c"],
        "yesterday_rejected": db.execute(
            "SELECT COUNT(*) AS c FROM purchase_requests WHERE status='rejected' AND created_at>=? AND created_at<?",
            (yesterday_start, today_start_for_yesterday),
        ).fetchone()["c"],
        "yesterday_visitors": db.execute(
            "SELECT COUNT(*) AS c FROM visitors WHERE last_seen_at>=? AND last_seen_at<?",
            (yesterday_start, today_start_for_yesterday),
        ).fetchone()["c"],
    }

    requests_rows_view = []
    for row in requests_rows:
        row_dict = dict(row)
        row_dict["created_at_fa"] = format_tehran(row["created_at"])
        row_dict["reviewed_at_fa"] = format_tehran(row["reviewed_at"])
        row_dict["category_titles"] = user_categories.get(row["user_id"]) or "-"
        requests_rows_view.append(row_dict)
    reports_view = []
    for row in reports:
        row_dict = dict(row)
        row_dict["created_at_fa"] = format_tehran(row["created_at"])
        row_dict["replied_at_fa"] = format_tehran(row["replied_at"])
        row_dict["category_titles"] = user_categories.get(row["user_id"]) or "-"
        reports_view.append(row_dict)
    return render_template(
        "admin_dashboard.html",
        requests_rows=requests_rows_view,
        categories=categories,
        videos=videos,
        reports=reports_view,
        testimonials=testimonials,
        visitors=visitors,
        online_by_page=online_by_page,
        stats=stats,
        visitors_limit=visitors_limit,
        visitors_search=q,
        auth_users=auth_users,
        server_now=format_tehran(now_iso()),
        server_day=to_tehran_adjusted(datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))).strftime("%A"),
        site_update_mode=setting_bool("site_update_mode", DEFAULT_SITE_UPDATE_MODE),
        site_domain_move_mode=setting_bool("site_domain_move_mode", DEFAULT_SITE_DOMAIN_MOVE_MODE),
        site_domain_move_target=get_setting("site_domain_move_target", DEFAULT_SITE_DOMAIN_MOVE_TARGET),
        utc_adjust_hours=get_utc_adjust_hours(),
        max_devices_per_user=setting_int("max_devices_per_user", DEFAULT_MAX_DEVICES_PER_USER),
        maintenance_fallback_url=get_setting("maintenance_fallback_url", "http://mxdomain.top:5000"),
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
    reason = request.form.get("reason", "").strip()
    if not reason:
        return jsonify({"ok": False, "message": "دلیل رد را وارد کنید."}), 400

    db = get_db()
    req = db.execute("SELECT * FROM purchase_requests WHERE id=?", (request_id,)).fetchone()
    if not req:
        return jsonify({"ok": False, "message": "درخواست پیدا نشد."}), 404

    db.execute(
        "UPDATE purchase_requests SET status='rejected', admin_note=?, reviewed_at=? WHERE id=?",
        (reason, now_iso(), request_id),
    )
    db.commit()
    return jsonify({"ok": True})


@app.post("/admin/api/requests/<int:request_id>/reset-pending")
@admin_required
def admin_reset_request_pending(request_id):
    db = get_db()
    req = db.execute("SELECT * FROM purchase_requests WHERE id=?", (request_id,)).fetchone()
    if not req:
        return jsonify({"ok": False, "message": "درخواست پیدا نشد."}), 404

    db.execute(
        "UPDATE purchase_requests SET status='pending', admin_note=NULL, reviewed_at=NULL WHERE id=?",
        (request_id,),
    )
    db.execute("DELETE FROM user_access WHERE source_request_id=?", (request_id,))
    db.commit()
    return jsonify({"ok": True})


@app.post("/api/report")
def submit_report():
    report_type = request.form.get("report_type", "").strip()
    report_text = request.form.get("report_text", "").strip()
    device_id = get_device_id_from_request()
    allowed_types = {"مستحجن", "کلاهبرداری", "پشتیبانی"}

    if report_type not in allowed_types or not report_text or not device_id:
        return jsonify({"ok": False, "message": "اطلاعات ریپورت کامل نیست."}), 400

    db = get_db()
    auth_result, err_resp, err_status = require_auth_for_api(db)
    if err_resp is not None:
        return err_resp, err_status
    _auth_user, _bound_device_id = auth_result

    register_visit(device_id, db=db)
    visitor = db.execute("SELECT * FROM visitors WHERE device_id=?", (device_id,)).fetchone()
    if visitor and visitor["is_banned"]:
        return jsonify({"ok": False, "message": "این دستگاه مسدود شده است."}), 403

    user = db.execute("SELECT id FROM users WHERE device_id=?", (device_id,)).fetchone()
    user_id = user["id"] if user else None
    reporter_name = f"کاربر {user_id}" if user_id else "کاربر مهمان"

    db.execute(
        "INSERT INTO reports(device_id, user_id, reporter_name, report_type, report_text, created_at) VALUES(?,?,?,?,?,?)",
        (device_id, user_id, reporter_name, report_type, report_text, now_iso()),
    )
    db.execute(
        "UPDATE visitors SET report_count=report_count+1, last_seen_at=? WHERE device_id=?",
        (now_iso(), device_id),
    )
    db.commit()
    mongo_upsert(
        "reports",
        {"id": int(db.execute("SELECT last_insert_rowid() AS i").fetchone()["i"])},
        {
            "device_id": device_id,
            "user_id": user_id,
            "report_type": report_type,
            "report_text": report_text,
            "created_at": now_iso(),
        },
    )
    return jsonify({"ok": True, "message": "ریپورت ثبت شد و برای ادمین ارسال شد."})


@app.post("/api/testimonials")
def submit_testimonial():
    testimonial_text = request.form.get("testimonial_text", "").strip()
    device_id = request.form.get("device_id", "").strip()
    if not testimonial_text or not device_id:
        return jsonify({"ok": False, "message": "متن نظر و شناسه دستگاه الزامی است."}), 400

    db = get_db()
    register_visit(device_id, db=db)
    visitor = db.execute("SELECT * FROM visitors WHERE device_id=?", (device_id,)).fetchone()
    if visitor and visitor["is_banned"]:
        return jsonify({"ok": False, "message": "این دستگاه مسدود شده است."}), 403

    user = db.execute("SELECT id FROM users WHERE device_id=?", (device_id,)).fetchone()
    user_id = user["id"] if user else None
    if not user_id:
        return jsonify({"ok": False, "message": "فقط خریداران می‌توانند نظر ثبت کنند."}), 403

    purchased = db.execute(
        "SELECT COUNT(*) AS c FROM purchase_requests WHERE user_id=? AND status='approved'",
        (user_id,),
    ).fetchone()["c"]
    if purchased == 0:
        return jsonify({"ok": False, "message": "برای ثبت نظر باید خرید تاییدشده داشته باشید."}), 403

    reporter_name = f"کاربر {user_id}"
    db.execute(
        """
        INSERT INTO testimonials(user_id,display_name,content,status,is_seed,created_at)
        VALUES(?,?,?,?,?,?)
        """,
        (user_id, reporter_name, testimonial_text, "pending", 0, now_iso()),
    )
    db.commit()
    return jsonify({"ok": True, "message": "نظر شما ثبت شد و پس از تایید ادمین نمایش داده می‌شود."})


@app.get("/api/my-report-replies")
def api_my_report_replies():
    device_id = request.args.get("device_id", "").strip()
    if not device_id:
        return jsonify({"ok": True, "items": []})
    db = get_db()
    rows = db.execute(
        """
        SELECT id, reporter_name, report_type, report_text, admin_reply, created_at, replied_at, user_seen_at
        FROM reports
        WHERE device_id=? AND admin_reply IS NOT NULL
        ORDER BY id DESC
        LIMIT 20
        """,
        (device_id,),
    ).fetchall()
    items = []
    for row in rows:
        items.append(
            {
                "reporter_name": row["reporter_name"],
                "id": row["id"],
                "report_type": row["report_type"],
                "report_text": row["report_text"],
                "admin_reply": row["admin_reply"],
                "created_at": format_tehran(row["created_at"]),
                "replied_at": format_tehran(row["replied_at"]),
                "is_seen": bool(row["user_seen_at"]),
            }
        )
    unseen_count = sum(1 for item in items if not item["is_seen"])
    return jsonify({"ok": True, "items": items, "unseen_count": unseen_count})


@app.post("/api/my-report-replies/mark-seen")
def api_mark_replies_seen():
    payload = request.get_json(silent=True) or {}
    device_id = (payload.get("device_id") or "").strip()
    if not device_id:
        return jsonify({"ok": False, "message": "شناسه دستگاه لازم است."}), 400
    db = get_db()
    db.execute(
        """
        UPDATE reports
        SET user_seen_at=?
        WHERE device_id=? AND admin_reply IS NOT NULL AND user_seen_at IS NULL
        """,
        (now_iso(), device_id),
    )
    db.commit()
    return jsonify({"ok": True})


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

    desired = payload.get("liked")
    existing = db.execute(
        "SELECT id FROM category_likes WHERE category_id=? AND device_id=?",
        (category_id, device_id),
    ).fetchone()

    if isinstance(desired, bool):
        if desired and not existing:
            db.execute(
                "INSERT OR IGNORE INTO category_likes(category_id, device_id, created_at) VALUES(?,?,?)",
                (category_id, device_id, now_iso()),
            )
        if (not desired) and existing:
            db.execute("DELETE FROM category_likes WHERE id=?", (existing["id"],))
        liked = desired
    else:
        if existing:
            db.execute("DELETE FROM category_likes WHERE id=?", (existing["id"],))
            liked = False
        else:
            db.execute(
                "INSERT OR IGNORE INTO category_likes(category_id, device_id, created_at) VALUES(?,?,?)",
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


@app.post("/admin/api/videos/<int:video_id>/delete")
@admin_required
def admin_delete_video(video_id):
    db = get_db()
    video = db.execute("SELECT * FROM videos WHERE id=?", (video_id,)).fetchone()
    if not video:
        return jsonify({"ok": False, "message": "فایل پیدا نشد."}), 404

    if video["file_path"]:
        full = os.path.join(VIDEOS_DIR, video["file_path"])
        if os.path.exists(full):
            try:
                os.remove(full)
            except OSError:
                pass
    db.execute("DELETE FROM videos WHERE id=?", (video_id,))
    db.commit()
    return jsonify({"ok": True})


@app.post("/admin/api/testimonials/<int:testimonial_id>/delete")
@admin_required
def admin_delete_testimonial(testimonial_id):
    db = get_db()
    row = db.execute("SELECT id FROM testimonials WHERE id=?", (testimonial_id,)).fetchone()
    if not row:
        return jsonify({"ok": False, "message": "نظر پیدا نشد."}), 404
    db.execute("DELETE FROM testimonials WHERE id=?", (testimonial_id,))
    db.commit()
    return jsonify({"ok": True})


@app.post("/admin/api/testimonials/<int:testimonial_id>/approve")
@admin_required
def admin_approve_testimonial(testimonial_id):
    db = get_db()
    row = db.execute("SELECT id FROM testimonials WHERE id=?", (testimonial_id,)).fetchone()
    if not row:
        return jsonify({"ok": False, "message": "نظر پیدا نشد."}), 404
    db.execute(
        "UPDATE testimonials SET status='approved', admin_note=NULL, reviewed_at=? WHERE id=?",
        (now_iso(), testimonial_id),
    )
    db.commit()
    return jsonify({"ok": True})


@app.post("/admin/api/testimonials/<int:testimonial_id>/reject")
@admin_required
def admin_reject_testimonial(testimonial_id):
    db = get_db()
    row = db.execute("SELECT id FROM testimonials WHERE id=?", (testimonial_id,)).fetchone()
    if not row:
        return jsonify({"ok": False, "message": "نظر پیدا نشد."}), 404
    db.execute(
        "UPDATE testimonials SET status='rejected', reviewed_at=? WHERE id=?",
        (now_iso(), testimonial_id),
    )
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
        if "://" not in external_url:
            external_url = f"https://{external_url}"
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


@app.get("/admin/api/live-stats")
@admin_required
def admin_live_stats():
    db = get_db()
    cleanup_live_sessions(db)
    today_start, tomorrow_start = tehran_day_range_utc_iso()
    yesterday_start, today_start_for_yesterday = tehran_day_range_utc_iso(offset_days=-1)
    online_by_page_rows = db.execute(
        """
        SELECT page_key, COUNT(DISTINCT device_id) AS c
        FROM presence_sessions
        GROUP BY page_key
        ORDER BY c DESC, page_key ASC
        """
    ).fetchall()
    online_by_page = {row["page_key"]: row["c"] for row in online_by_page_rows}
    stats = {
        "total_visitors": db.execute("SELECT COUNT(*) AS c FROM visitors").fetchone()["c"],
        "total_purchases": db.execute("SELECT COUNT(*) AS c FROM purchase_requests").fetchone()["c"],
        "total_reports": db.execute("SELECT COUNT(*) AS c FROM reports").fetchone()["c"],
        "approved_receipts": db.execute("SELECT COUNT(*) AS c FROM purchase_requests WHERE status='approved'").fetchone()["c"],
        "rejected_receipts": db.execute("SELECT COUNT(*) AS c FROM purchase_requests WHERE status='rejected'").fetchone()["c"],
        "online_total": db.execute("SELECT COUNT(DISTINCT device_id) AS c FROM presence_sessions").fetchone()["c"],
        "downloading_now": db.execute("SELECT COUNT(DISTINCT device_id) AS c FROM download_sessions").fetchone()["c"],
        "active_last_minute": db.execute(
            "SELECT COUNT(DISTINCT device_id) AS c FROM presence_sessions WHERE updated_at>=?",
            ((datetime.utcnow() - timedelta(seconds=60)).isoformat(),),
        ).fetchone()["c"],
        "latest_purchase_id": db.execute("SELECT COALESCE(MAX(id),0) AS m FROM purchase_requests").fetchone()["m"],
        "latest_report_id": db.execute("SELECT COALESCE(MAX(id),0) AS m FROM reports").fetchone()["m"],
        "today_purchases": db.execute(
            "SELECT COUNT(*) AS c FROM purchase_requests WHERE created_at>=? AND created_at<?",
            (today_start, tomorrow_start),
        ).fetchone()["c"],
        "today_approved": db.execute(
            "SELECT COUNT(*) AS c FROM purchase_requests WHERE status='approved' AND created_at>=? AND created_at<?",
            (today_start, tomorrow_start),
        ).fetchone()["c"],
        "today_rejected": db.execute(
            "SELECT COUNT(*) AS c FROM purchase_requests WHERE status='rejected' AND created_at>=? AND created_at<?",
            (today_start, tomorrow_start),
        ).fetchone()["c"],
        "today_visitors": db.execute(
            "SELECT COUNT(*) AS c FROM visitors WHERE last_seen_at>=? AND last_seen_at<?",
            (today_start, tomorrow_start),
        ).fetchone()["c"],
        "yesterday_purchases": db.execute(
            "SELECT COUNT(*) AS c FROM purchase_requests WHERE created_at>=? AND created_at<?",
            (yesterday_start, today_start_for_yesterday),
        ).fetchone()["c"],
        "yesterday_approved": db.execute(
            "SELECT COUNT(*) AS c FROM purchase_requests WHERE status='approved' AND created_at>=? AND created_at<?",
            (yesterday_start, today_start_for_yesterday),
        ).fetchone()["c"],
        "yesterday_rejected": db.execute(
            "SELECT COUNT(*) AS c FROM purchase_requests WHERE status='rejected' AND created_at>=? AND created_at<?",
            (yesterday_start, today_start_for_yesterday),
        ).fetchone()["c"],
        "yesterday_visitors": db.execute(
            "SELECT COUNT(*) AS c FROM visitors WHERE last_seen_at>=? AND last_seen_at<?",
            (yesterday_start, today_start_for_yesterday),
        ).fetchone()["c"],
        "server_now": format_tehran(now_iso()),
        "server_day": to_tehran_adjusted(datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))).strftime("%A"),
    }
    return jsonify({"ok": True, "stats": stats, "online_by_page": online_by_page})


@app.post("/admin/api/reports/<int:report_id>/reply")
@admin_required
def admin_reply_report(report_id):
    reply_text = request.form.get("reply_text", "").strip()
    if not reply_text:
        return jsonify({"ok": False, "message": "متن پاسخ اجباری است."}), 400

    db = get_db()
    report = db.execute("SELECT id FROM reports WHERE id=?", (report_id,)).fetchone()
    if not report:
        return jsonify({"ok": False, "message": "ریپورت پیدا نشد."}), 404
    db.execute(
        "UPDATE reports SET admin_reply=?, replied_at=?, user_seen_at=NULL WHERE id=?",
        (reply_text, now_iso(), report_id),
    )
    db.commit()
    return jsonify({"ok": True})


@app.post("/admin/api/settings")
@admin_required
def admin_update_settings():
    db = get_db()
    site_update_mode = "1" if request.form.get("site_update_mode") == "1" else "0"
    site_domain_move_mode = "1" if request.form.get("site_domain_move_mode") == "1" else "0"
    site_domain_move_target = (request.form.get("site_domain_move_target") or "").strip() or DEFAULT_SITE_DOMAIN_MOVE_TARGET
    maintenance_fallback_url = (request.form.get("maintenance_fallback_url") or "").strip() or "http://mxdomain.top:5000"
    try:
        utc_adjust_hours = int(request.form.get("utc_adjust_hours") or DEFAULT_UTC_ADJUST_HOURS)
    except Exception:
        return jsonify({"ok": False, "message": "utc_adjust_hours نامعتبر است."}), 400
    try:
        max_devices = int(request.form.get("max_devices_per_user") or DEFAULT_MAX_DEVICES_PER_USER)
    except Exception:
        return jsonify({"ok": False, "message": "max_devices_per_user نامعتبر است."}), 400

    updates = {
        "site_update_mode": site_update_mode,
        "site_domain_move_mode": site_domain_move_mode,
        "site_domain_move_target": site_domain_move_target,
        "utc_adjust_hours": str(utc_adjust_hours),
        "max_devices_per_user": str(max(1, min(10, max_devices))),
        "maintenance_fallback_url": maintenance_fallback_url,
    }
    for key, value in updates.items():
        db.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES(?,?,?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (key, value, now_iso()),
        )
        mongo_upsert(
            "app_settings",
            {"key": key},
            {"key": key, "value": value, "updated_at": now_iso()},
        )
    db.commit()
    return jsonify({"ok": True, "message": "تنظیمات ذخیره شد."})


@app.get("/admin/api/backup-db")
@admin_required
def admin_backup_db():
    return send_file(DB_PATH, as_attachment=True, download_name=f"data-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.db")


@app.get("/admin/receipt/<filename>")
@admin_required
def admin_view_receipt(filename):
    full = os.path.join(RECEIPTS_DIR, filename)
    if not os.path.exists(full):
        abort(404)
    return send_file(full)

@app.route("/.well-known/acme-challenge/<filename>")
def acme_challenge(filename):
    return send_file(
        os.path.join(BASE_DIR, ".well-known", "acme-challenge", filename)
    )

def create_app():
    init_db()      # دیتابیس هنگام اجرا ساخته می‌شود
    return app     # برنامه را به Gunicorn می‌دهیم

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
