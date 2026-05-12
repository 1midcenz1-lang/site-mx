<?php $title='MX Video'; ob_start(); ?>
<section class="hero hero-glass">
  <h1>لیست فایل‌های فعال شما</h1>
  <p>دسترسی شما به صورت خودکار با شناسه همین دستگاه بررسی می‌شود.</p>
  <div id="video-list" class="accordion-list"></div>
</section>
<div id="approved-text" class="result-box"></div>


<script src="/static/js/my_videos.js"></script>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
