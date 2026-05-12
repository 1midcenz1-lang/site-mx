<?php $title='MX Video'; ob_start(); ?>
<section class="hero">
  <h1>ورود پنل ادمین</h1>
</section>

<form class="form-card" method="post">
  <label>نام کاربری</label>
  <input name="username" required />

  <label>رمز عبور</label>
  <input name="password" type="password" required />

  <button class="btn" type="submit">ورود</button>

      <div class="result-box error">-</div>
</form>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
