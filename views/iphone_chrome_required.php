<?php $title='MX Video'; ob_start(); ?>
<section class="form-card">
  <h2>مرورگر باید با Chrome یا Safari باز شود</h2>
  <p>در iPhone، برای استفاده کامل سایت لطفا لینک را با <strong>Chrome</strong> یا <strong>Safari</strong> باز کنید.</p>
  <p>روی آیکون <strong>🧭</strong> (قطب‌نما) در گوشه مرورگر بزنید و گزینه باز کردن با Safari/Chrome را انتخاب کنید.</p>
  <a class="btn" href="#" id="auto-open-btn">کلیک کنید روی این آیکون 🧭</a>
  <a class="btn btn-ghost" href="googlechrome://navigate?url=<?= urlencode($next_url ?? '/') ?>">باز کردن مستقیم با Chrome</a>
  <a class="btn btn-ghost" href="<?= htmlspecialchars($next_url ?? '/') ?>">باز کردن با Safari</a>
  <a class="btn btn-ghost" href="<?= htmlspecialchars($next_url ?? '/') ?>">تلاش دوباره</a>
</section>
<script>
  (function () {
    const target = "<?= htmlspecialchars($next_url ?? '/') ?>";
    const chromeTarget = `googlechrome://navigate?url=${encodeURIComponent(target)}`;
    const safariTarget = target.replace(/^https:\/\//i, "x-safari-https://").replace(/^http:\/\//i, "x-safari-http://");
    const autoBtn = document.getElementById("auto-open-btn");
    if (autoBtn) {
      autoBtn.addEventListener("click", (e) => {
        e.preventDefault();
        window.location.href = chromeTarget;
        setTimeout(() => {
          window.location.href = safariTarget || target;
        }, 900);
      });
    }
    setTimeout(() => {
      window.location.href = chromeTarget;
      setTimeout(() => {
        window.location.href = safariTarget || target;
      }, 900);
    }, 700);
  })();
</script>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
