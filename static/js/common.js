(function () {
  function showPopup(message, tone) {
    const backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop";
    backdrop.innerHTML = `
      <div class="modal-card">
        <h3>${tone === "error" ? "خطا" : "پیام"}</h3>
        <p>${message}</p>
        <button class="btn ${tone === "error" ? "btn-danger" : ""}" type="button">باشه</button>
      </div>
    `;
    const close = () => backdrop.remove();
    backdrop.querySelector("button")?.addEventListener("click", close);
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) close();
    });
    document.body.appendChild(backdrop);
  }

  window.MX = window.MX || {};
  window.MX.showPopup = showPopup;
  window.alert = (msg) => showPopup(String(msg || ""));

  function isIPhone() {
    const ua = navigator.userAgent || "";
    const isiPhoneUA = /iPhone|iPod/i.test(ua);
    const isiPadAsMac = navigator.platform === "MacIntel" && (navigator.maxTouchPoints || 0) > 1;
    return isiPhoneUA || isiPadAsMac;
  }

  function isChromeOnIOS() {
    return /CriOS/i.test(navigator.userAgent || "");
  }

  function hash32(input) {
    let h = 2166136261;
    for (let i = 0; i < input.length; i += 1) {
      h ^= input.charCodeAt(i);
      h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24);
    }
    return (h >>> 0).toString(16).padStart(8, "0");
  }

  function buildDeviceFingerprint() {
    const parts = [
      navigator.platform || "na",
      String(navigator.maxTouchPoints || 0),
      String(navigator.hardwareConcurrency || 0),
      String(navigator.deviceMemory || 0),
      String(screen.width || 0),
      String(screen.height || 0),
      String(screen.colorDepth || 0),
      String(window.devicePixelRatio || 1),
      Intl.DateTimeFormat().resolvedOptions().timeZone || "na",
      navigator.language || "na",
      navigator.vendor || "na",
    ];
    return `mx-${hash32(parts.join("|"))}`;
  }

  function showIphoneCompassAlert() {
    if (!isIPhone() || isChromeOnIOS()) return;
    const shown = Number(localStorage.getItem("mx_ios_popup_count") || "0");
    if (shown >= 4) return;
    localStorage.setItem("mx_ios_popup_count", String(shown + 1));
    showPopup("اگر با این مرورگر نیستید نگران نشوید؛ ممکنه باشید ولی بهتره روی این آیکون بزنید: <img src='/icon.png' onerror=\"this.src='/static/icon.png'\" alt='icon' style='width:26px;height:26px;vertical-align:middle;border-radius:6px;margin:0 6px;'/> و لینک را با Chrome یا Safari باز کنید.");
  }

  function attachIphoneBuyAlerts() {
    if (!isIPhone() || isChromeOnIOS()) return;
    const buyLinks = document.querySelectorAll("a[href^='/buy/']");
    buyLinks.forEach((link) => {
      link.addEventListener("click", () => {
        showPopup("برای آیفون: قبل از خرید روی این آیکون بزنید <img src='/icon' onerror=\"this.src='/static/icon.png'\" alt='icon' style='width:26px;height:26px;vertical-align:middle;border-radius:6px;margin:0 6px;'/> و با Chrome یا Safari ادامه بدید.");
      });
    });
  }

  function initDevice() {
    let deviceId = localStorage.getItem("mx_device_id");
    if (!deviceId) {
      deviceId = buildDeviceFingerprint();
      localStorage.setItem("mx_device_id", deviceId);
    }
    document.cookie = `mx_device_id=${encodeURIComponent(deviceId)}; Max-Age=31536000; Path=/; SameSite=Lax`;
    return { deviceId };
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
    showIphoneCompassAlert();
    attachIphoneBuyAlerts();
    const onboard = initDevice();
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
    const surveyPanel = document.getElementById("survey-panel");
    const surveyForm = document.getElementById("survey-form");
    const surveyResult = document.getElementById("survey-result");
    const surveyDeviceInput = document.getElementById("survey_device_id");
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
    if (surveyDeviceInput) surveyDeviceInput.value = deviceId;

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
        if (surveyPanel) {
          surveyPanel.classList.toggle("hidden");
          reportPanel.classList.add("hidden");
          if (!surveyPanel.classList.contains("hidden")) {
            surveyPanel.scrollIntoView({ behavior: "smooth", block: "start" });
            const textArea = surveyForm ? surveyForm.querySelector("textarea[name='testimonial_text']") : null;
            if (textArea) textArea.focus({ preventScroll: true });
          }
        }
      });
    }
    if (messagesToggle) {
      messagesToggle.addEventListener("click", () => {
        window.location.href = "/messages";
      });
    }
    if (adminReplyBannerBtn) {
      adminReplyBannerBtn.addEventListener("click", () => {
        window.location.href = "/messages";
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
            if (data && data.login_required) {
              const next = encodeURIComponent(window.location.href);
              window.location.href = `/login?next=${next}`;
              return;
            }
            reportResult.classList.add("error");
            reportResult.textContent = data.message || "خطا در ارسال ریپورت";
            return;
          }
          reportResult.textContent = data.message;
          reportForm.reset();
          if (reportDeviceInput) reportDeviceInput.value = deviceId;
          if ("Notification" in window) {
            if (Notification.permission === "granted") {
              showPopup("ریپورت ثبت شد. پس از تایید ادمین از طریق نوتیف به شما اطلاع داده می‌شود.");
            } else {
              showPopup("ریپورت ثبت شد. لطفا درخواست نوتیف را تایید کنید تا بعد از تایید ادمین به شما اطلاع داده شود.");
            }
          }
        } catch (_err) {
          reportResult.classList.add("error");
          reportResult.textContent = "خطای ارتباط با سرور";
        }
      });
    }

    if (surveyForm && surveyResult) {
      surveyForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        surveyResult.classList.remove("error");
        surveyResult.textContent = "در حال ارسال نظر...";
        const fd = new FormData(surveyForm);
        try {
          const res = await fetch("/api/testimonials", { method: "POST", body: fd });
          const data = await res.json();
          if (!res.ok || !data.ok) {
            surveyResult.classList.add("error");
            surveyResult.textContent = data.message || "خطا در ثبت نظر";
            return;
          }
          surveyResult.textContent = data.message;
          surveyForm.reset();
          if (surveyDeviceInput) surveyDeviceInput.value = deviceId;
        } catch (_err) {
          surveyResult.classList.add("error");
          surveyResult.textContent = "خطای ارتباط با سرور";
        }
      });
    }

    async function refreshReplyBox() {
      if (!reportReplies) return;
      try {
        const res = await fetch(`/api/my-report-replies?device_id=${encodeURIComponent(deviceId)}`);
        const data = await res.json();
        if (!(res.ok && data.ok && data.items && data.items.length)) {
          if (messagesToggle) messagesToggle.classList.remove("has-alert");
          if (adminReplyBanner) adminReplyBanner.classList.add("hidden");
          reportReplies.textContent = "فعلا پاسخی از ادمین ثبت نشده است.";
          return;
        }
        reportReplies.textContent = data.items
          .map((item) => `${item.report_type} | ${item.created_at}\n${item.report_text}\nپاسخ ادمین (${item.replied_at}): ${item.admin_reply}`)
          .join("\n\n------------------\n\n");
        const unseenCount = Number(data.unseen_count || 0);
        if (messagesToggle) messagesToggle.classList.toggle("has-alert", unseenCount > 0);
        if (adminReplyBanner) adminReplyBanner.classList.toggle("hidden", unseenCount <= 0);
        const latestReplyId = Number(data.items[0].id || 0);
        const oldReplyId = Number(localStorage.getItem("mx_last_reply_id") || "0");
        if (
          unseenCount > 0 &&
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
