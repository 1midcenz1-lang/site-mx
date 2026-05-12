<?php $title='MX Video'; ob_start(); ?>
<section class="topbar">
  <h1>تیکت #<?= htmlspecialchars($report['id'] ?? '') ?></h1>
  <div class="topbar-actions">
    <a class="btn btn-ghost" href="/admin">بازگشت به داشبورد</a>
  </div>
</section>
<section class="card">
  <p><strong>کاربر:</strong> -</p>
  <p><strong>شناسه دستگاه:</strong> <span class="device-id"><?= htmlspecialchars($report['device_id'] ?? '') ?></span></p>
  <p><strong>موضوع:</strong> <?= htmlspecialchars($report['report_type'] ?? '') ?></p>
  <p><strong>اشتراک‌ها:</strong> <span class="tiny-text"><?= htmlspecialchars($report['category_titles'] ?? '') ?></span></p>
  <p><strong>ثبت:</strong> <?= htmlspecialchars($report['created_at_clock'] ?? '') ?> <span class="tiny-text"><?= htmlspecialchars($report['created_at_day'] ?? '') ?></span></p>
</section>
<section class="form-card">
  <h3>گفت‌وگو</h3>
    <div class="ticket-thread">
      <button class="btn small btn-danger delete-admin-msg-btn" type="button" data-report-id="<?= htmlspecialchars($report['id'] ?? '') ?>" data-msg-id="-">⋯ حذف</button>
      <div class="tiny-text">-<br>-</div>
    </div>
  </div>
  <form class="reply-form" data-report-id="<?= htmlspecialchars($report['id'] ?? '') ?>" style="margin-top:12px;">
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
      <button id="admin-ready-toggle" class="btn small btn-ghost" type="button">+</button>
      <select id="admin-ready-select" class="hidden">
        <option value="">متن آماده...</option>
        <option value="-">-</option>
      </select>
    </div>
    <textarea name="reply_text" rows="3" placeholder="پاسخ ادمین..." required></textarea>
    <button class="btn" type="submit">ثبت پاسخ</button>
  </form>
</section>
<script src="/static/js/admin.js"></script>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
