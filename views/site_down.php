<?php $title='سایت در دسترس نیست'; ob_start(); ?>
<section class="status-page status-page-update"><div class="status-badge">وضعیت دسترسی</div><h1>متاسفانه سایت از دسترس خارج شده</h1><p>اگر مشکلی دارید از همین صفحه تیکت ثبت کنید تا بررسی شود.</p></section>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
