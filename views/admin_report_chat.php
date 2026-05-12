<?php $title='تیکت #'.$report['id']; $scripts=['/static/js/admin.js']; ob_start(); ?>
<section class="topbar"><h1>تیکت #<?= (int)$report['id'] ?></h1><div class="topbar-actions"><a class="btn btn-ghost" href="/admin">بازگشت به داشبورد</a></div></section>
<section class="card"><p><strong>شناسه دستگاه:</strong> <span class="device-id"><?= htmlspecialchars($report['device_id'] ?? '-') ?></span></p><p><strong>موضوع:</strong> <?= htmlspecialchars($report['report_type'] ?? '-') ?></p></section>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
