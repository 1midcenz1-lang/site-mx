<?php
session_start();

$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/';
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

$categories = [
    ['id'=>1,'title'=>'کانال ایرانی','slug'=>'irani','payment_text'=>'پرداخت به شماره کارت درج شده در سایت.'],
    ['id'=>2,'title'=>'کانال خارجی','slug'=>'khareji','payment_text'=>'پرداخت به شماره کارت درج شده در سایت.'],
];
$testimonials = [
    ['display_name'=>'کاربر 102','content'=>'عالی بود','category_titles'=>'کانال ایرانی'],
    ['display_name'=>'کاربر 431','content'=>'کیفیت خیلی خوبه','category_titles'=>'کانال خارجی | کانال ایرانی'],
];

function render($view, $vars = []) {
    extract($vars);
    $viewFile = __DIR__ . '/views/' . $view . '.php';
    include __DIR__ . '/views/partials/layout.php';
    exit;
}

function require_admin() {
    if (empty($_SESSION['admin_logged_in'])) {
        header('Location: /admin/login');
        exit;
    }
}

if ($path === '/admin/login' && $method === 'POST') {
    $u = $_POST['username'] ?? '';
    $p = $_POST['password'] ?? '';
    if ($u === 'admin' && $p === 'mx9091') {
        $_SESSION['admin_logged_in'] = true;
        header('Location: /admin');
    } else {
        $_SESSION['flash'] = 'نام کاربری یا رمز عبور اشتباه است.';
        header('Location: /admin/login');
    }
    exit;
}
if ($path === '/admin_logout') { session_destroy(); header('Location: /admin/login'); exit; }

switch (true) {
    case $path === '/':
        render('home', compact('categories', 'testimonials'));
    case $path === '/login':
        render('login', ['next_url' => $_GET['next'] ?? '/']);
    case $path === '/my-videos':
        render('my_videos');
    case $path === '/messages':
        render('messages');
    case preg_match('#^/buy/([a-zA-Z0-9_-]+)$#', $path, $m):
        $slug = $m[1];
        $category = $categories[0];
        foreach ($categories as $c) if ($c['slug'] === $slug) $category = $c;
        render('buy', compact('category'));
    case $path === '/admin/login':
        $flash = $_SESSION['flash'] ?? null; unset($_SESSION['flash']);
        render('admin_login', compact('flash'));
    case $path === '/admin':
        require_admin();
        render('admin_dashboard', ['server_now'=>date('H:i:s'),'server_day'=>date('Y-m-d'),'stats'=>[],'categories'=>$categories,'videos'=>[],'requests_rows'=>[],'online_by_page'=>[],'visitors_search'=>'']);
    case preg_match('#^/admin/reports/(\d+)$#', $path, $m):
        require_admin();
        $report=['id'=>$m[1],'device_id'=>'mx-demo','report_type'=>'پشتیبانی','category_titles'=>'کانال ایرانی','created_at_clock'=>date('H:i:s'),'created_at_day'=>date('Y-m-d'),'messages'=>[]];
        render('admin_report_chat', ['report'=>$report,'ready_messages'=>[]]);
    case $path === '/admin/user-activity':
        require_admin();
        render('admin_user_activity', ['user_id'=>null,'device_id'=>'-','visitor'=>[],'access_titles'=>'-','liked_titles'=>'-','purchases'=>[],'reports'=>[]]);
    case $path === '/site-down':
        render('site_down');
    case $path === '/site-update':
        render('site_update', ['fallback_url' => '/']);
    case $path === '/domain-moved':
        render('site_domain_moved', ['target_url' => 'https://mxdomain.liara.run']);
    case $path === '/iphone-chrome-required':
        render('iphone_chrome_required', ['next_url' => '/']);
    default:
        http_response_code(404);
        echo '404 Not Found';
}
