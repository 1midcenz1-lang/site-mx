<?php $title='ورود ادمین'; ob_start(); ?>
<section class="hero"><h1>ورود پنل ادمین</h1></section>
<form class="form-card" method="post"><label>نام کاربری</label><input name="username" required /><label>رمز عبور</label><input name="password" type="password" required /><button class="btn" type="submit">ورود</button><?php if(!empty($flash)): ?><div class="result-box error"><?= htmlspecialchars($flash) ?></div><?php endif; ?></form>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
