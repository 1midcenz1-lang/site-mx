<?php $title='مرورگر مجاز در iPhone'; ob_start(); ?>
<section class="form-card"><h2>مرورگر باید با Chrome یا Safari باز شود</h2><p>در iPhone، برای استفاده کامل سایت لطفا لینک را با <strong>Chrome</strong> یا <strong>Safari</strong> باز کنید.</p><a class="btn btn-ghost" href="<?= htmlspecialchars($next_url) ?>">تلاش دوباره</a></section>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
