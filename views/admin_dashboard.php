<?php $title='MX Video'; ob_start(); ?>
<section class="topbar">
  <h1>پنل ادمین</h1>
  <div class="topbar-actions">
    <button id="notif-toggle-btn" class="btn btn-ghost" type="button">نوتیف: خاموش</button>
    <button id="download-all-backup-btn" class="btn" type="button">دانلود بکاپ دیتا (DB + Receipts)</button>
    <a class="btn btn-ghost" href="/admin_logout">خروج</a>
  </div>
</section>
<section class="admin-sticky-nav card">
  <a href="#admin-testimonials">نظرات</a>
  <a href="#reports-table">ریپورت‌ها</a>
  <a href="#admin-purchases">خریدها</a>
  <a href="#settings-form">تنظیمات</a>
  <a href="#admin-stats">آمار</a>
</section>
<div id="admin-live-toast" class="hidden" style="position:fixed;top:12px;right:12px;z-index:1300;"></div>
<section id="admin-stats" class="card">
  <h3>⏰ زمان فعلی سرور</h3>
  <div class="server-clock-pill">
    <strong data-stat-key="server_now"><?= htmlspecialchars($server_now ?? '-') ?></strong>
    <span data-stat-key="server_day"><?= htmlspecialchars($server_day ?? '-') ?></span>
  </div>
</section>
<h1>امار بازدید</h1>
<section class="grid-3">
  <article class="card"><h3>آنلاین لحظه‌ای</h3><p data-stat-key="online_total">-</p></article>
    <article class="card"><h3>Android / iPhone / Windows</h3><p><span data-stat-key="online_android">-</span> / <span data-stat-key="online_ios">-</span> / <span data-stat-key="online_windows">-</span></p></article>
  <article class="card"><h3>کل ریپورت‌ها</h3><p data-stat-key="total_reports">-</p></article>
  <article class="card"><h3>کل بازدیدکننده‌ها</h3><p data-stat-key="total_visitors">-</p></article>
</section>
<h1>امار کل</h1>
<section class="grid-3">
  <article class="card"><h3>کل خریدها</h3><p data-stat-key="total_purchases">-</p></article>
  <article class="card"><h3>فیش تایید شده</h3><p data-stat-key="approved_receipts">-</p></article>
  <article class="card"><h3>فیش رد شده</h3><p data-stat-key="rejected_receipts">-</p></article>
    <article class="card"><h3>در انتظار پرداخت</h3><p data-stat-key="pending_receipts">-</p></article>

</section>
<h1>امار امروز</h1>

<section class="grid-3">
  <article class="card"><h3>خریدهای امروز</h3><p data-stat-key="today_purchases">-</p></article>
  <article class="card"><h3>تاییدهای امروز</h3><p data-stat-key="today_approved">-</p></article>
  <article class="card"><h3>فیش رد شده امروز</h3><p data-stat-key="today_rejected">-</p></article>
  <article class="card"><h3>بازدید امروز</h3><p data-stat-key="today_visitors">-</p></article>
</section>
<h1>امار دیروز</h1>
<section class="grid-3">
  <article class="card"><h3>خریدهای دیروز</h3><p data-stat-key="yesterday_purchases">-</p></article>
  <article class="card"><h3>تاییدهای دیروز</h3><p data-stat-key="yesterday_approved">-</p></article>
  <article class="card"><h3>فیش رد شده دیروز</h3><p data-stat-key="yesterday_rejected">-</p></article>
  <article class="card"><h3>بازدید دیروز</h3><p data-stat-key="yesterday_visitors">-</p></article>
</section>
<section class="table-wrap scroll-box">
  <h2>آنلاین در هر صفحه</h2>
  <table>
    <thead><tr><th>صفحه</th><th>تعداد آنلاین</th></tr></thead>
    <tbody id="online-by-page-body">
      <tr><td>-</td><td>-</td></tr>
    </tbody>
  </table>
</section>
<br>
<section id="admin-purchases" class="table-wrap scroll-box">
  <h2>جستجو کاربر</h2>
  <form id="admin-user-search-form" method="GET" class="form-card">
    <label>مثال: کاربر 657</label>
    <input id="admin-user-search-input" name="q" value="<?= htmlspecialchars($visitors_search ?? '') ?>" />
    <button id="admin-user-search-btn" class="btn small" type="submit">اعمال</button>
  </form>
