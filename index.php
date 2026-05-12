<?php
// Lightweight PHP front controller for shared PHP hosts.
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

$staticFile = __DIR__ . $path;
if ($path !== '/' && is_file($staticFile)) {
    return false; // let web server serve static files
}

function render_page($title, $bodyHtml) {
    echo '<!doctype html><html lang="fa" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">';
    echo '<title>' . htmlspecialchars($title, ENT_QUOTES, 'UTF-8') . '</title>';
    echo '<link rel="stylesheet" href="/static/css/style.css">';
    echo '</head><body><main class="container">';
    echo '<section class="quick-links form-card">';
    echo '<a class="btn" href="/">دریافت ویدیو جدید</a>';
    echo '<a class="btn btn-ghost" href="/login">ورود</a>';
    echo '</section>';
    echo $bodyHtml;
    echo '</main></body></html>';
}

switch ($path) {
    case '/':
        render_page('خانه', '<section class="form-card"><h2>نسخه PHP فعال شد</h2><p>ظاهر سایت روی هاست PHP در دسترس است. برای امکانات کامل، بک‌اند Flask باید به PHP مهاجرت کامل شود.</p><a class="btn" href="/buy">خرید اشتراک</a></section>');
        break;
    case '/login':
        render_page('ورود', '<section class="form-card"><h2>ورود</h2><p>این نسخه موقت PHP است.</p></section>');
        break;
    case '/buy':
        render_page('خرید', '<section class="form-card"><h2>خرید اشتراک</h2><p>برای تایید پرداخت و پنل ادمین، مهاجرت کامل بک‌اند لازم است.</p></section>');
        break;
    default:
        http_response_code(404);
        render_page('404', '<section class="form-card"><h2>یافت نشد</h2></section>');
}
