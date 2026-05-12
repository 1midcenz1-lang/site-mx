<?php $title='داشبورد ادمین'; $scripts=['/static/js/admin.js']; ?>
<section class="topbar"><h1>پنل ادمین</h1><div class="topbar-actions"><a class="btn btn-ghost" href="/admin_logout">خروج</a></div></section>
<section class="card"><h3>⏰ زمان فعلی سرور</h3><div class="server-clock-pill"><strong><?= htmlspecialchars($server_now) ?></strong><span><?= htmlspecialchars($server_day) ?></span></div></section>
