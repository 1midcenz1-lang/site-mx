<?php $title='خانه'; $scripts=[]; ob_start(); ?>
<section class="purchase-counter">
  <div class="counter-glow"><p>🔥 تعداد اشتراک‌های فعال</p><strong id="total-purchase-counter">45</strong></div>
</section>
<section id="survey" class="table-wrap"><h2>دسته‌بندی‌های قابل مشاهده</h2>
<?php if (!empty($categories)): ?><div class="cards"><?php foreach ($categories as $c): ?>
<article class="card category-card" data-category-id="<?= (int)$c['id'] ?>" data-category-slug="<?= htmlspecialchars($c['slug']) ?>"><div class="category-head"><button class="like-btn" type="button" aria-label="لایک"><span class="like-icon">♡</span><span class="like-text">لایک</span><span class="like-count">0</span></button></div><h5><?= htmlspecialchars($c['title']) ?></h5><a class="btn-small" href="/buy/<?= urlencode($c['slug']) ?>">دریافت فایل</a></article>
<?php endforeach; ?></div><?php else: ?><div class="placeholder">هنوز هیچ دسته‌ای توسط ادمین ساخته نشده است.</div><?php endif; ?></section>
<br><section class="table-wrap"><h2>نظرسنجی مشترکین</h2><p class="muted">فقط کاربرانی که اشتراک تاییدشده دارند می‌توانند نظر ثبت کنند.</p><div class="testimonial-strip"><?php foreach (($testimonials ?? []) as $item): ?><article class="testimonial-card"><h4><?= htmlspecialchars($item['display_name']) ?></h4><p><?= htmlspecialchars($item['content']) ?></p></article><?php endforeach; ?></div></section>
<section class="footer-action"><a class="btn btn-ghost" href="/my-videos">ورود به فایل‌های من</a></section>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
