<?php $title='بروزرسانی سایت'; ob_start(); ?>
<section class="status-page status-page-update"><div class="status-badge">درحال بروزرسانی</div><h1>سایت درحال بروز رسانی هست</h1><p class="muted">لطفا چند دقیقه دیکه مجدد دامنه زیر را باز کنید</p><a class="btn status-link-btn" href="<?= htmlspecialchars($fallback_url) ?>" target="_blank"><?= htmlspecialchars($fallback_url) ?></a></section>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
