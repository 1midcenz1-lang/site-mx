<?php $title='ورود ادمین'; ?>
<section class="hero"><h1>ورود پنل ادمین</h1></section>
<form class="form-card" method="post"><label>نام کاربری</label><input name="username" required /><label>رمز عبور</label><input name="password" type="password" required /><button class="btn" type="submit">ورود</button><?php if(!empty($flash)): ?><div class="result-box error"><?= htmlspecialchars($flash) ?></div><?php endif; ?></form>