</section>
<br>
<section class="table-wrap scroll-box">
  <h2>درخواست‌های خرید</h2>
  <table>
    <thead>
      <tr>
        <th>کاربر</th>
        <th>شناسه دستگاه</th>
        <th>درخواست</th>
        <th>اشتراک‌های فعال</th>
        <th>زمان خرید (ایران)</th>
        <th>فیش</th>
        <th>مشاهده</th>
        <th>وضعیت</th>
        <th>توضیح کاربر</th>
        <th>یادداشت ادمین</th>
        <th>عملیات</th>
      </tr>
    </thead>
    <tbody id="purchase-rows-body">
      <tr data-request-id="-" data-requested-category="-" data-user-id="-">
        <td>کاربر -</td>
        <td class="device-id">-</td>
        <td>-</td>
        <td class="tiny-text">-</td>
        <td>-<br><span class="tiny-text">-</span></td>
        <td><a class="receipt-open-link" data-receipt-url="/admin/receipt/-?rid=-" href="/admin/receipt/-?rid=-">مشاهده</a></td>
        <td class="status-cell">-</td>
        <td>-</td>
        <td>-</td>
        <td>
          <form class="approve-form" data-request-id="-">
            <div class="chips">
            </div>
            <button class="btn small" type="submit">تایید</button>
            <label>دلیل رد</label>
            <textarea name="reject_reason" rows="2" placeholder="دلیل رد را بنویسید..."></textarea>
            <button class="btn btn-danger small reject-btn" type="button" data-request-id="-">رد</button>
            <button class="btn small btn-ghost fake-btn" type="button" data-request-id="-">فیک</button>
          </form>
            <button class="btn small reset-pending-btn" type="button" data-request-id="-">برگشت به pending</button>
        </td>
      </tr>
    </tbody>
  </table>
</section>
<br>
<section class="grid-2">
  <article class="form-card">
    <h2>افزودن دسته‌بندی</h2>
    <form id="category-form">
      <label>عنوان</label>
      <input name="title" required />
      <label>Slug (انگلیسی)</label>
      <input name="slug" required />
      <label>متن پرداخت</label>
      <textarea name="payment_text" rows="5" required></textarea>
      <button class="btn" type="submit">ثبت دسته</button>
    </form>
  </article>

  <article class="form-card">
    <h2>افزودن فایل ZIP</h2>
    <form id="video-form" enctype="multipart/form-data">
      <label>عنوان فایل</label>
      <input name="title" required />
      <label>دسته</label>
      <select name="category_id" required>
          <option value="-">- (-)</option>
      </select>
      <label>فایل ZIP (اختیاری)</label>
      <input type="file" name="video_file" accept=".zip,application/zip" />
      <label>یا لینک دانلود (اختیاری)</label>
      <input name="external_url" />
      <button class="btn" type="submit">ثبت فایل</button>
      <div id="upload-progress-wrap" class="upload-progress hidden">
        <div class="upload-progress-head">
          <span>در حال آپلود...</span>
          <span id="upload-progress-text">0%</span>
        </div>
        <div class="upload-progress-track">
          <div id="upload-progress-bar" class="upload-progress-bar"></div>
        </div>
      </div>
    </form>
  </article>
</section>

<section class="table-wrap scroll-box">
  <h2>لیست دسته‌بندی‌ها</h2>
  <table>
    <thead>
      <tr><th>ID</th><th>عنوان</th><th>Slug</th><th>اشتراک فعال</th><th>متن پرداخت</th><th>عملیات</th></tr>
    </thead>
    <tbody>
      <tr>
        <td>-</td>
        <td><input class="category-title-input" data-category-id="-" value="-" /></td>
        <td>-</td>
        <td>-</td>
        <td><textarea class="category-payment-input" data-category-id="-" rows="3">-</textarea></td>
        <td>
          <button class="btn small save-category-btn" data-category-id="-" type="button">ذخیره</button>
          <button class="btn small btn-danger delete-category-btn" data-category-id="-" type="button">حذف</button>
        </td>
      </tr>
    </tbody>
  </table>
</section>
<br>
<section class="table-wrap scroll-box">
  <h2>لیست فایل‌ها</h2>
  <table>
    <thead>
      <tr><th>ID</th><th>عنوان</th><th>دسته</th><th>نوع</th><th>حجم</th><th>عملیات</th></tr>
    </thead>
    <tbody>
      <tr>
        <td>-</td>
        <td>-</td>
        <td>-</td>
        <td>-</td>
        <td><button class="btn small btn-danger delete-video-btn" data-video-id="-" type="button">حذف</button></td>
      </tr>
    </tbody>
  </table>
</section>
<br>
<section id="admin-testimonials" class="table-wrap scroll-box">
  <h2>نظرات کاربران</h2>
  <table>
    <thead>
      <tr><th>کاربر</th><th>اشتراک‌ها</th><th>متن</th><th>وضعیت</th><th>عملیات</th></tr>
    </thead>
    <tbody>
      <tr>
        <td>-</td>
        <td class="tiny-text">-</td>
        <td>-</td>
        <td>-</td>
        <td>
          <button class="btn small approve-testimonial-btn" data-testimonial-id="-" type="button">تایید</button>
          <button class="btn small btn-ghost reject-testimonial-btn" data-testimonial-id="-" type="button">رد</button>
          <button class="btn small btn-danger delete-testimonial-btn" data-testimonial-id="-" type="button">حذف</button>
        </td>
      </tr>
    </tbody>
  </table>
