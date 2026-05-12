<?php $title='MX Video'; ob_start(); ?>
<section class="purchase-counter">
  <div class="counter-glow">
    <p>🔥 تعداد اشتراک‌های فعال</p>
    <strong id="total-purchase-counter">45</strong>
  </div>
</section>
<section id="survey" class="table-wrap">
  <h2>دسته‌بندی‌های قابل مشاهده</h2>
  <div class="cards">
    <article class="card category-card" data-category-id="-" data-category-slug="-">
      <div class="category-head">
        <button class="like-btn" type="button" aria-label="لایک">
          <span class="like-icon">♡</span>
          <span class="like-text">لایک</span><span class="like-count">0</span>
        </button>
      </div>
      <h5>-</h5>
      <a class="btn-small" href="/buy/-">دریافت فایل</a>
    </article>
  </div>
  <div class="placeholder">هنوز هیچ دسته‌ای توسط ادمین ساخته نشده است.</div>
</section>
<br>
<section class="table-wrap">
  <h2>نظرسنجی مشترکین</h2>
  <p class="muted">فقط کاربرانی که اشتراک تاییدشده دارند می‌توانند نظر ثبت کنند.</p>
  <div class="testimonial-strip">
    <article class="testimonial-card">
      <h4>-</h4>
      <p>-</p>
      <div class="mini-chip-wrap">
        <span class="mini-chip">-</span>
      </div>
    </article>
  </div>
</section>
<section class="footer-action">
  <a class="btn btn-ghost" href="/my-videos">ورود به فایل‌های من</a>
</section>

<script>
  (function () {
    const cards = document.querySelectorAll(".category-card");
    const deviceId = (window.MX && window.MX.ensureDeviceId && window.MX.ensureDeviceId())
      || localStorage.getItem("mx_device_id")
      || "";
    if (!deviceId) return;
    const liked = new Set();

    function renderCard(card, isLiked, countValue) {
      const btn = card.querySelector(".like-btn");
      const icon = card.querySelector(".like-icon");
      const text = card.querySelector(".like-text");
      const count = card.querySelector(".like-count");
      if (!btn || !icon || !text || !count) return;
      btn.classList.toggle("active", isLiked);
      icon.textContent = isLiked ? "❤" : "♡";
      text.textContent = isLiked ? "لایک" : "لایک";
      count.textContent = `(${countValue || 0})`;
    }

    async function loadLikes() {
      const res = await fetch(`/api/category-likes?device_id=${encodeURIComponent(deviceId)}`);
      const data = await res.json();
      if (!res.ok || !data.ok) return;
      liked.clear();
      (data.liked || []).forEach((id) => liked.add(String(id)));
      cards.forEach((card) => {
        const id = card.dataset.categoryId;
        if (!id) return;
        renderCard(card, liked.has(id), (data.counts || {})[id] || 0);
      });
    }

    cards.forEach((card) => {
      const id = card.dataset.categoryId;
      const btn = card.querySelector(".like-btn");
      if (!btn) return;
      if (!id) return;
      let inFlight = false;
      btn.addEventListener("click", () => {
        if (inFlight) return;
        inFlight = true;
        const nextLiked = !liked.has(String(id));
        fetch("/api/category-likes/toggle", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ category_id: Number(id), device_id: deviceId, liked: nextLiked }),
        })
          .then((res) => res.json())
          .then((data) => {
            if (!data.ok) return;
            if (data.liked) liked.add(String(id));
            else liked.delete(String(id));
            renderCard(card, data.liked, data.count || 0);
            const fx = document.createElement("span");
            fx.className = "like-burst";
            fx.textContent = data.liked ? "💖" : "✨";
            btn.appendChild(fx);
            setTimeout(() => fx.remove(), 850);
          })
          .finally(() => {
            inFlight = false;
          });
      });
    });
    loadLikes();

    const counterEl = document.getElementById("total-purchase-counter");
    function animateCounter(from, to) {
      if (!counterEl) return;
      const start = Number(from || 0);
      const end = Number(to || 0);
      const duration = 700;
      const startAt = performance.now();
      function frame(now) {
        const progress = Math.min(1, (now - startAt) / duration);
        const current = Math.round(start + ((end - start) * progress));
        if (progress < 1) requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    }
    function burstFx() {
      const fx = document.createElement("div");
      fx.className = "fx-burst";
      for (let i = 0; i < 24; i += 1) {
        const p = document.createElement("span");
        p.style.setProperty("--x", `${(Math.random() * 320) - 160}px`);
        p.style.setProperty("--y", `${(Math.random() * -180) - 30}px`);
        p.style.background = `hsl(${Math.floor(Math.random() * 360)} 100% 60%)`;
        fx.appendChild(p);
      }
      document.body.appendChild(fx);
      setTimeout(() => fx.remove(), 1200);
    }

    async function refreshPublicStats() {
      if (!counterEl) return;
      try {
        const res = await fetch("/api/public-stats");
        const data = await res.json();
        if (!res.ok || !data.ok) return;
        const prev = Number(counterEl.dataset.count || 0);
        const next = Number(data.total_purchases || 0);
        if (next !== prev) {
          animateCounter(prev, next);
          counterEl.dataset.count = String(next);
          burstFx();
        }
      } catch (_err) {
        // silent
      }
    }
    setInterval(refreshPublicStats, 8000);
  })();
</script>
<?php $content=ob_get_clean(); include __DIR__.'/partials/header.php'; echo $content; include __DIR__.'/partials/footer.php'; ?>
