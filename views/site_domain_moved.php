<?php $title='انتقال دامنه'; ob_start(); ?>
<section class="status-page status-page-domain"><div class="status-badge">اطلاعیه دامنه جدید</div><h1>سایت به دامنه زیر انتقال یافته</h1><p>لطفا لینک زیر را با <strong>Chrome</strong> باز کنید:</p><a class="btn status-link-btn" href="<?= htmlspecialchars($target_url) ?>" target="_blank" rel="noopener noreferrer"><?= htmlspecialchars($target_url) ?></a></section>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
