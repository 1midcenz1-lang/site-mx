(function () {
  const categoryForm = document.getElementById("category-form");
  const videoForm = document.getElementById("video-form");
  const progressWrap = document.getElementById("upload-progress-wrap");
  const progressBar = document.getElementById("upload-progress-bar");
  const progressText = document.getElementById("upload-progress-text");
  const statNodes = document.querySelectorAll("[data-stat-key]");
  const notifToggleBtn = document.getElementById("notif-toggle-btn");
  let lastPurchaseId = 0;
  let lastReportId = 0;
  const NOTIF_KEY = "mx_admin_notif_enabled";
  let notificationsEnabled = localStorage.getItem(NOTIF_KEY) === "1";

  function setStat(key, value) {
    const el = document.querySelector(`[data-stat-key='${key}']`);
    if (!el) return;
    el.textContent = String(value);
  }

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
          alert("اجازه نوتیف داده نشد.");
          return;
        }
      }
      notificationsEnabled = !notificationsEnabled;
      localStorage.setItem(NOTIF_KEY, notificationsEnabled ? "1" : "0");
      renderNotifToggle();
    });
  }

  if (categoryForm) {
    categoryForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(categoryForm);
      const res = await fetch("/admin/api/categories", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا");
        return;
      }
      alert("دسته ثبت شد");
      window.location.reload();
    });
  }

  document.querySelectorAll(".delete-category-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("این دسته و فایل‌های مربوط به آن حذف شود؟")) return;
      const id = btn.dataset.categoryId;
      const res = await fetch(`/admin/api/categories/${id}/delete`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا در حذف دسته");
        return;
      }
      alert("دسته حذف شد");
      window.location.reload();
    });
  });

  document.querySelectorAll(".delete-video-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("این فایل حذف شود؟")) return;
      const id = btn.dataset.videoId;
      const res = await fetch(`/admin/api/videos/${id}/delete`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا در حذف فایل");
        return;
      }
      alert("فایل حذف شد");
      window.location.reload();
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
            alert(data.message || "خطا");
            return;
          }
          if (progressBar && progressText) {
            progressBar.style.width = "100%";
            progressText.textContent = "100%";
          }
          alert("فایل ثبت شد");
          window.location.reload();
        } catch (_err) {
          alert("خطا در پاسخ سرور");
        }
      };

      xhr.onerror = () => {
        alert("خطا در آپلود فایل");
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
        alert(data.message || "خطا در تایید");
        return;
      }
      alert("تایید شد");
      window.location.reload();
    });
  });

  document.querySelectorAll(".reject-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const rid = btn.dataset.requestId;
      const form = btn.closest("form");
      const reasonInput = form ? form.querySelector("textarea[name='reject_reason']") : null;
      const reason = reasonInput ? reasonInput.value.trim() : "";
      if (!reason) {
        alert("دلیل رد را وارد کنید.");
        return;
      }
      const fd = new FormData();
      fd.append("reason", reason);
      const res = await fetch(`/admin/api/requests/${rid}/reject`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا در رد درخواست");
        return;
      }
      alert("رد شد");
      window.location.reload();
    });
  });

  document.querySelectorAll(".reset-pending-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const rid = btn.dataset.requestId;
      const res = await fetch(`/admin/api/requests/${rid}/reset-pending`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا در بازگشت به pending");
        return;
      }
      alert("وضعیت به pending برگشت.");
      window.location.reload();
    });
  });

  document.querySelectorAll(".ban-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.visitorId;
      const res = await fetch(`/admin/api/visitors/${id}/ban`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا در بن");
        return;
      }
      alert("کاربر بن شد");
      window.location.reload();
    });
  });

  document.querySelectorAll(".unban-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.visitorId;
      const res = await fetch(`/admin/api/visitors/${id}/unban`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا در آن‌بن");
        return;
      }
      alert("کاربر آن‌بن شد");
      window.location.reload();
    });
  });

  document.querySelectorAll(".report-ban-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const fd = new FormData();
      fd.append("device_id", btn.dataset.deviceId);
      const res = await fetch("/admin/api/device-ban", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا در بن");
        return;
      }
      alert("کاربر گزارش‌دهنده بن شد");
      window.location.reload();
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
        alert(data.message || "خطا در ثبت پاسخ");
        return;
      }
      alert("پاسخ ثبت شد");
      window.location.reload();
    });
  });

  if (statNodes.length > 0) {
    let primed = false;
    setInterval(async () => {
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
        if (!primed) {
          lastPurchaseId = latestPurchase;
          lastReportId = latestReport;
          primed = true;
          return;
        }
        if (latestPurchase > lastPurchaseId) {
          notifyAdmin("درخواست خرید جدید", `${latestPurchase - lastPurchaseId} خرید جدید ثبت شد.`);
          lastPurchaseId = latestPurchase;
        }
        if (latestReport > lastReportId) {
          notifyAdmin("ریپورت جدید", `${latestReport - lastReportId} ریپورت جدید ثبت شد.`);
          lastReportId = latestReport;
        }
      } catch (_err) {
        // silent
      }
    }, 10000);
  }
})();
