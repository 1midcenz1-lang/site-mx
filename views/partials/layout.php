<?php $isAdminPage = str_starts_with(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/', '/admin'); ?>
<!doctype html><html lang="fa" dir="rtl"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title><?= htmlspecialchars($title ?? 'MX Video') ?></title><link rel="stylesheet" href="/static/css/style.css" /></head><body><main class="container">
<?php if (!$isAdminPage): ?>
<section class="quick-links form-card"><a class="btn" href="/">دریافت ویدیو جدید</a><a class="btn btn-ghost my-videos-link" href="/my-videos">مشاهده ویدیوهای من <span id="my-videos-badge" class="notify-badge hidden">0</span></a></section>
<section id="admin-reply-banner" class="alert-banner hidden"><button id="admin-reply-banner-btn" type="button">⚠️ ادمین پاسخی برای شما ثبت کرده - مشاهده</button></section>
<?php endif; include $viewFile; ?>
</main>
<?php if (!$isAdminPage): ?><script src="/static/js/common.js?v=2"></script><?php endif; ?>
<?php if (!empty($scripts)): foreach ($scripts as $s): ?><script src="<?= $s ?>"></script><?php endforeach; endif; ?>
</body></html>
