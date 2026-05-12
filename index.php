<?php
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/';

$staticFile = __DIR__ . $path;
if ($path !== '/' && is_file($staticFile)) {
    return false;
}

function layout(string $title, string $content, array $scripts = [], bool $admin = false): void {
    echo '<!doctype html><html lang="fa" dir="rtl"><head>';
    echo '<meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />';
    echo '<title>' . htmlspecialchars($title, ENT_QUOTES, 'UTF-8') . '</title>';
    echo '<link rel="stylesheet" href="/static/css/style.css" />';
    echo '</head><body><main class="container">';

    if (!$admin) {
        echo '<section class="quick-links form-card">';
        echo '<a class="btn" href="/">دریافت ویدیو جدید</a>';
        echo '<a class="btn btn-ghost my-videos-link" href="/my-videos">مشاهده ویدیوهای من <span id="my-videos-badge" class="notify-badge hidden">0</span></a>';
        echo '</section><section id="admin-reply-banner" class="alert-banner hidden"><button id="admin-reply-banner-btn" type="button">⚠️ ادمین پاسخی برای شما ثبت کرده - مشاهده</button></section>';
    }

    echo $content;

    if (!$admin) {
        echo '<button id="report-toggle" class="report-fab" type="button"><span>🚩</span><span>ریپورت</span></button>';
        echo '<button id="support-toggle" class="support-fab" type="button"><span>🛟</span><span>پشتیبانی</span></button>';
        echo '<button id="survey-toggle" class="survey-fab" type="button"><span>💬</span><span>ثبت نظر</span></button>';
        echo '<button id="admin-messages-toggle" class="messages-fab" type="button"><span>🔔</span><span id="admin-messages-count" class="fab-count hidden">0</span></button>';
        echo '<script src="/static/js/common.js?v=2"></script>';
    }

    foreach ($scripts as $script) {
        echo '<script src="' . htmlspecialchars($script, ENT_QUOTES, 'UTF-8') . '"></script>';
    }
    echo '</main></body></html>';
}

switch ($path) {
    case '/':
        $html = '<section class="purchase-counter"><div class="counter-glow"><p>🔥 تعداد اشتراک‌های فعال</p><strong id="total-purchase-counter">45</strong></div></section>'
              . '<section class="table-wrap"><h2>دسته‌بندی‌های قابل مشاهده</h2><div class="placeholder">در نسخه PHP باید داده‌ها از دیتابیس PHP خوانده شود.</div></section>'
              . '<section class="footer-action"><a class="btn btn-ghost" href="/my-videos">ورود به فایل‌های من</a></section>';
        layout('خانه', $html);
        break;
    case '/login':
        layout('ورود', '<section class="form-card"><h2>ورود کاربر</h2><form id="login-form"><label>شناسه دستگاه</label><input type="text" /><button class="btn" type="button">ورود</button></form><div id="login-result" class="result-box"></div></section>', ['/static/js/login.js']);
        break;
    case '/buy':
    case '/buy/irani':
    case '/buy/khareji':
        layout('خرید', '<section class="form-card"><h2>خرید اشتراک</h2><p>فرم کامل خرید و آپلود فیش باید با endpointهای PHP متصل شود.</p><div id="buy-app"></div></section>', ['/static/js/buy.js']);
        break;
    case '/my-videos':
        layout('ویدیوهای من', '<section class="table-wrap"><h2>ویدیوهای من</h2><div id="my-videos-app" class="placeholder">لیست ویدیوها بعد از اتصال API نمایش داده می‌شود.</div></section>', ['/static/js/my_videos.js']);
        break;
    case '/messages':
        layout('پیام‌ها', '<section class="table-wrap"><h2>پیام‌ها</h2><div id="messages-app" class="placeholder">پیام‌ها بعد از اتصال بک‌اند PHP لود می‌شوند.</div></section>', ['/static/js/messages.js']);
        break;
    case '/admin':
    case '/admin/login':
        layout('ورود ادمین', '<section class="form-card"><h2>ورود ادمین</h2><form><label>نام کاربری</label><input type="text"><label>رمز عبور</label><input type="password"><button class="btn" type="button">ورود</button></form></section>', ['/static/js/admin.js'], true);
        break;
    default:
        http_response_code(404);
        layout('404', '<section class="form-card"><h2>صفحه پیدا نشد</h2></section>');
}
