(function () {
  const categoryForm = document.getElementById("category-form");
  const videoForm = document.getElementById("video-form");
  const progressWrap = document.getElementById("upload-progress-wrap");
  const progressBar = document.getElementById("upload-progress-bar");
  const progressText = document.getElementById("upload-progress-text");
  const statNodes = document.querySelectorAll("[data-stat-key]");
  const notifToggleBtn = document.getElementById("notif-toggle-btn");
  const onlineByPageBody = document.getElementById("online-by-page-body");
  const settingsForm = document.getElementById("settings-form");
  const backupAllBtn = document.getElementById("download-all-backup-btn");
  const unseenBanner = document.getElementById("admin-unseen-banner");
  const unseenText = document.getElementById("admin-unseen-text");
  const liveToast = document.getElementById("admin-live-toast");
  let refreshLiveStats = async () => {};
  let lastPurchaseId = 0;
  let lastReportId = 0;
  let lastTestimonialId = 0;
  const NOTIF_KEY = "mx_admin_notif_enabled";
  let notificationsEnabled = localStorage.getItem(NOTIF_KEY) === "1";

  function showPopup(message, tone) {
    const backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop";
    backdrop.innerHTML = `
      <div class="modal-card">
        <h3>${tone === "error" ? "خطا" : "پیام"}</h3>
        <p>${message}</p>
        <button class="btn ${tone === "error" ? "btn-danger" : ""}" type="button">متوجه شدم</button>
      </div>
    `;
    const close = () => backdrop.remove();
    backdrop.querySelector("button")?.addEventListener("click", close);
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) close();
    });
    document.body.appendChild(backdrop);
  }
  window.alert = (msg) => showPopup(String(msg || ""));

  function setStat(key, value) {
    const el = document.querySelector(`[data-stat-key='${key}']`);
    if (!el) return;
    el.textContent = String(value);
  }

  setInterval(() => {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    const ss = String(now.getSeconds()).padStart(2, "0");
    setStat("server_now", `${hh}:${mm}:${ss}`);
  }, 1000);

  function notifyAdmin(title, body) {
    if (!notificationsEnabled) return;
    if (!("Notification" in window)) return;
    if (Notification.permission === "granted") {
      new Notification(title, { body });
      return;
    }
    if (Notification.permission !== "denied") {
      Notification.requestPermission().then((permission) => {
        if (permission === "granted") {
          new Notification(title, { body });
        }
      });
    }
  }

  function showLiveToast(text) {
    if (!liveToast) return;
    liveToast.innerHTML = `<div class="modal-card">${text}</div>`;
    liveToast.classList.remove("hidden");
    setTimeout(() => liveToast.classList.add("hidden"), 3500);
  }

  function renderNotifToggle() {
    if (!notifToggleBtn) return;
    notifToggleBtn.textContent = notificationsEnabled ? "نوتیف: روشن" : "نوتیف: خاموش";
    notifToggleBtn.classList.toggle("btn-danger", notificationsEnabled);
  }

  if (notifToggleBtn) {
    renderNotifToggle();
    notifToggleBtn.addEventListener("click", async () => {
      if (!notificationsEnabled && "Notification" in window && Notification.permission !== "granted") {
        const perm = await Notification.requestPermission();
        if (perm !== "granted") {
          showPopup("اجازه نوتیف داده نشد.");
          return;
        }
      }
      notificationsEnabled = !notificationsEnabled;
      localStorage.setItem(NOTIF_KEY, notificationsEnabled ? "1" : "0");
      renderNotifToggle();
    });
  }

  if (settingsForm) {
    settingsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(settingsForm);
      const res = await fetch("/admin/api/settings", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در ذخیره تنظیمات");
        return;
      }
      showPopup("تنظیمات ذخیره شد");
      refreshLiveStats();
    });
  }

  if (categoryForm) {
    categoryForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(categoryForm);
      const res = await fetch("/admin/api/categories", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا");
        return;
      }
      showPopup("دسته ثبت شد");
      refreshLiveStats();
    });
  }

  if (backupAllBtn) {
    backupAllBtn.addEventListener("click", () => {
      window.open("/admin/api/backup-db", "_blank");
      setTimeout(() => {
        window.open("/admin/api/backup-receipts", "_blank");
      }, 600);
    });
  }

  document.querySelectorAll(".save-category-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.categoryId;
      const titleInput = document.querySelector(`.category-title-input[data-category-id='${id}']`);
      const paymentInput = document.querySelector(`.category-payment-input[data-category-id='${id}']`);
      const fd = new FormData();
      fd.append("title", titleInput ? titleInput.value : "");
      fd.append("payment_text", paymentInput ? paymentInput.value : "");
      const res = await fetch(`/admin/api/categories/${id}/update`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در ذخیره دسته");
        return;
      }
      showPopup("دسته بروزرسانی شد");
    });
  });

  document.querySelectorAll(".delete-category-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("این دسته و فایل‌های مربوط به آن حذف شود؟")) return;
      const id = btn.dataset.categoryId;
      const res = await fetch(`/admin/api/categories/${id}/delete`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در حذف دسته");
        return;
      }
      showPopup("دسته حذف شد");
      btn.closest("tr")?.remove();
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".delete-video-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("این فایل حذف شود؟")) return;
      const id = btn.dataset.videoId;
      const res = await fetch(`/admin/api/videos/${id}/delete`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در حذف فایل");
        return;
      }
      showPopup("فایل حذف شد");
      btn.closest("tr")?.remove();
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".delete-testimonial-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("این نظر حذف شود؟")) return;
      const id = btn.dataset.testimonialId;
      const res = await fetch(`/admin/api/testimonials/${id}/delete`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در حذف نظر");
        return;
      }
      showPopup("نظر حذف شد");
      btn.closest("tr")?.remove();
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".approve-testimonial-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.testimonialId;
      const res = await fetch(`/admin/api/testimonials/${id}/approve`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در تایید نظر");
        return;
      }
      showPopup("نظر تایید شد");
      const row = btn.closest("tr");
      if (row) {
        const cells = row.querySelectorAll("td");
        if (cells[3]) cells[3].textContent = "approved";
      }
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".reject-testimonial-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.testimonialId;
      const res = await fetch(`/admin/api/testimonials/${id}/reject`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در رد نظر");
        return;
      }
      showPopup("نظر رد شد");
      const row = btn.closest("tr");
      if (row) {
        const cells = row.querySelectorAll("td");
        if (cells[3]) cells[3].textContent = "rejected";
      }
      refreshLiveStats();
    });
  });

  if (videoForm) {
    videoForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(videoForm);
      if (progressWrap && progressBar && progressText) {
        progressWrap.classList.remove("hidden");
        progressBar.style.width = "0%";
        progressText.textContent = "0%";
      }

      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/admin/api/videos");

      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable || !progressBar || !progressText) return;
        const percent = Math.round((event.loaded / event.total) * 100);
        progressBar.style.width = `${percent}%`;
        progressText.textContent = `${percent}%`;
      };

      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText || "{}");
          if (xhr.status < 200 || xhr.status >= 300 || !data.ok) {
            showPopup(data.message || "خطا");
            return;
          }
          if (progressBar && progressText) {
            progressBar.style.width = "100%";
            progressText.textContent = "100%";
          }
          showPopup("فایل ثبت شد");
          refreshLiveStats();
        } catch (_err) {
          showPopup("خطا در پاسخ سرور");
        }
      };

      xhr.onerror = () => {
        showPopup("خطا در آپلود فایل");
      };

      xhr.send(fd);
    });
  }

  document.querySelectorAll(".approve-form").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const rid = form.dataset.requestId;
      const fd = new FormData(form);
      const res = await fetch(`/admin/api/requests/${rid}/approve`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در تایید");
        return;
      }
      showPopup("تایید شد");
      const row = form.closest("tr");
      if (row) {
        const cells = row.querySelectorAll("td");
        if (cells[6]) cells[6].textContent = "approved";
        if (cells[8]) cells[8].textContent = "-";
      }
    });
  });

  document.querySelectorAll(".reject-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const rid = btn.dataset.requestId;
      const form = btn.closest("form");
      const reasonInput = form ? form.querySelector("textarea[name='reject_reason']") : null;
      const reason = reasonInput ? reasonInput.value.trim() : "";
      if (!reason) {
        showPopup("دلیل رد را وارد کنید.");
        return;
      }
      const fd = new FormData();
      fd.append("reason", reason);
      const res = await fetch(`/admin/api/requests/${rid}/reject`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در رد درخواست");
        return;
      }
      showPopup("رد شد");
      const row = btn.closest("tr");
      if (row) {
        const cells = row.querySelectorAll("td");
        if (cells[6]) cells[6].textContent = "rejected";
        if (cells[8]) cells[8].textContent = reason;
      }
    });
  });

  document.querySelectorAll(".reset-pending-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const rid = btn.dataset.requestId;
      const res = await fetch(`/admin/api/requests/${rid}/reset-pending`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در بازگشت به pending");
        return;
      }
      showPopup("وضعیت به pending برگشت.");
      const row = btn.closest("tr");
      if (row) {
        const cells = row.querySelectorAll("td");
        if (cells[6]) cells[6].textContent = "pending";
      }
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".ban-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.visitorId;
      const res = await fetch(`/admin/api/visitors/${id}/ban`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در بن");
        return;
      }
      showPopup("کاربر بن شد");
      btn.textContent = "بن شد";
      btn.disabled = true;
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".unban-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.visitorId;
      const res = await fetch(`/admin/api/visitors/${id}/unban`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در آن‌بن");
        return;
      }
      showPopup("کاربر آن‌بن شد");
      btn.textContent = "آن‌بن شد";
      btn.disabled = true;
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".report-ban-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const fd = new FormData();
      fd.append("device_id", btn.dataset.deviceId);
      const res = await fetch("/admin/api/device-ban", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در بن");
        return;
      }
      showPopup("کاربر گزارش‌دهنده بن شد");
      btn.disabled = true;
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".reply-form").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const rid = form.dataset.reportId;
      const fd = new FormData(form);
      const res = await fetch(`/admin/api/reports/${rid}/reply`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در ثبت پاسخ");
        return;
      }
      showPopup("پاسخ ثبت شد");
      const row = form.closest("tr");
      const thread = row ? row.querySelector(".ticket-thread") : null;
      const text = form.querySelector("textarea[name='reply_text']")?.value || "";
      if (thread) {
        const item = document.createElement("div");
        item.className = "ticket-msg ticket-admin";
        item.innerHTML = `<strong>ادمین</strong>: ${text}`;
        thread.appendChild(item);
      }
      refreshLiveStats();
    });
  });

  if (statNodes.length > 0) {
    let primed = false;
    refreshLiveStats = async () => {
      try {
        const res = await fetch("/admin/api/live-stats");
        const data = await res.json();
        if (!res.ok || !data.ok) return;
        const stats = data.stats || {};
        Object.keys(stats).forEach((key) => {
          if (key === "latest_purchase_id" || key === "latest_report_id") return;
          setStat(key, stats[key]);
        });
        const latestPurchase = Number(stats.latest_purchase_id || 0);
        const latestReport = Number(stats.latest_report_id || 0);
        const latestTestimonial = Number(stats.latest_testimonial_id || 0);
        if (!primed) {
          lastPurchaseId = latestPurchase;
          lastReportId = latestReport;
          lastTestimonialId = latestTestimonial;
          primed = true;
          return;
        }
        const unseenPurchase = Math.max(0, latestPurchase - lastPurchaseId);
        const unseenReport = Math.max(0, latestReport - lastReportId);
        const unseenTestimonial = Math.max(0, latestTestimonial - lastTestimonialId);
        if (unseenPurchase > 0) {
          notifyAdmin("درخواست خرید جدید", `${unseenPurchase} خرید جدید ثبت شد.`);
          showLiveToast("🛒 خرید جدید ثبت شد");
          lastPurchaseId = latestPurchase;
        }
        if (unseenReport > 0) {
          notifyAdmin("ریپورت جدید", `${unseenReport} ریپورت جدید ثبت شد.`);
          showLiveToast("📩 ریپورت جدید ثبت شد");
          lastReportId = latestReport;
        }
        if (unseenTestimonial > 0) {
          notifyAdmin("نظر جدید", `${unseenTestimonial} نظر جدید ثبت شد.`);
          showLiveToast("💬 نظر جدید ثبت شد");
          lastTestimonialId = latestTestimonial;
        }
        const totalUnseen = unseenPurchase + unseenReport + unseenTestimonial;
        if (unseenBanner && unseenText) {
          if (totalUnseen > 0) {
            unseenBanner.classList.remove("hidden");
            unseenText.textContent = `خرید: ${unseenPurchase} | ریپورت: ${unseenReport} | نظر: ${unseenTestimonial}`;
          } else {
            unseenBanner.classList.add("hidden");
          }
        }
        if (onlineByPageBody && data.online_by_page) {
          const rows = Object.entries(data.online_by_page)
            .map(([page, count]) => `<tr><td>${page}</td><td>${count}</td></tr>`)
            .join("");
          onlineByPageBody.innerHTML = rows || "<tr><td colspan='2'>-</td></tr>";
        }
      } catch (_err) {
        // silent
      }
    };
    refreshLiveStats();
    setInterval(refreshLiveStats, 1000);
  }
})();
