<?php $title='جزئیات کاربر'; ob_start(); ?>
<section class="topbar"><h1>جزئیات کامل کاربر</h1><div class="topbar-actions"><a class="btn btn-ghost" href="/admin">بازگشت به داشبورد</a></div></section>
<section class="grid-3"><article class="card"><h3>کاربر</h3><p><?= $user_id ? 'کاربر '.(int)$user_id : '-' ?></p></article><article class="card"><h3>device_id</h3><p class="device-id"><?= htmlspecialchars($device_id ?? '-') ?></p></article><article class="card"><h3>آخرین حضور</h3><p><?= htmlspecialchars($visitor['last_seen_at'] ?? '-') ?></p></article></section>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
