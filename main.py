import os
import re
import secrets
import string
import json
import uuid
import zipfile
import time
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO
from urllib import request as urllib_request
from zoneinfo import ZoneInfo

from flask import (
    Flask,
    abort,
    flash,
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
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
RECEIPTS_DIR = os.path.join(UPLOAD_DIR, "receipts")
VIDEOS_DIR = os.path.join(UPLOAD_DIR, "videos")
SAMPLES_DIR = os.path.join(UPLOAD_DIR, "samples")

ALLOWED_RECEIPT_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_ARCHIVE_EXTENSIONS = {"zip"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-now")
app.config["ADMIN_USER"] = os.environ.get("ADMIN_USER", "admin")
app.config["ADMIN_PASS"] = os.environ.get("ADMIN_PASS", "mx9091")

TEHRAN_TZ = ZoneInfo("Asia/Tehran")
DEFAULT_SITE_DOMAIN_MOVE_TARGET = "https://mxdomain.liara.run"
DEFAULT_UTC_ADJUST_HOURS = 4
DEFAULT_MAX_DEVICES_PER_USER = 2
REMOTE_FILE_SIZE_TIMEOUT_SECONDS = 1.2
REMOTE_FILE_SIZE_CACHE_TTL_SECONDS = 6 * 60 * 60
REMOTE_FILE_SIZE_MAX_NETWORK_CHECKS_PER_REQUEST = 15
_remote_file_size_cache: dict[str, tuple[float, str]] = {}

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
    "درحال بررسی پرداختت هستیم «چند ساعت» طول میکشه لطفا تا اتمام این فرایند صبور باشید\n\n"
    "منتظر ادمین بمونید تا در اولین فرصت فیش رو تایید کند تا دسترسی فیلم ها براتون باز بشه و بتونید دانلود کنید\n\n"
)

CLIENT_APPROVED_TEXT = (
    "مرسى كه خريد كرديد.\n"
    "توجه كنيد خريد شما در اينجا فقط با همين دستگاه قابل نمايشه اگر دسته بندى براى شما فعال نشده لطفا تا تاييد ادمين صبر كنيد\n"
    "توجه كنيد درصورتى كه فيش فيك ارسال كنيد وضعيتتون ثابت ميمونه و ممكن است بن بشيد.\n"
    "اكر دوباره خواستيد خريدى بكنيد ميتونيد مجدد دريافت ويديو رو بزنيد و دسته بندى ديكرى را بخريد."
)


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def normalize_report_messages(raw_messages, fallback_text: str = "", fallback_at: str | None = None):
    normalized = []
    if isinstance(raw_messages, list):
        for m in raw_messages:
            if isinstance(m, dict):
                sender = "admin" if m.get("sender") == "admin" else "user"
                text = str(m.get("text") or "").strip()
                if not text:
                    continue
                normalized.append({
                    "id": str(m.get("id") or uuid.uuid4().hex[:12]),
                    "sender": sender,
                    "text": text,
                    "at": m.get("at") or fallback_at or now_iso(),
                })
            elif isinstance(m, str) and m.strip():
                normalized.append({"id": uuid.uuid4().hex[:12], "sender": "user", "text": m.strip(), "at": fallback_at or now_iso()})
    if not normalized and fallback_text.strip():
        normalized = [{"id": uuid.uuid4().hex[:12], "sender": "user", "text": fallback_text.strip(), "at": fallback_at or now_iso()}]
    return normalized


def save_receipt_file(receipt_file, final_name: str) -> tuple[str, str]:
    local_path = os.path.join(RECEIPTS_DIR, final_name)
    receipt_file.save(local_path)
    return "local", final_name


def normalize_receipt_name(raw_name: str, mimetype: str | None = None) -> str:
    base = secure_filename(raw_name or "").strip("._ ")
    if not base:
        base = "receipt"
    name, ext = os.path.splitext(base)
    ext = (ext or "").lower()
    if not ext:
        lowered = base.lower()
        for guess in ["jpg", "jpeg", "png", "webp"]:
            if lowered.endswith(f"_{guess}"):
                name = base[: -(len(guess) + 1)]
                ext = f".{guess}"
                break
    if not ext and mimetype:
        mt = mimetype.lower()
        if "jpeg" in mt or "jpg" in mt:
            ext = ".jpg"
        elif "png" in mt:
            ext = ".png"
        elif "webp" in mt:
            ext = ".webp"
    ext = ext if ext in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"
    clean_name = secure_filename(name) or "receipt"
    return f"{clean_name}{ext}"


def format_clock(iso_value: str | None) -> str:
    if not iso_value:
        return "-"
    try:
        dt = datetime.fromisoformat(str(iso_value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        local_dt = dt.astimezone(TEHRAN_TZ)
        return local_dt.strftime("%I:%M:%S %p")
    except Exception:
        return str(iso_value)


def format_day(iso_value: str | None) -> str:
    if not iso_value:
        return "-"
    try:
        dt = datetime.fromisoformat(str(iso_value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        local_dt = dt.astimezone(TEHRAN_TZ)
        return local_dt.strftime("%m/%d/%Y")
    except Exception:
        return "-"


def purchase_status_label(status: str | None, is_fake: bool = False) -> str:
    status_map = {
        "approved": "تایید شده",
        "rejected": "تایید نشده",
        "pending": "در انتظار بررسی",
        "fake": "تایید نشده",
    }
    base = status_map.get((status or "").strip(), "نامشخص")
    return f"{base} | فیک" if is_fake else base


def human_size(size_bytes: int | None) -> str:
    if not size_bytes or size_bytes <= 0:
        return "-"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size_bytes)
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    return f"{value:.1f} {units[idx]}"


def local_zip_info(file_path: str | None) -> tuple[int | None, str]:
    if not file_path:
        return None, "-"
    full = os.path.join(VIDEOS_DIR, file_path)
    if not os.path.exists(full):
        return None, "-"
    try:
        size = os.path.getsize(full)
    except Exception:
        size = 0
    file_count = None
    try:
        with zipfile.ZipFile(full) as zf:
            file_count = len([n for n in zf.namelist() if not n.endswith("/")])
    except Exception:
        file_count = None
    return file_count, human_size(size)


def remote_file_size(url: str | None, allow_network: bool = True) -> str:
    if not url:
        return "-"
    now_ts = time.time()
    cached = _remote_file_size_cache.get(url)
    if cached and (now_ts - cached[0] <= REMOTE_FILE_SIZE_CACHE_TTL_SECONDS):
        return cached[1]
    if not allow_network:
        return cached[1] if cached else "-"
    try:
        req = urllib_request.Request(url, method="HEAD")
        with urllib_request.urlopen(req, timeout=REMOTE_FILE_SIZE_TIMEOUT_SECONDS) as resp:
            content_length = resp.headers.get("Content-Length")
            if content_length and str(content_length).isdigit():
                val = human_size(int(content_length))
                _remote_file_size_cache[url] = (now_ts, val)
                return val
    except Exception:
        pass
    _remote_file_size_cache[url] = (now_ts, "-")
    return "-"


def build_admin_purchase_rows(mdb, cat_by_id: dict[int, dict], users_by_id: dict[int, dict], limit: int = 300):
    access_rows = list(mdb["user_access"].find({}, {"_id": 0, "user_id": 1, "category_id": 1}))
    access_by_user: dict[int, list[int]] = {}
    for ua in access_rows:
        uid = ua.get("user_id")
        cid = ua.get("category_id")
        if uid is None or cid is None:
            continue
        access_by_user.setdefault(uid, []).append(cid)
    rows = []
    for r in mdb["purchase_requests"].find({}, {"_id": 0}).sort("id", -1).limit(limit):
        user = users_by_id.get(r.get("user_id"), {})
        req_cat = cat_by_id.get(r.get("requested_category_id"), {})
        granted_ids = access_by_user.get(r.get("user_id"), [])
        granted = [cat_by_id.get(cid, {}).get("title") for cid in granted_ids if cat_by_id.get(cid)]
        req_is_fake = bool(r.get("is_fake_receipt"))
        rows.append({
            **r,
            "device_id": user.get("device_id", "-"),
            "requested_category": req_cat.get("title", "-"),
            "category_titles": ", ".join(granted) if granted else "-",
            "created_at_clock": format_clock(r.get("created_at")),
            "created_at_day": format_day(r.get("created_at")),
            "status_label": purchase_status_label(r.get("status"), req_is_fake),
            "is_fake_receipt": req_is_fake,
            "receipt_seen_at": r.get("receipt_seen_at"),
            "receipt_seen": bool(r.get("receipt_seen_at")),
        })
    return rows


def build_admin_reports(mdb, cat_by_id: dict[int, dict], limit: int = 300):
    reports = []
    access_rows = list(mdb["user_access"].find({}, {"_id": 0, "user_id": 1, "category_id": 1}))
    access_by_user: dict[int, list[int]] = {}
    for ua in access_rows:
        uid = ua.get("user_id")
        cid = ua.get("category_id")
        if uid is None or cid is None:
            continue
        access_by_user.setdefault(uid, []).append(cid)
    for rp in mdb["reports"].find({}, {"_id": 0}).sort("id", -1).limit(limit):
        rp = dict(rp or {})
        user_id = rp.get("user_id")
        category_titles = [cat_by_id.get(cid, {}).get("title") for cid in access_by_user.get(user_id, []) if cat_by_id.get(cid)]
        rp["category_titles"] = ", ".join(category_titles) if category_titles else "-"
        normalized_messages = normalize_report_messages(rp.get("messages"), (rp.get("report_text") or "").strip(), rp.get("created_at"))
        rp["messages"] = normalized_messages
        rp["created_at_clock"] = format_clock(rp.get("created_at"))
        rp["created_at_day"] = format_day(rp.get("created_at"))
        for msg in rp["messages"]:
            msg["at_clock"] = format_clock(msg.get("at"))
            msg["at_day"] = format_day(msg.get("at"))
        reports.append(rp)
    return reports


def get_mongo_client():
    if "mongo_client" in app.extensions:
        return app.extensions["mongo_client"]
    #uri = os.environ.get("MONGO_URI", "mongodb://mani:mani2244@185.8.172.161:27017/site_mx2?authSource=admin")
    uri = os.environ.get("MONGO_URI", "mongodb://mani:mani2244@127.0.0.1:27017/site_mx2?authSource=admin")
    db_name = os.environ.get("MONGO_DB_NAME", "").strip()
    try:
        pymongo_mod = __import__("pymongo")
        client = pymongo_mod.MongoClient(uri, serverSelectionTimeoutMS=8000, connectTimeoutMS=8000)
        client.admin.command("ping")
        if not db_name:
            parsed = uri.rsplit("/", 1)[-1].split("?", 1)[0].strip()
            db_name = parsed if parsed else "site_mx2"
        app.extensions["mongo_client"] = client
        app.extensions["mongo_db_name"] = db_name
        app.extensions["mongo_error"] = None
        print(f"[mongo] connected uri={uri} db={db_name}")
        return client
    except Exception:
        app.extensions["mongo_client"] = None
        app.extensions["mongo_db_name"] = db_name or "site_mx2"
        app.extensions["mongo_error"] = "cannot-connect"
        print(f"[mongo] connection failed uri={uri}. set MONGO_URI correctly and install pymongo.")
        return None


def mongo_db():
    client = get_mongo_client()
    if not client:
        return None
    return client[app.extensions.get("mongo_db_name", "site_mx2")]


def mongo_next_id(name: str) -> int:
    mdb = mongo_db()
    if mdb is None:
        raise RuntimeError("MongoDB unavailable")
    row = mdb["counters"].find_one({"_id": name})
    if not row:
        mdb["counters"].insert_one({"_id": name, "v": 1})
        return 1
    value = int(row.get("v", 0)) + 1
    mdb["counters"].update_one({"_id": name}, {"$set": {"v": value}})
    return value


def get_setting(key: str, default: str) -> str:
    mdb = mongo_db()
    if mdb is None:
        return default
    row = mdb["app_settings"].find_one({"key": key})
    return row.get("value") if row else default


def setting_bool(key: str, default: bool = False) -> bool:
    return get_setting(key, "1" if default else "0") == "1"


def setting_int(key: str, default: int) -> int:
    try:
        return int(get_setting(key, str(default)))
    except Exception:
        return default


def duration_ms_to_seconds_text(value_ms: int) -> str:
    try:
        seconds = max(1, int(round(int(value_ms) / 1000)))
    except Exception:
        seconds = 5
    return str(seconds)


def seed_mongo():
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    mdb = mongo_db()
    if mdb is None:
        print("[mongo] seed skipped; mongodb unavailable")
        return
    defaults = {
        "site_update_mode": "0",
        "site_domain_move_mode": "0",
        "site_domain_move_target": DEFAULT_SITE_DOMAIN_MOVE_TARGET,
        "utc_adjust_hours": str(DEFAULT_UTC_ADJUST_HOURS),
        "max_devices_per_user": str(DEFAULT_MAX_DEVICES_PER_USER),
        "maintenance_fallback_url": "http://mxdomain.top:5000",
        "purchase_enabled": "1",
        "purchase_disabled_message": "فعلا خرید بسته است. لطفا بعدا دوباره امتحان کنید.",
        "global_notice_enabled": "0",
        "global_notice_text": "",
        "global_notice_color": "#0ea5e9",
        "global_notice_duration_ms": "5000",
        "global_notice_pages": "home,my-videos,buy",
        "global_notice_position": "top-right",
        "global_notice_font_size_px": "14",
        "global_notice_max_width_px": "320",
        "ticket_ready_messages_json": "[]",
    }
    for k, v in defaults.items():
        mdb["app_settings"].update_one({"key": k}, {"$setOnInsert": {"key": k, "value": v, "updated_at": now_iso()}}, upsert=True)


def parse_user_agent(user_agent: str) -> dict[str, str]:
    ua = (user_agent or "").lower()
    browser_name = "Unknown"
    if "crios" in ua:
        browser_name = "Chrome iOS"
    elif "chrome" in ua:
        browser_name = "Chrome"
    elif "firefox" in ua:
        browser_name = "Firefox"
    elif "safari" in ua:
        browser_name = "Safari"
    os_name = "Unknown"
    if "iphone" in ua or "ipad" in ua:
        os_name = "iOS"
    elif "android" in ua:
        os_name = "Android"
    elif "windows" in ua:
        os_name = "Windows"
    device_model = "Desktop"
    if "iphone" in ua:
        device_model = "iPhone"
    elif "ipad" in ua:
        device_model = "iPad"
    elif "android" in ua:
        device_model = "Android"
    return {"browser_name": browser_name, "os_name": os_name, "device_model": device_model}


def register_visit(device_id: str):
    if not device_id:
        return
    mdb = mongo_db()
    if mdb is None:
        return
    meta = parse_user_agent(request.headers.get("User-Agent", ""))
    print(
        f"[visit] device_id={device_id} browser={meta.get('browser_name')} "
        f"os={meta.get('os_name')} model={meta.get('device_model')}"
    )
    row = mdb["visitors"].find_one({"device_id": device_id})
    if not row:
        mdb["visitors"].insert_one({
            "id": mongo_next_id("visitors"),
            "device_id": device_id,
            "username": None,
            "first_seen_at": now_iso(),
            "last_seen_at": now_iso(),
            "visit_count": 1,
            "purchase_count": 0,
            "report_count": 0,
            "is_banned": 0,
            "user_agent": request.headers.get("User-Agent", ""),
            **meta,
        })
    else:
        mdb["visitors"].update_one({"device_id": device_id}, {"$inc": {"visit_count": 1}, "$set": {"last_seen_at": now_iso(), **meta}})


def generate_access_code(length: int = 16) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_device_id_from_request(payload: dict | None = None) -> str:
    if payload and payload.get("device_id"):
        return str(payload.get("device_id")).strip()
    return (request.form.get("device_id") or request.args.get("device_id") or request.cookies.get("mx_device_id") or "").strip()


def current_auth_user():
    mdb = mongo_db()
    if mdb is None:
        return None
    code = session.get("auth_access_code")
    if not code:
        return None
    return mdb["auth_users"].find_one({"access_code": code})


def bind_device(access_code: str, device_id: str):
    mdb = mongo_db()
    if mdb is None:
        return False, "MongoDB unavailable"
    max_devices = setting_int("max_devices_per_user", DEFAULT_MAX_DEVICES_PER_USER)
    coll = mdb["auth_user_devices"]
    row = coll.find_one({"access_code": access_code, "device_id": device_id})
    if row:
        coll.update_one({"_id": row["_id"]}, {"$set": {"last_seen_at": now_iso()}})
        return True, ""
    if coll.count_documents({"access_code": access_code}) >= max_devices:
        return False, f"این اکانت فقط روی {max_devices} دستگاه مجاز است."
    coll.insert_one({"id": mongo_next_id("auth_user_devices"), "access_code": access_code, "device_id": device_id, "first_seen_at": now_iso(), "last_seen_at": now_iso()})
    return True, ""


def require_auth():
    did = get_device_id_from_request()
    if not did:
        return None, (jsonify({"ok": False, "message": "شناسه دستگاه لازم است."}), 400)
    mdb = mongo_db()
    if mdb is None:
        return None, (jsonify({"ok": False, "message": "MongoDB unavailable"}), 503)
    user = mdb["users"].find_one({"device_id": did})
    if not user:
        alias = did.replace("-", "")[:12] or uuid.uuid4().hex[:12]
        user = {"id": mongo_next_id("users"), "device_id": did, "full_name": f"user-{alias}", "phone": f"device-{alias}", "is_banned": 0, "created_at": now_iso(), "updated_at": now_iso()}
        mdb["users"].insert_one(user)
    return (user, did), None


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged"):
            return redirect(url_for("admin_login"))
        return func(*args, **kwargs)
    return wrapper


@app.before_request
def modes():
    path = request.path or "/"
    if path.startswith("/khnowledge-mx") or path.startswith("/static") or path in {"/site-update", "/site-domain-moved", "/iphone-chrome-required", "/api/system-status"}:
        return None
    if setting_bool("site_update_mode", False):
        if path.startswith("/api/"):
            return jsonify({"ok": False, "message": "سایت در حال بروزرسانی است."}), 503
        return redirect(url_for("site_update_page"))
    if setting_bool("site_domain_move_mode", False):
        target = get_setting("site_domain_move_target", DEFAULT_SITE_DOMAIN_MOVE_TARGET)
        if path.startswith("/api/"):
            return jsonify({"ok": False, "message": "سایت منتقل شده", "target_url": target}), 503
        return redirect(url_for("site_domain_move_page"))
    did = (request.cookies.get("mx_device_id") or "").strip()
    if did and path not in {"/site-down", "/messages", "/api/report", "/api/my-report-replies", "/api/my-report-replies/mark-seen"}:
        mdb = mongo_db()
        if mdb is not None:
            v = mdb["visitors"].find_one({"device_id": did}, {"_id": 0, "is_banned": 1})
            if v and int(v.get("is_banned", 0)) == 1:
                if path.startswith("/api/"):
                    return jsonify({"ok": False, "message": "سایت از دسترس خارج شده"}), 503
                return redirect(url_for("site_down_page"))
    return None


@app.route("/")
def home():
    mdb = mongo_db()
    categories = list(mdb["categories"].find({}, {"_id": 0}).sort("id", 1)) if mdb is not None else []
    total_purchases = mdb["user_access"].count_documents({}) if mdb is not None else 0
    testimonials = []
    if mdb is not None:
        cat_by_id = {c["id"]: c for c in categories}
        users_by_device = {u.get("device_id"): u for u in mdb["users"].find({}, {"_id": 0, "id": 1, "device_id": 1})}
        for t in mdb["testimonials"].find({"status": "approved"}, {"_id": 0}).sort("id", -1).limit(160):
            category_titles = t.get("category_titles")
            if not category_titles:
                device_id = t.get("device_id")
                user = users_by_device.get(device_id) if device_id else None
                titles = []
                if user:
                    for ua in mdb["user_access"].find({"user_id": user.get("id")}, {"_id": 0, "category_id": 1}):
                        c = cat_by_id.get(ua.get("category_id"))
                        if c:
                            titles.append(c.get("title"))
                category_titles = " | ".join(titles) if titles else "-"
            testimonials.append({
                **t,
                "display_name": t.get("display_name") or t.get("author_name") or "کاربر",
                "content": t.get("content") or t.get("testimonial_text") or "",
                "category_titles": category_titles,
            })
    return render_template("home.html", categories=categories, testimonials=testimonials, total_purchases=total_purchases)


@app.route("/buy/<slug>")
def buy_page(slug):
    mdb = mongo_db()
    category = mdb["categories"].find_one({"slug": slug}, {"_id": 0}) if mdb is not None else None
    if not category:
        abort(404)
    return render_template("buy.html", category=category)


@app.route("/my-videos")
def my_videos_page():
    return render_template("my_videos.html")


@app.route("/messages")
def messages_page():
    return render_template("messages.html")


@app.get("/login")
def login_page():
    return redirect(url_for("home"))


@app.post("/api/auth/login")
def api_auth_login():
    return jsonify({"ok": False, "message": "سیستم کد دسترسی حذف شده است."}), 410


@app.post("/api/auth/create-code")
def api_auth_create_code():
    return jsonify({"ok": False, "message": "سیستم کد دسترسی حذف شده است."}), 410


@app.get("/api/auth/status")
def api_auth_status():
    return jsonify({"ok": True, "logged_in": True, "mode": "device_id"})


@app.get("/api/auth/my-code")
def api_auth_my_code():
    return jsonify({"ok": False, "message": "سیستم کد دسترسی حذف شده است."}), 410


@app.post("/api/auth/logout")
def api_auth_logout():
    return jsonify({"ok": True})


@app.get("/api/public-stats")
def api_public_stats():
    mdb = mongo_db()
    total_active_subscriptions = mdb["user_access"].count_documents({}) if mdb is not None else 0
    return jsonify({
        "ok": True,
        "total_purchases": int(total_active_subscriptions),
        "total_active_subscriptions": int(total_active_subscriptions),
        "updated_at": now_iso(),
    })


@app.post("/api/register-visit")
def api_register_visit():
    payload = request.get_json(silent=True) or {}
    did = (payload.get("device_id") or "").strip()
    if not did:
        return jsonify({"ok": False, "message": "شناسه دستگاه لازم است."}), 400
    register_visit(did)
    mdb = mongo_db()
    v = mdb["visitors"].find_one({"device_id": did}) if mdb is not None else None
    if v and int(v.get("is_banned", 0)) == 1:
        return jsonify({"ok": False, "message": "مسدود شده"}), 403
    return jsonify({"ok": True})


@app.post("/api/presence")
def api_presence():
    payload = request.get_json(silent=True) or {}
    did = (payload.get("device_id") or "").strip()
    page_key = (payload.get("page_key") or "unknown").strip()[:80]
    if not did:
        return jsonify({"ok": False, "message": "شناسه دستگاه لازم است."}), 400
    register_visit(did)
    mdb = mongo_db()
    if mdb is not None:
        mdb["presence_sessions"].update_one({"device_id": did}, {"$set": {"page_key": page_key, "updated_at": now_iso()}}, upsert=True)
    return jsonify({"ok": True})


@app.post("/api/submit-request")
def submit_request():
    auth, err = require_auth()
    if err:
        return err
    _user, did = auth
    cid = request.form.get("category_id", "").strip()
    note = (request.form.get("request_note") or "").strip()
    receipt = request.files.get("receipt")
    if not cid or not receipt:
        return jsonify({"ok": False, "message": "اطلاعات ناقص"}), 400
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    if not setting_bool("purchase_enabled", True):
        return jsonify({"ok": False, "message": get_setting("purchase_disabled_message", "فعلا خرید بسته است.")}), 403
    category = mdb["categories"].find_one({"id": int(cid)})
    if not category:
        return jsonify({"ok": False, "message": "دسته نامعتبر"}), 400
    user = mdb["users"].find_one({"device_id": did})
    if not user:
        alias = did.replace("-", "")[:12] or uuid.uuid4().hex[:12]
        user = {"id": mongo_next_id("users"), "device_id": did, "full_name": f"user-{alias}", "phone": f"device-{alias}", "is_banned": 0, "created_at": now_iso(), "updated_at": now_iso()}
        mdb["users"].insert_one(user)
    if mdb["purchase_requests"].find_one({"user_id": user["id"], "status": "pending"}):
        return jsonify({"ok": False, "message": CLIENT_WAITING_REVIEW_TEXT, "pending_exists": True}), 409
    receipt_name = normalize_receipt_name(receipt.filename, receipt.mimetype)
    ext = receipt_name.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_RECEIPT_EXTENSIONS:
        return jsonify({"ok": False, "message": "فرمت رسید مجاز نیست."}), 400
    final_name = f"{uuid.uuid4().hex}_{receipt_name}"
    storage_type, receipt_path = save_receipt_file(receipt, final_name)
    mdb["purchase_requests"].insert_one({"id": mongo_next_id("purchase_requests"), "user_id": user["id"], "requested_category_id": category["id"], "receipt_path": receipt_path, "receipt_storage": storage_type, "status": "pending", "admin_note": None, "user_note": note or None, "created_at": now_iso(), "reviewed_at": None})
    mdb["visitors"].update_one({"device_id": did}, {"$inc": {"purchase_count": 1}, "$set": {"last_seen_at": now_iso()}}, upsert=True)
    return jsonify({"ok": True, "message": CLIENT_WAITING_REVIEW_TEXT, "next_url": "/my-videos"})


@app.get("/api/purchase-status")
def purchase_status():
    did = request.args.get("device_id", "").strip()
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    user = mdb["users"].find_one({"device_id": did})
    if not user:
        return jsonify({"ok": True, "has_pending": False})
    latest = mdb["purchase_requests"].find_one({"user_id": user["id"]}, sort=[("id", -1)])
    return jsonify({"ok": True, "latest_status": latest.get("status") if latest else None, "has_pending": bool(latest and latest.get("status") == "pending"), "is_rejected": bool(latest and latest.get("status") == "rejected"), "message": CLIENT_WAITING_REVIEW_TEXT, "rejected_note": latest.get("admin_note") if latest else None})


@app.post("/api/report")
def submit_report():
    auth, err = require_auth()
    if err:
        return err
    _u, did = auth
    report_type = request.form.get("report_type", "").strip()
    report_text = request.form.get("report_text", "").strip()
    if not report_type or not report_text:
        return jsonify({"ok": False, "message": "اطلاعات ناقص"}), 400
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    user = mdb["users"].find_one({"device_id": did})
    uid = user.get("id") if user else None
    now = now_iso()
    mdb["reports"].insert_one({
        "id": mongo_next_id("reports"),
        "device_id": did,
        "user_id": uid,
        "reporter_name": f"کاربر {uid}" if uid else "کاربر",
        "report_type": report_type,
        "report_text": report_text,
        "admin_reply": None,
        "replied_at": None,
        "user_seen_at": None,
        "created_at": now,
        "messages": [{"sender": "user", "text": report_text, "at": now}],
    })
    return jsonify({"ok": True, "message": "ریپورت ثبت شد"})


@app.post("/api/testimonials")
def submit_testimonial():
    auth, err = require_auth()
    if err:
        return err
    user, did = auth
    payload = request.form or {}
    text = (payload.get("testimonial_text") or "").strip()
    name = (payload.get("testimonial_name") or "").strip() or f"کاربر {user.get('id')}"
    if not text:
        return jsonify({"ok": False, "message": "متن نظر خالی است."}), 400
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    has_access = mdb["user_access"].count_documents({"user_id": user.get("id")}) > 0
    if not has_access:
        return jsonify({"ok": False, "message": "ثبت نظر فقط برای کاربرانی که اشتراک فعال دارند باز است."}), 403
    titles = []
    for ua in mdb["user_access"].find({"user_id": user.get("id")}, {"_id": 0, "category_id": 1}):
        cat = mdb["categories"].find_one({"id": ua.get("category_id")}, {"_id": 0, "title": 1})
        if cat:
            titles.append(cat.get("title"))
    mdb["testimonials"].insert_one({"id": mongo_next_id("testimonials"), "user_id": user.get("id"), "display_name": name, "content": text, "testimonial_text": text, "author_name": name, "category_titles": " | ".join(titles) if titles else "-", "device_id": did or None, "status": "pending", "created_at": now_iso()})
    return jsonify({"ok": True, "message": "نظر شما ثبت شد و بعد از تایید نمایش داده می‌شود."})


@app.get("/api/my-report-replies")
def my_replies():
    did = request.args.get("device_id", "").strip()
    mdb = mongo_db()
    if mdb is None or not did:
        return jsonify({"ok": True, "items": [], "unseen_count": 0})
    rows = list(mdb["reports"].find({"device_id": did}, {"_id": 0}).sort("id", -1).limit(30))
    unseen = 0
    for x in rows:
        messages = normalize_report_messages(x.get("messages"), x.get("report_text") or "", x.get("created_at"))
        x["messages"] = messages
        has_admin = any(m.get("sender") == "admin" for m in messages)
        if has_admin and not x.get("user_seen_at"):
            unseen += 1
    ready_messages = []
    if session.get("admin_logged"):
        try:
            ready_messages = json.loads(get_setting("ticket_ready_messages_json", "[]"))
            if not isinstance(ready_messages, list):
                ready_messages = []
        except Exception:
            ready_messages = []
    return jsonify({"ok": True, "items": rows, "unseen_count": unseen, "ready_messages": ready_messages})


@app.post("/api/my-report-replies/mark-seen")
def mark_replies_seen():
    did = get_device_id_from_request(request.get_json(silent=True) or {})
    mdb = mongo_db()
    if mdb is None or not did:
        return jsonify({"ok": False}), 400
    mdb["reports"].update_many({"device_id": did, "user_seen_at": None}, {"$set": {"user_seen_at": now_iso()}})
    return jsonify({"ok": True})


@app.post("/api/reports/<int:rid>/reply")
def user_reply_report(rid):
    payload = request.get_json(silent=True) or {}
    did = get_device_id_from_request(payload)
    text = (payload.get("text") or "").strip()
    if not did or not text:
        return jsonify({"ok": False, "message": "اطلاعات ناقص"}), 400
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    row = mdb["reports"].find_one({"id": rid, "device_id": did})
    if not row:
        return jsonify({"ok": False, "message": "تیکت پیدا نشد"}), 404
    msgs = normalize_report_messages(row.get("messages"), row.get("report_text") or "", row.get("created_at"))
    msgs.append({"id": uuid.uuid4().hex[:12], "sender": "user", "text": text, "at": now_iso()})
    mdb["reports"].update_one({"id": rid}, {"$set": {"messages": msgs, "report_text": text, "user_seen_at": None}})
    return jsonify({"ok": True})


@app.post("/api/reports/<int:rid>/messages/<msg_id>/delete")
def user_delete_report_message(rid, msg_id):
    payload = request.get_json(silent=True) or {}
    did = get_device_id_from_request(payload)
    mdb = mongo_db()
    if mdb is None or not did:
        return jsonify({"ok": False, "message": "اطلاعات ناقص"}), 400
    row = mdb["reports"].find_one({"id": rid, "device_id": did}, {"_id": 0})
    if not row:
        return jsonify({"ok": False, "message": "تیکت پیدا نشد"}), 404
    msgs = normalize_report_messages(row.get("messages"), row.get("report_text") or "", row.get("created_at"))
    next_msgs = [m for m in msgs if not (str(m.get("id")) == str(msg_id) and m.get("sender") == "user")]
    if len(next_msgs) == len(msgs):
        return jsonify({"ok": False, "message": "این پیام قابل حذف نیست."}), 400
    mdb["reports"].update_one({"id": rid}, {"$set": {"messages": next_msgs}})
    return jsonify({"ok": True})


@app.post("/api/reports/<int:rid>/delete")
def user_delete_report(rid):
    payload = request.get_json(silent=True) or {}
    did = get_device_id_from_request(payload)
    mdb = mongo_db()
    if mdb is None or not did:
        return jsonify({"ok": False, "message": "اطلاعات ناقص"}), 400
    res = mdb["reports"].delete_one({"id": rid, "device_id": did})
    if res.deleted_count < 1:
        return jsonify({"ok": False, "message": "تیکت پیدا نشد"}), 404
    return jsonify({"ok": True})


@app.get("/api/category-likes")
def category_likes():
    did = request.args.get("device_id", "").strip()
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    counts = {}
    for row in mdb["category_likes"].aggregate([{"$group": {"_id": "$category_id", "c": {"$sum": 1}}}]):
        counts[str(row["_id"])] = row["c"]
    liked = [x["category_id"] for x in mdb["category_likes"].find({"device_id": did}, {"_id": 0, "category_id": 1})] if did else []
    return jsonify({"ok": True, "counts": counts, "liked": liked})


@app.post("/api/category-likes/toggle")
def toggle_like():
    payload = request.get_json(silent=True) or {}
    did = (payload.get("device_id") or "").strip()
    cid = int(payload.get("category_id") or 0)
    desired = bool(payload.get("liked"))
    mdb = mongo_db()
    if mdb is None or not did or not cid:
        return jsonify({"ok": False}), 400
    coll = mdb["category_likes"]
    exists = coll.find_one({"device_id": did, "category_id": cid})
    if desired and not exists:
        coll.insert_one({"id": mongo_next_id("category_likes"), "device_id": did, "category_id": cid, "created_at": now_iso()})
    if not desired and exists:
        coll.delete_one({"_id": exists["_id"]})
    count = coll.count_documents({"category_id": cid})
    return jsonify({"ok": True, "liked": desired, "count": count})


@app.get("/api/my-videos")
def api_my_videos():
    did = request.args.get("device_id", "").strip()
    mdb = mongo_db()
    if mdb is None or not did:
        return jsonify({"ok": False, "message": "شناسه دستگاه لازم است."}), 400
    user = mdb["users"].find_one({"device_id": did})
    if not user:
        return jsonify({"ok": True, "approved_text": "هنوز خریدی ثبت نشده است. ابتدا فیش را ارسال کنید.", "categories": []})
    latest = mdb["purchase_requests"].find_one({"user_id": user["id"]}, sort=[("id", -1)])
    access = list(mdb["user_access"].find({"user_id": user["id"]}, {"_id": 0}))
    categories = []
    for ua in access:
        cat = mdb["categories"].find_one({"id": ua["category_id"]}, {"_id": 0})
        if not cat:
            continue
        vids = list(mdb["videos"].find({"category_id": cat["id"]}, {"_id": 0}))
        for v in vids:
            v["watch_url"] = f"/api/watch/{v['id']}"
            v["type"] = v.get("source_type")
            if v.get("source_type") == "file":
                cnt, sz = local_zip_info(v.get("file_path"))
                v["file_count"] = cnt
                v["file_size"] = sz
            else:
                v["file_count"] = None
                v["file_size"] = remote_file_size(v.get("external_url"))
        categories.append({"id": cat["id"], "title": cat["title"], "videos": vids})
    approved_text = "هنوز خریدی ثبت نشده است. ابتدا فیش را ارسال کنید."
    if latest and latest.get("status") == "pending":
        approved_text = CLIENT_WAITING_REVIEW_TEXT
    elif latest and latest.get("status") == "rejected":
        note = (latest.get("admin_note") or "").strip()
        approved_text = f"درخواست شما رد شده است.{f' دلیل: {note}' if note else ''}"
    elif categories:
        approved_text = CLIENT_APPROVED_TEXT
    return jsonify({"ok": True, "approved_text": approved_text, "categories": categories})


@app.get("/api/my-videos/summary")
def api_my_videos_summary():
    did = request.args.get("device_id", "").strip()
    mdb = mongo_db()
    if mdb is None or not did:
        return jsonify({"ok": True, "total_categories": 0, "unseen_categories": 0})
    user = mdb["users"].find_one({"device_id": did})
    if not user:
        return jsonify({"ok": True, "total_categories": 0, "unseen_categories": 0})
    total = mdb["user_access"].count_documents({"user_id": user["id"]})
    seen = mdb["user_video_seen"].count_documents({"user_id": user["id"]})
    return jsonify({"ok": True, "total_categories": total, "unseen_categories": max(0, total - seen)})


@app.post("/api/my-videos/mark-seen")
def api_mark_seen():
    payload = request.get_json(silent=True) or {}
    did = get_device_id_from_request(payload)
    mdb = mongo_db()
    if mdb is None or not did:
        return jsonify({"ok": False}), 400
    user = mdb["users"].find_one({"device_id": did})
    if not user:
        return jsonify({"ok": True})
    for ua in mdb["user_access"].find({"user_id": user["id"]}, {"_id": 0}):
        mdb["user_video_seen"].update_one({"user_id": user["id"], "category_id": ua["category_id"]}, {"$set": {"seen_at": now_iso()}}, upsert=True)
    return jsonify({"ok": True})


@app.get("/api/watch/<int:video_id>")
def api_watch(video_id):
    mdb = mongo_db()
    if mdb is None:
        abort(404)
    video = mdb["videos"].find_one({"id": video_id}, {"_id": 0})
    if not video:
        abort(404)
    if video.get("source_type") == "url" and video.get("external_url"):
        return redirect(video["external_url"])
    fp = video.get("file_path")
    if not fp:
        abort(404)
    full = os.path.join(VIDEOS_DIR, fp)
    if not os.path.exists(full):
        abort(404)
    return send_file(full, as_attachment=True)


@app.get("/api/system-status")
def api_system_status():
    mongo_ok = mongo_db() is not None
    return jsonify(
        {
            "ok": True,
            "mongo_ok": mongo_ok,
            "mongo_db_name": app.extensions.get("mongo_db_name", "site_mx2"),
            "mongo_error": app.extensions.get("mongo_error"),
            "site_update_mode": setting_bool("site_update_mode", False),
            "site_domain_move_mode": setting_bool("site_domain_move_mode", False),
            "site_domain_move_target": get_setting("site_domain_move_target", DEFAULT_SITE_DOMAIN_MOVE_TARGET),
        }
    )


@app.route("/site-update")
def site_update_page():
    return render_template("site_update.html", fallback_url=get_setting("maintenance_fallback_url", "http://mxdomain.top:5000"))


@app.route("/site-domain-moved")
def site_domain_move_page():
    return render_template("site_domain_moved.html", target_url=get_setting("site_domain_move_target", DEFAULT_SITE_DOMAIN_MOVE_TARGET))


@app.route("/site-down")
def site_down_page():
    return render_template("site_down.html")


@app.route("/iphone-chrome-required")
def iphone_chrome_required_page():
    next_url = request.args.get("next", "/")
    return render_template("iphone_chrome_required.html", next_url=next_url)


@app.route("/khnowledge-mx/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("username") == app.config["ADMIN_USER"] and request.form.get("password") == app.config["ADMIN_PASS"]:
            session["admin_logged"] = True
            return redirect("/khnowledge-mx")
        flash("نام کاربری یا رمز اشتباه است.")
    return render_template("admin_login.html")


@app.route("/khnowledge-mx")
@admin_required
def admin_dashboard():
    mdb = mongo_db()
    base_stats = {"online_total": 0, "online_ios": 0, "online_android": 0, "online_windows": 0, "total_reports": 0, "total_visitors": 0, "total_purchases": 0, "approved_receipts": 0, "rejected_receipts": 0, "pending_receipts": 0, "today_purchases": 0, "today_approved": 0, "today_rejected": 0, "today_visitors": 0, "yesterday_purchases": 0, "yesterday_approved": 0, "yesterday_rejected": 0, "yesterday_visitors": 0, "active_last_minute": 0}
    if mdb is None:
        return render_template("admin_dashboard.html", requests_rows=[], categories=[], videos=[], reports=[], testimonials=[], visitors=[], activity_rows=[], online_by_page={}, stats=base_stats, visitors_search="", auth_users=[], server_now=datetime.now(TEHRAN_TZ).strftime("%I:%M:%S %p"), server_day=datetime.now(TEHRAN_TZ).strftime("%m/%d/%Y"), site_update_mode=setting_bool("site_update_mode", False), site_domain_move_mode=setting_bool("site_domain_move_mode", False), site_domain_move_target=get_setting("site_domain_move_target", DEFAULT_SITE_DOMAIN_MOVE_TARGET), utc_adjust_hours=setting_int("utc_adjust_hours", DEFAULT_UTC_ADJUST_HOURS), max_devices_per_user=setting_int("max_devices_per_user", DEFAULT_MAX_DEVICES_PER_USER), maintenance_fallback_url=get_setting("maintenance_fallback_url", "http://mxdomain.top:5000"), purchase_enabled=setting_bool("purchase_enabled", True), purchase_disabled_message=get_setting("purchase_disabled_message", "فعلا خرید بسته است. لطفا بعدا دوباره امتحان کنید."), global_notice_enabled=setting_bool("global_notice_enabled", False), global_notice_text=get_setting("global_notice_text", ""), global_notice_color=get_setting("global_notice_color", "#0ea5e9"), global_notice_duration_seconds=duration_ms_to_seconds_text(setting_int("global_notice_duration_ms", 5000)), global_notice_pages=get_setting("global_notice_pages", "home,my-videos,buy"), global_notice_font_size_px=setting_int("global_notice_font_size_px", 14), global_notice_max_width_px=setting_int("global_notice_max_width_px", 320), global_notice_position=get_setting("global_notice_position", "top-right"), ticket_ready_messages_json=get_setting("ticket_ready_messages_json", "[]"))

    categories = list(mdb["categories"].find({}, {"_id": 0}).sort("id", 1))
    active_per_category = {row["_id"]: int(row.get("count", 0)) for row in mdb["user_access"].aggregate([{"$group": {"_id": "$category_id", "count": {"$sum": 1}}}])}
    for c in categories:
        c["active_count"] = active_per_category.get(c.get("id"), 0)
    cat_by_id = {c["id"]: c for c in categories}
    videos = list(mdb["videos"].find({}, {"_id": 0}).sort("id", -1).limit(180))

    users_by_id = {u["id"]: u for u in mdb["users"].find({}, {"_id": 0, "id": 1, "device_id": 1})}
    requests_rows = build_admin_purchase_rows(mdb, cat_by_id, users_by_id, 300)
    reports = build_admin_reports(mdb, cat_by_id, 300)

    testimonials = []
    for t in mdb["testimonials"].find({}, {"_id": 0}).sort("id", -1).limit(200):
        t_category_titles = t.get("category_titles")
        if not t_category_titles:
            titles = []
            t_user_id = t.get("user_id")
            if t_user_id:
                for ua in mdb["user_access"].find({"user_id": t_user_id}, {"_id": 0, "category_id": 1}):
                    c = cat_by_id.get(ua.get("category_id"))
                    if c:
                        titles.append(c.get("title"))
            t_category_titles = " | ".join(titles) if titles else "-"
        testimonials.append({
            **t,
            "display_name": t.get("display_name") or t.get("author_name") or "کاربر",
            "content": t.get("content") or t.get("testimonial_text") or "",
            "category_titles": t_category_titles,
        })

    q = (request.args.get("q") or "").strip()
    vf = {}
    if q:
        m = re.search(r"(\d+)", q)
        if m:
            uid = int(m.group(1))
            user = mdb["users"].find_one({"id": uid}, {"_id": 0, "device_id": 1})
            if user and user.get("device_id"):
                vf = {"device_id": user.get("device_id")}
            else:
                vf = {"device_id": "__not_found__"}
        else:
            vf = {"device_id": {"$regex": q, "$options": "i"}}
    visitors = list(mdb["visitors"].find(vf, {"_id": 0}).sort("last_seen_at", -1).limit(1500))
    visitor_device_ids = [v.get("device_id") for v in visitors if v.get("device_id")]
    code_by_device = {
        x.get("device_id"): x.get("access_code")
        for x in mdb["auth_user_devices"].find(
            {"device_id": {"$in": visitor_device_ids}},
            {"_id": 0, "device_id": 1, "access_code": 1},
        )
        if x.get("device_id")
    } if visitor_device_ids else {}
    visitor_users = list(mdb["users"].find(
        {"device_id": {"$in": visitor_device_ids}} if visitor_device_ids else {"device_id": "__none__"},
        {"_id": 0, "id": 1, "device_id": 1},
    ))
    user_by_device = {u.get("device_id"): u for u in visitor_users if u.get("device_id")}
    visitor_user_ids = [u.get("id") for u in visitor_users if u.get("id") is not None]
    active_user_ids = {
        row.get("_id")
        for row in mdb["user_access"].aggregate([
            {"$match": {"user_id": {"$in": visitor_user_ids}}},
            {"$group": {"_id": "$user_id"}},
        ])
    } if visitor_user_ids else set()
    for v in visitors:
        if code_by_device.get(v.get("device_id")):
            v["username"] = code_by_device.get(v.get("device_id"))
        user = user_by_device.get(v.get("device_id"))
        has_active_access = bool(user and user.get("id") in active_user_ids)
        v["purchase_status_label"] = "تایید شده" if has_active_access else "تایید نشده"

    auth_users_raw = list(mdb["auth_users"].find({}, {"_id": 0}).sort("id", -1).limit(300))
    auth_codes = [a.get("access_code") for a in auth_users_raw if a.get("access_code")]
    auth_devices_by_code = {}
    if auth_codes:
        for d in mdb["auth_user_devices"].find({"access_code": {"$in": auth_codes}}, {"_id": 0, "access_code": 1, "last_seen_at": 1}):
            code = d.get("access_code")
            if not code:
                continue
            auth_devices_by_code.setdefault(code, []).append(d)
    auth_users = []
    for au in auth_users_raw:
        devs = auth_devices_by_code.get(au.get("access_code"), [])
        auth_users.append({**au, "device_count": len(devs), "last_device_seen": max([d.get("last_seen_at", "") for d in devs], default=None)})

    online_by_page = {}
    latest_page_pipeline = [
        {"$sort": {"updated_at": -1}},
        {"$group": {"_id": "$device_id", "page_key": {"$first": "$page_key"}}},
        {"$group": {"_id": "$page_key", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20},
    ]
    for row in mdb["presence_sessions"].aggregate(latest_page_pipeline):
        key = row.get("_id") or "unknown"
        label = key
        if key.startswith("/buy/"):
            label = "صفحه خرید: " + key.replace("/buy/", "")
        elif key == "/":
            label = "صفحه اصلی"
        elif key == "/my-videos":
            label = "فایل‌های من"
        elif key == "/messages":
            label = "تیکت‌ها"
        online_by_page[label] = int(row.get("count", 0))
    likes_by_device = {}
    if visitor_device_ids:
        for lk in mdb["category_likes"].find({"device_id": {"$in": visitor_device_ids}}, {"_id": 0, "device_id": 1, "category_id": 1}):
            did = lk.get("device_id")
            cat = cat_by_id.get(lk.get("category_id"))
            if did and cat:
                likes_by_device.setdefault(did, []).append(cat.get("title"))
    access_titles_by_user_id = {}
    if visitor_user_ids:
        for ua in mdb["user_access"].find({"user_id": {"$in": visitor_user_ids}}, {"_id": 0, "user_id": 1, "category_id": 1}):
            uid = ua.get("user_id")
            c = cat_by_id.get(ua.get("category_id"))
            if uid is not None and c:
                access_titles_by_user_id.setdefault(uid, []).append(c.get("title"))
    report_count_by_device = {
        row.get("_id"): int(row.get("count", 0))
        for row in mdb["reports"].aggregate([
            {"$match": {"device_id": {"$in": visitor_device_ids}}},
            {"$group": {"_id": "$device_id", "count": {"$sum": 1}}},
        ])
    } if visitor_device_ids else {}
    activity_rows = []
    for v in visitors:
        did = v.get("device_id")
        liked_titles = likes_by_device.get(did, [])
        user = user_by_device.get(did)
        access_titles = access_titles_by_user_id.get(user.get("id"), []) if user else []
        report_count = report_count_by_device.get(did, 0)
        activity_rows.append({
            "user_id": user.get("id") if user else None,
            "device_id": did,
            "browser_name": v.get("browser_name") or "-",
            "os_name": v.get("os_name") or "-",
            "purchase_status_label": v.get("purchase_status_label") or "تایید نشده",
            "last_seen_at": format_clock(v.get("last_seen_at")),
            "last_seen_day": format_day(v.get("last_seen_at")),
            "visit_count": int(v.get("visit_count", 0)),
            "liked_titles": "، ".join(liked_titles) if liked_titles else "-",
            "access_titles": "، ".join(access_titles) if access_titles else "-",
            "report_count": report_count,
        })
    base_stats.update({
        "total_reports": mdb["reports"].count_documents({}),
        "total_visitors": mdb["visitors"].count_documents({}),
        "total_purchases": mdb["purchase_requests"].count_documents({}),
        "approved_receipts": mdb["purchase_requests"].count_documents({"status": "approved"}),
        "rejected_receipts": mdb["purchase_requests"].count_documents({"status": "rejected"}),
        "pending_receipts": mdb["purchase_requests"].count_documents({"status": "pending"}),
    })

    return render_template("admin_dashboard.html", requests_rows=requests_rows, categories=categories, videos=videos, reports=reports, testimonials=testimonials, visitors=visitors, activity_rows=activity_rows, online_by_page=online_by_page, stats=base_stats, visitors_search=q, auth_users=auth_users, server_now=datetime.now(TEHRAN_TZ).strftime("%I:%M:%S %p"), server_day=datetime.now(TEHRAN_TZ).strftime("%m/%d/%Y"), site_update_mode=setting_bool("site_update_mode", False), site_domain_move_mode=setting_bool("site_domain_move_mode", False), site_domain_move_target=get_setting("site_domain_move_target", DEFAULT_SITE_DOMAIN_MOVE_TARGET), utc_adjust_hours=setting_int("utc_adjust_hours", DEFAULT_UTC_ADJUST_HOURS), max_devices_per_user=setting_int("max_devices_per_user", DEFAULT_MAX_DEVICES_PER_USER), maintenance_fallback_url=get_setting("maintenance_fallback_url", "http://mxdomain.top:5000"), purchase_enabled=setting_bool("purchase_enabled", True), purchase_disabled_message=get_setting("purchase_disabled_message", "فعلا خرید بسته است. لطفا بعدا دوباره امتحان کنید."), global_notice_enabled=setting_bool("global_notice_enabled", False), global_notice_text=get_setting("global_notice_text", ""), global_notice_color=get_setting("global_notice_color", "#0ea5e9"), global_notice_duration_seconds=duration_ms_to_seconds_text(setting_int("global_notice_duration_ms", 5000)), global_notice_pages=get_setting("global_notice_pages", "home,my-videos,buy"), global_notice_font_size_px=setting_int("global_notice_font_size_px", 14), global_notice_max_width_px=setting_int("global_notice_max_width_px", 320), global_notice_position=get_setting("global_notice_position", "top-right"), ticket_ready_messages_json=get_setting("ticket_ready_messages_json", "[]"))


@app.get("/khnowledge-mx/receipt/<path:filename>")
@admin_required
def admin_receipt(filename):
    clean = secure_filename(filename)
    rid = request.args.get("rid", "").strip()
    wants_download = request.args.get("download") == "1"
    mdb = mongo_db()
    if rid.isdigit() and mdb is not None:
        mdb["purchase_requests"].update_one({"id": int(rid), "receipt_seen_at": None}, {"$set": {"receipt_seen_at": now_iso()}})
    full = os.path.join(RECEIPTS_DIR, clean)
    if not os.path.exists(full):
        abort(404)
    if wants_download:
        return send_file(full, as_attachment=True, download_name=clean)
    return send_file(full)


@app.get("/khnowledge-mx/reports/<int:rid>")
@admin_required
def admin_report_chat(rid):
    mdb = mongo_db()
    if mdb is None:
        return redirect("/khnowledge-mx")
    row = mdb["reports"].find_one({"id": rid}, {"_id": 0})
    if not row:
        return redirect("/khnowledge-mx")
    categories = list(mdb["categories"].find({}, {"_id": 0, "id": 1, "title": 1}))
    cat_by_id = {c.get("id"): c.get("title") for c in categories}
    user_id = row.get("user_id")
    titles = []
    if user_id:
        for ua in mdb["user_access"].find({"user_id": user_id}, {"_id": 0, "category_id": 1}):
            title = cat_by_id.get(ua.get("category_id"))
            if title:
                titles.append(title)
    messages = normalize_report_messages(row.get("messages"), row.get("report_text") or "", row.get("created_at"))
    row["messages"] = messages
    for msg in row["messages"]:
        msg["at_clock"] = format_clock(msg.get("at"))
        msg["at_day"] = format_day(msg.get("at"))
    mdb["reports"].update_one({"id": rid}, {"$set": {"messages": messages, "admin_seen_at": now_iso()}})
    row["created_at_clock"] = format_clock(row.get("created_at"))
    row["created_at_day"] = format_day(row.get("created_at"))
    row["category_titles"] = ", ".join(titles) if titles else "-"
    try:
        ready_messages = json.loads(get_setting("ticket_ready_messages_json", "[]"))
        if not isinstance(ready_messages, list):
            ready_messages = []
    except Exception:
        ready_messages = []
    return render_template("admin_report_chat.html", report=row, ready_messages=ready_messages)


@app.get("/khnowledge-mx/user-activity/<path:device_id>")
@admin_required
def admin_user_activity(device_id):
    mdb = mongo_db()
    if mdb is None:
        return redirect("/khnowledge-mx")
    did = (device_id or "").strip()
    if not did:
        return redirect("/khnowledge-mx")

    visitor = mdb["visitors"].find_one({"device_id": did}, {"_id": 0}) or {}
    user = mdb["users"].find_one({"device_id": did}, {"_id": 0}) or {}
    user_id = user.get("id")

    categories = list(mdb["categories"].find({}, {"_id": 0, "id": 1, "title": 1}))
    cat_by_id = {c.get("id"): c.get("title") for c in categories}
    access_titles = []
    if user_id:
        for ua in mdb["user_access"].find({"user_id": user_id}, {"_id": 0, "category_id": 1}):
            title = cat_by_id.get(ua.get("category_id"))
            if title:
                access_titles.append(title)

    liked_titles = []
    for lk in mdb["category_likes"].find({"device_id": did}, {"_id": 0, "category_id": 1}):
        title = cat_by_id.get(lk.get("category_id"))
        if title:
            liked_titles.append(title)

    purchases = []
    if user_id:
        for row in mdb["purchase_requests"].find({"user_id": user_id}, {"_id": 0}).sort("id", -1).limit(100):
            req_cat = cat_by_id.get(row.get("requested_category_id"), "-")
            purchases.append({
                **row,
                "requested_category": req_cat,
                "status_label": purchase_status_label(row.get("status"), bool(row.get("is_fake_receipt"))),
                "created_at_clock": format_clock(row.get("created_at")),
                "created_at_day": format_day(row.get("created_at")),
            })

    reports = []
    for rp in mdb["reports"].find({"device_id": did}, {"_id": 0}).sort("id", -1).limit(100):
        rp["created_at_clock"] = format_clock(rp.get("created_at"))
        rp["created_at_day"] = format_day(rp.get("created_at"))
        reports.append(rp)

    return render_template(
        "admin_user_activity.html",
        device_id=did,
        user_id=user_id,
        visitor=visitor,
        access_titles="، ".join(access_titles) if access_titles else "-",
        liked_titles="، ".join(liked_titles) if liked_titles else "-",
        purchases=purchases,
        reports=reports,
    )


@app.post("/khnowledge-mx/api/categories")
@admin_required
def admin_create_category():
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    title = (request.form.get("title") or "").strip()
    slug = (request.form.get("slug") or "").strip().lower()
    payment_text = (request.form.get("payment_text") or "").strip()
    if not title or not slug or not payment_text:
        return jsonify({"ok": False, "message": "اطلاعات ناقص"}), 400
    if mdb["categories"].find_one({"slug": slug}):
        return jsonify({"ok": False, "message": "slug تکراری است"}), 409
    mdb["categories"].insert_one({"id": mongo_next_id("categories"), "title": title, "slug": slug, "payment_text": payment_text, "created_at": now_iso()})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/categories/<int:category_id>/delete")
@admin_required
def admin_delete_category(category_id):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    for v in mdb["videos"].find({"category_id": category_id}, {"_id": 0, "file_path": 1}):
        if v.get("file_path"):
            try:
                os.remove(os.path.join(VIDEOS_DIR, v["file_path"]))
            except Exception:
                pass
    mdb["videos"].delete_many({"category_id": category_id})
    mdb["user_access"].delete_many({"category_id": category_id})
    mdb["categories"].delete_one({"id": category_id})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/categories/<int:category_id>/update")
@admin_required
def admin_update_category(category_id):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    title = (request.form.get("title") or "").strip()
    payment_text = (request.form.get("payment_text") or "").strip()
    if not title or not payment_text:
        return jsonify({"ok": False, "message": "اطلاعات ناقص"}), 400
    mdb["categories"].update_one({"id": category_id}, {"$set": {"title": title, "payment_text": payment_text, "updated_at": now_iso()}})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/videos")
@admin_required
def admin_create_video():
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    title = (request.form.get("title") or "").strip()
    category_id = int(request.form.get("category_id") or 0)
    external_url = (request.form.get("external_url") or "").strip()
    video_file = request.files.get("video_file")
    if not title or not category_id:
        return jsonify({"ok": False, "message": "اطلاعات ناقص"}), 400
    if not external_url and not video_file:
        return jsonify({"ok": False, "message": "فایل یا لینک لازم است"}), 400
    doc = {"id": mongo_next_id("videos"), "title": title, "category_id": category_id, "created_at": now_iso()}
    if external_url:
        doc.update({"source_type": "url", "external_url": external_url, "file_path": None})
    else:
        filename = secure_filename(video_file.filename or "")
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_ARCHIVE_EXTENSIONS:
            return jsonify({"ok": False, "message": "فقط ZIP مجاز است"}), 400
        final = f"{uuid.uuid4().hex}_{filename}"
        video_file.save(os.path.join(VIDEOS_DIR, final))
        doc.update({"source_type": "file", "external_url": None, "file_path": final})
    mdb["videos"].insert_one(doc)
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/videos/<int:video_id>/delete")
@admin_required
def admin_delete_video(video_id):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    row = mdb["videos"].find_one({"id": video_id})
    if row and row.get("file_path"):
        try:
            os.remove(os.path.join(VIDEOS_DIR, row["file_path"]))
        except Exception:
            pass
    mdb["videos"].delete_one({"id": video_id})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/requests/<int:rid>/approve")
@admin_required
def admin_approve_request(rid):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    req = mdb["purchase_requests"].find_one({"id": rid})
    if not req:
        return jsonify({"ok": False, "message": "درخواست پیدا نشد"}), 404
    category_ids = [int(x) for x in request.form.getlist("category_ids") if str(x).isdigit()]
    if not category_ids and req.get("requested_category_id"):
        category_ids = [int(req["requested_category_id"])]
    for cid in category_ids:
        mdb["user_access"].update_one({"user_id": req["user_id"], "category_id": cid}, {"$set": {"granted_at": now_iso()}}, upsert=True)
    mdb["purchase_requests"].update_one({"id": rid}, {"$set": {"status": "approved", "reviewed_at": now_iso(), "admin_note": None, "granted_category_ids": category_ids, "is_fake_receipt": False}})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/requests/<int:rid>/reject")
@admin_required
def admin_reject_request(rid):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    reason = (request.form.get("reason") or "").strip()
    if not reason:
        return jsonify({"ok": False, "message": "دلیل رد لازم است"}), 400
    mdb["purchase_requests"].update_one({"id": rid}, {"$set": {"status": "rejected", "reviewed_at": now_iso(), "admin_note": reason, "is_fake_receipt": False}})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/requests/<int:rid>/fake")
@admin_required
def admin_fake_request(rid):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    reason = (request.form.get("reason") or "").strip() or "فیش نامعتبر تشخیص داده شد."
    mdb["purchase_requests"].update_one({"id": rid}, {"$set": {"status": "rejected", "is_fake_receipt": True, "reviewed_at": now_iso(), "admin_note": reason}})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/requests/<int:rid>/reset-pending")
@admin_required
def admin_reset_pending(rid):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    req = mdb["purchase_requests"].find_one({"id": rid})
    if req and req.get("user_id"):
        granted_ids = [int(x) for x in (req.get("granted_category_ids") or []) if str(x).isdigit()]
        if not granted_ids and req.get("requested_category_id"):
            granted_ids = [int(req["requested_category_id"])]
        for cid in granted_ids:
            mdb["user_access"].delete_many({"user_id": req["user_id"], "category_id": cid})
    mdb["purchase_requests"].update_one({"id": rid}, {"$set": {"status": "pending", "reviewed_at": None, "admin_note": None, "granted_category_ids": [], "is_fake_receipt": False}})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/reports/<int:rid>/reply")
@admin_required
def admin_reply_report(rid):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    reply = (request.form.get("reply") or request.form.get("reply_text") or "").strip()
    if not reply:
        return jsonify({"ok": False, "message": "پاسخ خالی است"}), 400
    row = mdb["reports"].find_one({"id": rid}, {"_id": 0, "messages": 1})
    msgs = normalize_report_messages((row or {}).get("messages"), "", now_iso())
    msgs.append({"id": uuid.uuid4().hex[:12], "sender": "admin", "text": reply, "at": now_iso()})
    mdb["reports"].update_one({"id": rid}, {"$set": {"admin_reply": reply, "replied_at": now_iso(), "user_seen_at": None, "messages": msgs}})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/reports/<int:rid>/messages/<msg_id>/delete")
@admin_required
def admin_delete_report_message(rid, msg_id):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    row = mdb["reports"].find_one({"id": rid}, {"_id": 0})
    if not row:
        return jsonify({"ok": False, "message": "تیکت پیدا نشد"}), 404
    msgs = normalize_report_messages(row.get("messages"), row.get("report_text") or "", row.get("created_at"))
    next_msgs = [m for m in msgs if not (str(m.get("id")) == str(msg_id) and m.get("sender") == "admin")]
    if len(next_msgs) == len(msgs):
        return jsonify({"ok": False, "message": "این پیام قابل حذف نیست."}), 400
    mdb["reports"].update_one({"id": rid}, {"$set": {"messages": next_msgs}})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/reports/<int:rid>/delete")
@admin_required
def admin_delete_report(rid):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    res = mdb["reports"].delete_one({"id": rid})
    if res.deleted_count < 1:
        return jsonify({"ok": False, "message": "تیکت پیدا نشد"}), 404
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/device-ban")
@admin_required
def admin_device_ban():
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    did = (request.form.get("device_id") or "").strip()
    if not did:
        return jsonify({"ok": False, "message": "device_id لازم است"}), 400
    mdb["visitors"].update_one({"device_id": did}, {"$set": {"is_banned": 1, "last_seen_at": now_iso()}}, upsert=True)
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/visitors/<int:visitor_id>/ban")
@admin_required
def admin_ban_visitor(visitor_id):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    mdb["visitors"].update_one({"id": visitor_id}, {"$set": {"is_banned": 1}})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/visitors/<int:visitor_id>/unban")
@admin_required
def admin_unban_visitor(visitor_id):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    mdb["visitors"].update_one({"id": visitor_id}, {"$set": {"is_banned": 0}})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/testimonials/<int:testimonial_id>/approve")
@admin_required
def admin_approve_testimonial(testimonial_id):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    mdb["testimonials"].update_one({"id": testimonial_id}, {"$set": {"status": "approved"}})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/testimonials/<int:testimonial_id>/reject")
@admin_required
def admin_reject_testimonial(testimonial_id):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    mdb["testimonials"].update_one({"id": testimonial_id}, {"$set": {"status": "rejected"}})
    return jsonify({"ok": True})


@app.post("/khnowledge-mx/api/testimonials/<int:testimonial_id>/delete")
@admin_required
def admin_delete_testimonial(testimonial_id):
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    mdb["testimonials"].delete_one({"id": testimonial_id})
    return jsonify({"ok": True})


@app.get("/khnowledge-mx/api/backup-db")
@admin_required
def admin_backup_db():
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    import json
    payload = {}
    for name in ["app_settings", "categories", "videos", "users", "purchase_requests", "reports", "visitors", "testimonials", "auth_users", "auth_user_devices", "user_access", "presence_sessions"]:
        payload[name] = list(mdb[name].find({}, {"_id": 0}))
    out_path = os.path.join(BASE_DIR, "mongo_backup.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return send_file(out_path, as_attachment=True, download_name="mongo_backup.json")


@app.get("/khnowledge-mx/api/backup-receipts")
@admin_required
def admin_backup_receipts():
    zip_path = os.path.join(BASE_DIR, "receipts_backup.zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in os.listdir(RECEIPTS_DIR):
            full = os.path.join(RECEIPTS_DIR, name)
            if os.path.isfile(full):
                zf.write(full, arcname=name)
    return send_file(zip_path, as_attachment=True, download_name="receipts_backup.zip")


@app.get("/khnowledge-mx/api/backup-all")
@admin_required
def admin_backup_all():
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    import json

    payload = {}
    for name in ["app_settings", "categories", "videos", "users", "purchase_requests", "reports", "visitors", "testimonials", "auth_users", "auth_user_devices", "user_access", "presence_sessions"]:
        payload[name] = list(mdb[name].find({}, {"_id": 0}))

    db_json = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    bundle_bytes = BytesIO()
    with zipfile.ZipFile(bundle_bytes, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mongo_backup.json", db_json)
        for name in os.listdir(RECEIPTS_DIR):
            full = os.path.join(RECEIPTS_DIR, name)
            if os.path.isfile(full):
                zf.write(full, arcname=f"receipts/{name}")
    bundle_bytes.seek(0)
    return send_file(bundle_bytes, as_attachment=True, download_name="site_mx2_backup_bundle.zip", mimetype="application/zip")


@app.get("/khnowledge-mx/api/live-stats")
@admin_required
def admin_live_stats():
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable", "stats": {}, "online_by_page": {}}), 503

    now = datetime.utcnow()
    active_since = (now - timedelta(seconds=60)).isoformat()
    online_since = (now - timedelta(minutes=5)).isoformat()
    today = now.date()
    today_start_dt = datetime.combine(today, datetime.min.time())
    today_end_dt = today_start_dt + timedelta(days=1)
    y_start_dt = today_start_dt - timedelta(days=1)
    y_end_dt = today_start_dt
    today_start, today_end = today_start_dt.isoformat(), today_end_dt.isoformat()
    y_start, y_end = y_start_dt.isoformat(), y_end_dt.isoformat()
    online_devices = list(mdb["presence_sessions"].find({"updated_at": {"$gte": online_since}}, {"_id": 0, "device_id": 1}))
    os_counts = {"ios": 0, "android": 0, "windows": 0}
    seen = set()
    for row in online_devices:
        did = row.get("device_id")
        if not did or did in seen:
            continue
        seen.add(did)
        vis = mdb["visitors"].find_one({"device_id": did}, {"_id": 0, "os_name": 1})
        os_name = (vis or {}).get("os_name", "").lower()
        if "ios" in os_name:
            os_counts["ios"] += 1
        elif "android" in os_name:
            os_counts["android"] += 1
        elif "windows" in os_name:
            os_counts["windows"] += 1
    stats = {
        "online_total": len(seen),
        "active_last_minute": mdb["presence_sessions"].count_documents({"updated_at": {"$gte": active_since}}),
        "online_ios": os_counts["ios"],
        "online_android": os_counts["android"],
        "online_windows": os_counts["windows"],
        "total_reports": mdb["reports"].count_documents({}),
        "total_visitors": mdb["visitors"].count_documents({}),
        "total_purchases": mdb["purchase_requests"].count_documents({}),
        "approved_receipts": mdb["purchase_requests"].count_documents({"status": "approved"}),
        "rejected_receipts": mdb["purchase_requests"].count_documents({"status": "rejected"}),
        "pending_receipts": mdb["purchase_requests"].count_documents({"status": "pending"}),
        "today_purchases": mdb["purchase_requests"].count_documents({"created_at": {"$gte": today_start, "$lt": today_end}}),
        "today_approved": mdb["purchase_requests"].count_documents({"status": "approved", "reviewed_at": {"$gte": today_start, "$lt": today_end}}),
        "today_rejected": mdb["purchase_requests"].count_documents({"status": "rejected", "reviewed_at": {"$gte": today_start, "$lt": today_end}}),
        "today_visitors": mdb["visitors"].count_documents({"last_seen_at": {"$gte": today_start, "$lt": today_end}}),
        "yesterday_purchases": mdb["purchase_requests"].count_documents({"created_at": {"$gte": y_start, "$lt": y_end}}),
        "yesterday_approved": mdb["purchase_requests"].count_documents({"status": "approved", "reviewed_at": {"$gte": y_start, "$lt": y_end}}),
        "yesterday_rejected": mdb["purchase_requests"].count_documents({"status": "rejected", "reviewed_at": {"$gte": y_start, "$lt": y_end}}),
        "yesterday_visitors": mdb["visitors"].count_documents({"last_seen_at": {"$gte": y_start, "$lt": y_end}}),
    }
    latest_purchase = mdb["purchase_requests"].find_one({}, {"id": 1, "_id": 0}, sort=[("id", -1)])
    latest_report = mdb["reports"].find_one({}, {"id": 1, "_id": 0}, sort=[("id", -1)])
    latest_testimonial = mdb["testimonials"].find_one({}, {"id": 1, "_id": 0}, sort=[("id", -1)])
    stats["latest_purchase_id"] = int((latest_purchase or {}).get("id") or 0)
    stats["latest_report_id"] = int((latest_report or {}).get("id") or 0)
    stats["latest_testimonial_id"] = int((latest_testimonial or {}).get("id") or 0)
    stats["server_now"] = datetime.now(TEHRAN_TZ).strftime("%I:%M:%S %p")
    stats["server_day"] = datetime.now(TEHRAN_TZ).strftime("%m/%d/%Y")

    pipeline = [
        {"$match": {"updated_at": {"$gte": online_since}}},
        {"$sort": {"updated_at": -1}},
        {"$group": {"_id": "$device_id", "page_key": {"$first": "$page_key"}}},
        {"$group": {"_id": "$page_key", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    online_by_page = {}
    for row in mdb["presence_sessions"].aggregate(pipeline):
        key = row.get("_id") or "unknown"
        label = key
        if key.startswith("/buy/"):
            label = "صفحه خرید: " + key.replace("/buy/", "")
        elif key == "/":
            label = "صفحه اصلی"
        elif key == "/my-videos":
            label = "فایل‌های من"
        elif key == "/messages":
            label = "تیکت‌ها"
        online_by_page[label] = int(row.get("count", 0))
    return jsonify({"ok": True, "stats": stats, "online_by_page": online_by_page, "mongo_ok": True})


@app.get("/khnowledge-mx/api/live-feed")
@admin_required
def admin_live_feed():
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    categories = list(mdb["categories"].find({}, {"_id": 0, "id": 1, "title": 1}))
    cat_by_id = {c["id"]: c for c in categories}
    users_by_id = {u["id"]: u for u in mdb["users"].find({}, {"_id": 0, "id": 1, "device_id": 1})}
    requests_rows = build_admin_purchase_rows(mdb, cat_by_id, users_by_id, 120)
    reports = build_admin_reports(mdb, cat_by_id, 120)
    report_rows = []
    for rp in reports:
        messages = rp.get("messages") or []
        last_msg = messages[-1] if messages else {}
        report_rows.append({
            "id": rp.get("id"),
            "reporter_name": rp.get("reporter_name") or f"کاربر {rp.get('user_id') or '-'}",
            "device_id": rp.get("device_id") or "-",
            "report_type": rp.get("report_type") or "-",
            "category_titles": rp.get("category_titles") or "-",
            "created_at_clock": rp.get("created_at_clock"),
            "created_at_day": rp.get("created_at_day"),
            "last_sender": "ادمین" if last_msg.get("sender") == "admin" else "کاربر",
            "last_text": last_msg.get("text") or "-",
            "last_at_clock": format_clock(last_msg.get("at")),
            "last_at_day": format_day(last_msg.get("at")),
        })
    return jsonify({"ok": True, "purchases": requests_rows, "reports": report_rows})


@app.post("/khnowledge-mx/api/settings")
@admin_required
def admin_update_settings():
    mdb = mongo_db()
    if mdb is None:
        return jsonify({"ok": False, "message": "Mongo unavailable"}), 503
    duration_raw = request.form.get("global_notice_duration_seconds") or "5"
    try:
        duration = max(1, int(duration_raw)) * 1000
    except Exception:
        duration = 5000
    selected_pages = request.form.getlist("global_notice_pages")
    allowed_pages = {"home", "my-videos", "buy"}
    selected_pages = [p for p in selected_pages if p in allowed_pages]
    if not selected_pages:
        selected_pages = ["home"]
    raw_ready_messages = (request.form.get("ticket_ready_messages_json") or "[]").strip()
    try:
        parsed_ready_messages = json.loads(raw_ready_messages)
        if not isinstance(parsed_ready_messages, list):
            parsed_ready_messages = []
    except Exception:
        parsed_ready_messages = []
    updates = {
        "site_update_mode": "1" if request.form.get("site_update_mode") == "1" else "0",
        "site_domain_move_mode": "1" if request.form.get("site_domain_move_mode") == "1" else "0",
        "site_domain_move_target": (request.form.get("site_domain_move_target") or DEFAULT_SITE_DOMAIN_MOVE_TARGET).strip(),
        "maintenance_fallback_url": (request.form.get("maintenance_fallback_url") or "http://mxdomain.top:5000").strip(),
        "utc_adjust_hours": str(int(request.form.get("utc_adjust_hours") or DEFAULT_UTC_ADJUST_HOURS)),
        "max_devices_per_user": str(max(1, min(10, int(request.form.get("max_devices_per_user") or DEFAULT_MAX_DEVICES_PER_USER)))),
        "purchase_enabled": "1" if request.form.get("purchase_enabled") == "1" else "0",
        "purchase_disabled_message": (request.form.get("purchase_disabled_message") or "").strip() or "فعلا خرید بسته است. لطفا بعدا دوباره امتحان کنید.",
        "global_notice_enabled": "1" if request.form.get("global_notice_enabled") == "1" else "0",
        "global_notice_text": (request.form.get("global_notice_text") or "").strip(),
        "global_notice_color": (request.form.get("global_notice_color") or "#0ea5e9").strip()[:32],
        "global_notice_duration_ms": str(duration),
        "global_notice_pages": ",".join(selected_pages),
        "global_notice_position": "top-right" if (request.form.get("global_notice_position") or "top-right") == "top-right" else "bottom-right",
        "global_notice_font_size_px": str(max(11, min(28, int(request.form.get("global_notice_font_size_px") or 14)))),
        "global_notice_max_width_px": str(max(200, min(900, int(request.form.get("global_notice_max_width_px") or 320)))),
        "ticket_ready_messages_json": json.dumps(parsed_ready_messages, ensure_ascii=False),
    }
    for k, v in updates.items():
        mdb["app_settings"].update_one({"key": k}, {"$set": {"key": k, "value": v, "updated_at": now_iso()}}, upsert=True)
    return jsonify({"ok": True, "message": "تنظیمات ذخیره شد."})


@app.get("/api/global-notice")
def api_global_notice():
    page = (request.args.get("page") or "").strip()
    allowed_pages = {"home", "my-videos", "buy"}
    if page not in allowed_pages:
        return jsonify({"ok": True, "enabled": False})
    enabled = setting_bool("global_notice_enabled", False)
    pages = {p.strip() for p in get_setting("global_notice_pages", "home,my-videos,buy").split(",") if p.strip()}
    if (not enabled) or page not in pages:
        return jsonify({"ok": True, "enabled": False})
    text = get_setting("global_notice_text", "").strip()
    if not text:
        return jsonify({"ok": True, "enabled": False})
    return jsonify({
        "ok": True,
        "enabled": True,
        "text": text,
        "color": get_setting("global_notice_color", "#0ea5e9"),
        "duration_ms": max(1000, setting_int("global_notice_duration_ms", 5000)),
        "position": get_setting("global_notice_position", "top-right"),
        "font_size_px": max(11, setting_int("global_notice_font_size_px", 14)),
        "max_width_px": max(200, setting_int("global_notice_max_width_px", 320)),
    })


@app.route("/khnowledge-mx/logout")
@app.route("/khnowledge-mx_logout")
def admin_logout():
    session.clear()
    return redirect("/khnowledge-mx/login")


if __name__ == "__main__":
    seed_mongo()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
