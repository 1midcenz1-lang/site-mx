<?php $title='MX Video'; ob_start(); ?>
<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>انتقال دامنه</title>
  <link rel="stylesheet" href="/static/css/style.css" />
</head>
<body>
  <main class="container">
    <section class="status-page status-page-domain">
      <div class="status-badge">اطلاعیه دامنه جدید</div>
      <h1>سایت به دامنه زیر انتقال یافته</h1>
      <p>لطفا لینک زیر را با <strong>Chrome</strong> باز کنید:</p>
      <a class="btn status-link-btn" href="<?= htmlspecialchars($target_url ?? '') ?>" target="_blank" rel="noopener noreferrer"><?= htmlspecialchars($target_url ?? '') ?></a>
    </section>
  </main>
</body>
<script>
  (function () {
    async function checkStatus() {
      try {
        const res = await fetch("/api/system-status");
        const data = await res.json();
        if (res.ok && data.ok && !data.site_domain_move_mode) {
          window.location.replace("/");
        }
      } catch (_err) {
        // silent
      }
    }
    checkStatus();
    setInterval(checkStatus, 5000);
  })();
</script>
</html>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
