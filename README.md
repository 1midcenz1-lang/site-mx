# MX Video Site

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Site: `http://127.0.0.1:5000`

## PHP Hosting (recommended for your host)

This project now includes a PHP front controller:

- `index.php`
- `.htaccess`

Upload the whole project to your PHP host (Apache + PDO SQLite enabled).
All routes are handled by `index.php`.

## Admin Login

- username: `admin`
- password: `mx9091`

Use env vars in production:

- `ADMIN_USER`
- `ADMIN_PASS`
- `SECRET_KEY`

## Sample ZIP files on home

Put files here:

- `uploads/samples/irani_nemone.zip`
- `uploads/samples/khareji_nemone.zip`

Also supported automatically from project root:

- `irani_nemone.zip`
- `khareji_nemone.zip`

## Notes

- User is locked to the first device (`device_id` from browser localStorage).
- Admin can approve each request and choose one or multiple categories for user access.
- ZIP files can be uploaded by admin or added by external download link.
