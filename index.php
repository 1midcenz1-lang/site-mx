<?php
session_start();

const APP_PREFIX = '/khnowledge-mx';

function db(): PDO {
    static $pdo = null;
    if ($pdo instanceof PDO) return $pdo;
    $dbDir = __DIR__ . '/data';
    if (!is_dir($dbDir)) mkdir($dbDir, 0777, true);
    $pdo = new PDO('sqlite:' . $dbDir . '/app.sqlite');
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->exec("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, slug TEXT NOT NULL UNIQUE, payment_text TEXT NOT NULL)");
    $pdo->exec("CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT NOT NULL)");
    $count = (int)$pdo->query('SELECT COUNT(*) FROM categories')->fetchColumn();
    if ($count === 0) {
        $stmt = $pdo->prepare('INSERT INTO categories (title, slug, payment_text) VALUES (?,?,?)');
        $stmt->execute(['کانال ایرانی', 'irani', 'پرداخت به شماره کارت درج شده در سایت.']);
        $stmt->execute(['کانال خارجی', 'khareji', 'پرداخت به شماره کارت درج شده در سایت.']);
    }
    return $pdo;
}
function all_categories(): array { return db()->query('SELECT * FROM categories ORDER BY id DESC')->fetchAll(PDO::FETCH_ASSOC); }
function json_out(array $data, int $status = 200): void { http_response_code($status); header('Content-Type: application/json; charset=utf-8'); echo json_encode($data, JSON_UNESCAPED_UNICODE); exit; }
function render($view, $vars = []) { extract($vars); include __DIR__ . '/views/' . $view . '.php'; exit; }
function require_admin() { if (empty($_SESSION['admin_logged_in'])) { header('Location: /admin/login'); exit; } }

$rawPath = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/';
$path = $rawPath;
if (str_starts_with($path, APP_PREFIX)) $path = substr($path, strlen(APP_PREFIX)) ?: '/';
if ($path === '/index.php') $path = '/';
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($path === '/admin/login' && $method === 'POST') {
    $u = $_POST['username'] ?? ''; $p = $_POST['password'] ?? '';
    if ($u === 'admin' && $p === 'mx9091') { $_SESSION['admin_logged_in'] = true; header('Location: /admin'); }
    else { $_SESSION['flash'] = 'نام کاربری یا رمز عبور اشتباه است.'; header('Location: /admin/login'); }
    exit;
}
if ($path === '/admin_logout') { session_destroy(); header('Location: /admin/login'); exit; }

if (str_starts_with($path, '/api/')) {
    require_admin();
    if ($path === '/api/live-stats') {
        json_out(['ok'=>true,'stats'=>['online_total'=>0,'online_android'=>0,'online_ios'=>0,'online_windows'=>0,'total_reports'=>0,'total_visitors'=>0,'total_purchases'=>0,'approved_receipts'=>0,'rejected_receipts'=>0,'pending_receipts'=>0,'today_purchases'=>0,'today_approved'=>0,'today_rejected'=>0,'today_visitors'=>0,'yesterday_purchases'=>0,'yesterday_approved'=>0,'yesterday_rejected'=>0,'yesterday_visitors'=>0,'latest_purchase_id'=>0,'latest_report_id'=>0,'latest_testimonial_id'=>0],'online_by_page'=>new stdClass()]);
    }
    if ($path === '/api/live-feed') json_out(['ok'=>true,'purchases'=>[],'reports'=>[]]);
    if ($path === '/api/categories' && $method === 'POST') {
        $title=trim($_POST['title']??''); $slug=trim($_POST['slug']??''); $payment=trim($_POST['payment_text']??'');
        if ($title===''||$slug===''||$payment==='') json_out(['ok'=>false,'message'=>'تمام فیلدها الزامی است.'],422);
        try { db()->prepare('INSERT INTO categories (title,slug,payment_text) VALUES (?,?,?)')->execute([$title,$slug,$payment]); }
        catch (Throwable $e) { json_out(['ok'=>false,'message'=>'slug تکراری است.'],422); }
        json_out(['ok'=>true]);
    }
    if (preg_match('#^/api/categories/(\d+)/update$#',$path,$m) && $method==='POST') {
        db()->prepare('UPDATE categories SET title=?, payment_text=? WHERE id=?')->execute([trim($_POST['title']??''), trim($_POST['payment_text']??''), (int)$m[1]]);
        json_out(['ok'=>true]);
    }
    if (preg_match('#^/api/categories/(\d+)/delete$#',$path,$m) && $method==='POST') {
        db()->prepare('DELETE FROM categories WHERE id=?')->execute([(int)$m[1]]);
        json_out(['ok'=>true]);
    }
    if ($path === '/api/settings' && $method==='POST') {
        $stmt = db()->prepare('INSERT INTO settings (k,v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v');
        foreach ($_POST as $k=>$v) $stmt->execute([$k, is_array($v)?json_encode($v, JSON_UNESCAPED_UNICODE): (string)$v]);
        json_out(['ok'=>true]);
    }
    if ($path === '/api/backup-all') { header('Content-Type: text/plain; charset=utf-8'); echo 'Backup not configured yet.'; exit; }
    json_out(['ok'=>true]);
}

$categories = all_categories();
$testimonials = [];

switch (true) {
    case $path === '/': render('home', compact('categories', 'testimonials'));
    case $path === '/login': render('login', ['next_url' => $_GET['next'] ?? '/']);
    case $path === '/my-videos': render('my_videos');
    case $path === '/messages': render('messages');
    case preg_match('#^/buy/([a-zA-Z0-9_-]+)$#', $path, $m):
        $slug = $m[1]; $category = $categories[0] ?? ['title'=>'-','slug'=>'-','payment_text'=>'-'];
        foreach ($categories as $c) if ($c['slug'] === $slug) $category = $c;
        render('buy', compact('category'));
    case $path === '/admin/login': $flash = $_SESSION['flash'] ?? null; unset($_SESSION['flash']); render('admin_login', compact('flash'));
    case $path === '/admin': require_admin(); render('admin_dashboard', ['server_now'=>date('H:i:s'),'server_day'=>date('Y-m-d')]);
    case preg_match('#^/admin/reports/(\d+)$#', $path, $m): require_admin(); render('admin_report_chat', ['report'=>['id'=>$m[1],'device_id'=>'mx-demo','report_type'=>'پشتیبانی','category_titles'=>'-','created_at_clock'=>date('H:i:s'),'created_at_day'=>date('Y-m-d'),'messages'=>[]],'ready_messages'=>[]]);
    case $path === '/admin/user-activity': require_admin(); render('admin_user_activity', ['user_id'=>null,'device_id'=>'-','visitor'=>[],'access_titles'=>'-','liked_titles'=>'-','purchases'=>[],'reports'=>[]]);
    case $path === '/site-down': render('site_down');
    case $path === '/site-update': render('site_update', ['fallback_url' => '/']);
    case $path === '/domain-moved': render('site_domain_moved', ['target_url' => 'https://mxdomain.liara.run']);
    case $path === '/iphone-chrome-required': render('iphone_chrome_required', ['next_url' => '/']);
    default: http_response_code(404); echo '404 Not Found';
}
