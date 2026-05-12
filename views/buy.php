<?php $title='MX Video'; ob_start(); ?>
<section class="hero hero-glass">
  <h1>دریافت اشتراک <?= htmlspecialchars($category['title'] ?? '') ?></h1>
  <p>فقط عکس فیش را ارسال کن؛ سیستم با حساب کاربری و شناسه دستگاه خرید را ثبت می‌کند.</p>
  <pre class="payment-text"><?= htmlspecialchars($category['payment_text'] ?? '') ?></pre>
</section>

<form id="buy-form" class="form-card" enctype="multipart/form-data">
  <input type="hidden" name="category_id" value="<?= (int)($category['id'] ?? 0) ?>" />
  <input type="hidden" name="device_id" id="device_id" />

  <label>عکس فیش</label>
  <input type="file" name="receipt" accept="image/*" required />
  <label>توضیحات (اختیاری)</label>
  <textarea name="request_note" rows="3" placeholder="اگر توضیحی دارید اینجا بنویسید..."></textarea>

  <button class="btn form-submit-btn" type="submit">ارسال فیش و ثبت درخواست</button>
</form>

<div id="form-result" class="result-box"></div>
<div id="pending-note" class="result-box hidden">
  لطفاً صبور باشید؛ بررسی فیش شما ممکن است چند ساعت زمان ببرد. تا زمانی که این فیش تایید نشده، امکان ثبت خرید جدید برای شما غیرفعال است.
</div>

<script src="/static/js/buy.js"></script>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
