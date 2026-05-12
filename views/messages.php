<?php $title='MX Video'; ob_start(); ?>
<section class="hero hero-glass">
  <h1>تیکت‌های پشتیبانی</h1>
  <p>اینجا می‌توانید گفت‌وگو بین خودتان و ادمین را برای هر ریپورت ادامه دهید.</p>
  <div id="messages-list" class="accordion-list"></div>
  <br>
  <div class="form-card">
    <h3>ثبت درخواست پشتیبانی جدید</h3>
    <form id="new-support-form">
      <textarea id="new-support-text" rows="3" placeholder="مشکل یا درخواست جدیدت رو بنویس..." required></textarea>
      <button class="btn" type="submit">ارسال تیکت جدید</button>
    </form>
    <div id="new-support-result" class="result-box"></div>
  </div>
</section>

<script src="/static/js/messages.js"></script>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