</section>
<br>
<section id="reports-table" class="table-wrap scroll-box">
  <h2>ریپورت‌های کاربران</h2>
  <table>
    <thead>
      <tr>
        <th>کاربر</th><th>شناسه دستگاه</th><th>موضوع</th><th>آخرین پیام</th><th>اشتراک‌ها</th><th>زمان (ایران)</th><th>عملیات</th>
      </tr>
    </thead>
    <tbody id="report-rows-body">
      <tr>
        <td>-</td>
        <td class="device-id">-</td>
        <td>-</td>
        <td>
        </td>
        <td class="tiny-text">-</td>
        <td>-<br><span class="tiny-text">-</span></td>
        <td>
          <a class="btn small" href="/admin/reports/-">باز کردن تیکت</a>
          <button class="btn small btn-danger report-ban-btn" data-device-id="-" type="button">بن</button>
          <button class="btn small btn-ghost report-delete-btn" data-report-id="-" type="button">حذف</button>
        </td>
      </tr>
    </tbody>
  </table>
</section>
<br>

<br>
<section class="form-card settings-card">
  <h2>تنظیمات سیستم (DB)</h2>
  <form id="settings-form" class="settings-grid">
    <label>دامنه جدید</label>
    <input name="site_domain_move_target" value="-" />
    <label>لینک بکاپ زمان بروزرسانی</label>
    <input name="maintenance_fallback_url" value="-" />
    <label>مقدار جابجایی UTC (ساعت)</label>
    <input type="number" name="utc_adjust_hours" value="-" />
    <label>حداکثر دستگاه برای هر اکانت</label>
    <input type="number" name="max_devices_per_user" min="1" max="10" value="-" />
    <label>متن زمانی که خرید بسته است (پاپ‌آپ قرمز)</label>
    <textarea name="purchase_disabled_message" rows="3">-</textarea>
    <hr>
    <h3>نوتیف سراسری سایت</h3>
    <label>متن نوتیف</label>
    <textarea name="global_notice_text" rows="2">-</textarea>
    <label>رنگ نوتیف</label>
    <input type="color" name="global_notice_color" value="-" />
    <label>زمان نمایش (ثانیه)</label>
    <input type="number" step="1" name="global_notice_duration_seconds" value="-" />
    <label>محل نمایش</label>
    <select name="global_notice_position">
    </select>
    <label>اندازه فونت (px)</label>
    <input type="number" step="1" name="global_notice_font_size_px" value="-" />
    <label>حداکثر عرض نوتیف (px)</label>
    <input type="number" step="1" name="global_notice_max_width_px" value="-" />
    <hr>
    <h3>متن‌های آماده تیکت</h3>
    <input type="hidden" id="ticket-ready-json-input" name="ticket_ready_messages_json" value="-" />
    <div id="ticket-ready-list"></div>
    <button id="ticket-ready-add-btn" class="btn small btn-ghost" type="button">+ افزودن متن آماده</button>
    <label>صفحه‌ها</label>
    <button class="btn" type="submit">ذخیره تنظیمات</button>
  </form>
</section>
<br>
<section id="admin-files" class="table-wrap scroll-box">
  <h2>خلاصه کامل رفتار کاربرها</h2>
  <table>
    <thead><tr><th>کاربر</th><th>device_id</th><th>Browser</th><th>OS</th><th>وضعیت خرید</th><th>آخرین حضور</th><th>تعداد ورود</th><th>دسته‌های لایک‌شده</th><th>دسترسی‌ها</th><th>تعداد ریپورت</th><th>لینک</th></tr></thead>
    <tbody>
      <tr>
        <td class="device-id">-</td>
        <td>-</td>
        <td>-</td>
        <td class="status-cell">-</td>
        <td>-<br><span class="tiny-text">-</span></td>
        <td>-</td>
        <td class="tiny-text">-</td>
        <td class="tiny-text">-</td>
        <td>-</td>
        <td><a href="-">مشاهده جزئیات</a></td>
      </tr>
    </tbody>
  </table>
</section>
<div id="receipt-modal" class="modal-backdrop hidden">
  <div class="modal-card receipt-modal-card">
    <div class="topbar-actions">
      <a id="receipt-modal-download" class="btn small btn-ghost" href="#" target="_blank" rel="noopener">⬇️ دانلود</a>
      <button id="receipt-modal-close" class="btn btn-danger small receipt-modal-close" type="button">✕</button>
    </div>
    <img id="receipt-modal-image" alt="receipt" class="receipt-modal-image" />
    <form id="receipt-modal-actions" class="approve-form receipt-modal-actions" data-request-id="">
      <div class="chips">
          <label><input type="checkbox" name="category_ids" value="-" />-</label>
      </div>
      <textarea name="reject_reason" rows="2" placeholder="دلیل رد"></textarea>
      <button class="btn small" type="submit">تایید</button>
      <button class="btn small btn-danger reject-btn" type="button">رد</button>
      <button class="btn small btn-ghost fake-btn" type="button">فیک</button>
    </form>
  </div>
</div>

<script src="/static/js/admin.js"></script>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
