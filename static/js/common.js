(function () {
  function generateUUID() {
    // اگر crypto موجود بود استفاده کن
    if (window.crypto && crypto.randomUUID) {
      return crypto.randomUUID();
    }

    // fallback ساده (UUID v4-like)
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
  function initDevice() {
    let deviceId = localStorage.getItem("mx_device_id");
    if (!deviceId) {
      deviceId = generateUUID();
      localStorage.setItem("mx_device_id", deviceId);
    }
    return Promise.resolve({ deviceId });
  }

  async function registerVisit(deviceId) {
    try {
      await fetch("/api/register-visit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: deviceId }),
      });
    } catch (_err) {
      // silent
    }
  }

  async function sendPresence(deviceId) {
    const pageKey = window.location.pathname || "/";
    try {
      await fetch("/api/presence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: deviceId, page_key: pageKey }),
      });
    } catch (_err) {
      // silent
    }
  }

  async function setup() {
    const onboard = await initDevice();
    const deviceId = onboard.deviceId;

    window.MX = window.MX || {};
    window.MX.deviceId = deviceId;
    window.MX.ensureDeviceId = () => deviceId;

    registerVisit(deviceId);
    sendPresence(deviceId);
    setInterval(() => sendPresence(deviceId), 30000);
    const videosBadge = document.getElementById("my-videos-badge");
    if (videosBadge) {
      try {
        const res = await fetch(`/api/my-videos/summary?device_id=${encodeURIComponent(deviceId)}`);
        const data = await res.json();
        if (res.ok && data.ok && data.total_categories > 0) {
          const unseen = Number(data.unseen_categories || 0);
          videosBadge.classList.remove("hidden");
          videosBadge.textContent = String(unseen > 0 ? unseen : data.total_categories);
          videosBadge.classList.toggle("is-red", unseen > 0);
          videosBadge.classList.toggle("is-blue", unseen <= 0);
        }
      } catch (_err) {
        // silent
      }
    }

    const reportForm = document.getElementById("report-form");
    const reportResult = document.getElementById("report-result");
    const reportDeviceInput = document.getElementById("report_device_id");
    const reportPanel = document.getElementById("report-panel");
    const reportToggle = document.getElementById("report-toggle");
    const surveyToggle = document.getElementById("survey-toggle");
    const reportReplies = document.getElementById("report-replies");
    const messagesToggle = document.getElementById("admin-messages-toggle");
    const adminReplyBanner = document.getElementById("admin-reply-banner");
    const adminReplyBannerBtn = document.getElementById("admin-reply-banner-btn");
    const reportTypeSelect = reportForm ? reportForm.querySelector("select[name='report_type']") : null;
    const notifEnabled = localStorage.getItem("mx_user_notif_enabled") !== "0";
    let notifAsked = false;

    async function ensureNotificationPermission() {
      if (!("Notification" in window)) return;
      if (!notifEnabled) return;
      if (Notification.permission !== "default") return;
      if (notifAsked) return;
      notifAsked = true;
      try {
        const perm = await Notification.requestPermission();
        if (perm === "denied") localStorage.setItem("mx_user_notif_enabled", "0");
      } catch (_err) {
        // silent
      }
    }

    ensureNotificationPermission();
    document.addEventListener("click", () => {
      ensureNotificationPermission();
    });

    if (reportDeviceInput) reportDeviceInput.value = deviceId;

    if (reportToggle && reportPanel) {
      reportToggle.addEventListener("click", () => {
        const isHidden = reportPanel.classList.toggle("hidden");
        if (!isHidden) {
          reportPanel.scrollIntoView({ behavior: "smooth", block: "start" });
          const textArea = reportForm ? reportForm.querySelector("textarea[name='report_text']") : null;
          if (textArea) textArea.focus({ preventScroll: true });
        }
      });
    }
    if (surveyToggle && reportPanel) {
      surveyToggle.addEventListener("click", () => {
        reportPanel.classList.remove("hidden");
        if (reportTypeSelect) reportTypeSelect.value = "نظرسنجی";
        reportPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
    if (messagesToggle && reportReplies) {
      messagesToggle.addEventListener("click", () => {
        if (reportPanel) reportPanel.classList.remove("hidden");
        reportReplies.classList.toggle("hidden");
        reportReplies.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }
    if (adminReplyBannerBtn && reportReplies) {
      adminReplyBannerBtn.addEventListener("click", () => {
        if (reportPanel) reportPanel.classList.remove("hidden");
        reportReplies.classList.remove("hidden");
        reportReplies.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }

    if (reportForm) {
      reportForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        reportResult.classList.remove("error");
        reportResult.textContent = "در حال ارسال ریپورت...";
        const fd = new FormData(reportForm);

        try {
          const res = await fetch("/api/report", { method: "POST", body: fd });
          const data = await res.json();
          if (!res.ok || !data.ok) {
            reportResult.classList.add("error");
            reportResult.textContent = data.message || "خطا در ارسال ریپورت";
            return;
          }
          reportResult.textContent = data.message;
          reportForm.reset();
          if (reportDeviceInput) reportDeviceInput.value = deviceId;
        } catch (_err) {
          reportResult.classList.add("error");
          reportResult.textContent = "خطای ارتباط با سرور";
        }
      });
    }

    async function refreshReplyBox() {
      if (!reportReplies) return;
      try {
        const res = await fetch(`/api/my-report-replies?device_id=${encodeURIComponent(deviceId)}`);
        const data = await res.json();
        if (!(res.ok && data.ok && data.items && data.items.length)) {
          reportReplies.textContent = "فعلا پاسخی از ادمین ثبت نشده است.";
          return;
        }
        reportReplies.textContent = data.items
          .map((item) => `${item.report_type} | ${item.created_at}\n${item.report_text}\nپاسخ ادمین (${item.replied_at}): ${item.admin_reply}`)
          .join("\n\n------------------\n\n");
        if (messagesToggle) messagesToggle.classList.add("has-alert");
        if (adminReplyBanner) adminReplyBanner.classList.remove("hidden");
        const latestReplyId = Number(data.items[0].id || 0);
        const oldReplyId = Number(localStorage.getItem("mx_last_reply_id") || "0");
        if (
          latestReplyId > oldReplyId &&
          "Notification" in window &&
          Notification.permission === "granted" &&
          notifEnabled
        ) {
          new Notification("پاسخ جدید ادمین", { body: "برای مشاهده پاسخ وارد سایت شوید." });
        }
        if (latestReplyId > oldReplyId) localStorage.setItem("mx_last_reply_id", String(latestReplyId));
      } catch (_err) {
        // silent
      }
    }

    async function refreshPurchaseNotification() {
      try {
        const res = await fetch(`/api/purchase-status?device_id=${encodeURIComponent(deviceId)}`);
        const data = await res.json();
        if (!(res.ok && data.ok)) return;
        const status = data.latest_status || "none";
        const oldStatus = localStorage.getItem("mx_last_purchase_status") || "none";
        if (
          status !== oldStatus &&
          oldStatus !== "none" &&
          status === "approved" &&
          "Notification" in window &&
          Notification.permission === "granted" &&
          notifEnabled
        ) {
          new Notification("خرید شما تایید شد ✅", { body: "برای مشاهده فایل‌ها وارد بخش ویدیوهای من شوید." });
        }
        localStorage.setItem("mx_last_purchase_status", status);
      } catch (_err) {
        // silent
      }
    }

    refreshReplyBox();
    refreshPurchaseNotification();
    setInterval(refreshReplyBox, 12000);
    setInterval(refreshPurchaseNotification, 12000);
  }

  setup();
})();
