<?php $title='MX Video'; ob_start(); ?>
<section class="topbar">
  <h1>جزئیات کامل کاربر</h1>
  <div class="topbar-actions">
    <a class="btn btn-ghost" href="/admin">بازگشت به داشبورد</a>
  </div>
</section>

<section class="grid-3">
  <article class="card"><h3>device_id</h3><p class="device-id"><?= htmlspecialchars($device_id ?? '-') ?></p></article>
  <article class="card"><h3>آخرین حضور</h3><p>-</p></article>
</section>

<section class="grid-2">
  <article class="card">
    <h3>اطلاعات دستگاه</h3>
    <p>Browser: -</p>
    <p>OS: -</p>
    <p>تعداد ورود: -</p>
  </article>
  <article class="card">
    <h3>دسته‌ها</h3>
    <p><strong>دسترسی‌ها:</strong> <?= htmlspecialchars($access_titles ?? '-') ?></p>
    <p><strong>لایک‌ها:</strong> <?= htmlspecialchars($liked_titles ?? '-') ?></p>
  </article>
</section>

<section class="table-wrap">
  <h2>خریدها</h2>
  <table>
    <thead>
      <tr><th>ID</th><th>دسته درخواستی</th><th>وضعیت</th><th>یادداشت کاربر</th><th>یادداشت ادمین</th><th>زمان</th></tr>
    </thead>
    <tbody>
        <tr>
          <td>-</td>
          <td>-</td>
          <td>-</td>
          <td>-</td>
          <td>-</td>
          <td>-<br><span class="tiny-text">-</span></td>
        </tr>
        <tr><td colspan="6">خریدی ثبت نشده است.</td></tr>
    </tbody>
  </table>
</section>

<section class="table-wrap">
  <h2>ریپورت‌ها</h2>
  <table>
    <thead>
      <tr><th>ID</th><th>موضوع</th><th>متن</th><th>زمان</th><th>لینک</th></tr>
    </thead>
    <tbody>
        <tr>
          <td>-</td>
          <td>-</td>
          <td>-</td>
          <td>-<br><span class="tiny-text">-</span></td>
          <td><a href="/admin/reports/-">باز کردن تیکت</a></td>
        </tr>
        <tr><td colspan="5">ریپورتی ثبت نشده است.</td></tr>
    </tbody>
  </table>
</section>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
