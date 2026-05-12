  </main>
  <?php if (empty($isAdminPage)): ?>
  <script src="/static/js/common.js?v=2"></script>
  <?php endif; ?>
  <?php if (!empty($scripts)): foreach ($scripts as $script): ?>
  <script src="<?= htmlspecialchars($script) ?>"></script>
  <?php endforeach; endif; ?>
  <?= $inlineScripts ?? '' ?>
</body>
</html>
