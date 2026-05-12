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

  function showCornerFlash(message, options = {}) {
    const box = document.createElement("div");
    box.className = "iphone-corner-flash";
    if (options.red) {
      box.style.background = "rgba(153, 27, 27, 0.96)";
      box.style.borderColor = "#ef4444";
    }
    box.innerHTML = `<div class="iphone-corner-flash-arrow">⬇️</div><div>${message}</div>`;
    document.body.appendChild(box);
    setTimeout(() => box.remove(), 4200);
  }

  function showSiteNotice(message, color, durationMs, options = {}) {
    const box = document.createElement("div");
    box.className = "iphone-corner-flash";
    box.style.top = options.position === "top-right" ? "16px" : "";
    box.style.bottom = options.position === "top-right" ? "auto" : "18px";
    box.style.fontSize = `${Math.max(11, Number(options.fontSizePx || 14))}px`;
    box.style.maxWidth = `${Math.max(200, Number(options.maxWidthPx || 320))}px`;
    if (color) box.style.borderColor = color;
    box.innerHTML = `<div>${message}</div>`;
    document.body.appendChild(box);
    setTimeout(() => box.remove(), Math.max(1000, Number(durationMs || 5000)));
  }

  window.MX = window.MX || {};
  window.MX.showPopup = showPopup;
  window.alert = (msg) => showPopup(String(msg || ""));

  function playNotifyFeedback() {
    try {
      if (navigator.vibrate) navigator.vibrate([120, 60, 120]);
    } catch (_err) {
      // silent
    }
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = "sine";
      o.frequency.value = 880;
      g.gain.value = 0.001;
      o.connect(g);
      g.connect(ctx.destination);
      const now = ctx.currentTime;
      g.gain.exponentialRampToValueAtTime(0.08, now + 0.01);
      g.gain.exponentialRampToValueAtTime(0.0001, now + 0.25);
      o.start(now);
      o.stop(now + 0.25);
    } catch (_err) {
      // silent
    }
  }

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

  const IOS_COMPASS_ALERT_KEY = "mx_ios_compass_alert_count";
  const IOS_COMPASS_ALERT_MAX = 15;
  const IOS_COMPASS_ALERT_TEXT = "توجه حتما حتما روی ایفون باید با مرورگر سافاری یا کروم که خارج از بله هست وارد بشید<br>برای اینکار کافیه روی قطب نما <img src='/static/icon.png' alt='قطب نما' style='width:16px;height:16px;vertical-align:middle;border-radius:4px;' /> کلیک کنید که پایین سمت راسته";

  function showIphoneCompassAlert() {
    if (!isIPhone() || isChromeOnIOS()) return;
    const shown = Number(localStorage.getItem(IOS_COMPASS_ALERT_KEY) || "0");
    if (shown >= IOS_COMPASS_ALERT_MAX) return;
    localStorage.setItem(IOS_COMPASS_ALERT_KEY, String(shown + 1));
    showCornerFlash(IOS_COMPASS_ALERT_TEXT, { red: true });
  }

  function attachIphoneBuyAlerts() {
    if (!isIPhone() || isChromeOnIOS()) return;
    const buyLinks = document.querySelectorAll("a[href^='/buy/']");
    buyLinks.forEach((link) => {
      link.addEventListener("click", (event) => {
        const shown = Number(localStorage.getItem(IOS_COMPASS_ALERT_KEY) || "0");
        if (shown >= IOS_COMPASS_ALERT_MAX) return;
        event.preventDefault();
        localStorage.setItem(IOS_COMPASS_ALERT_KEY, String(shown + 1));
        showCornerFlash(IOS_COMPASS_ALERT_TEXT, { red: true });
        const href = link.getAttribute("href");
        if (href) {
          setTimeout(() => {
            window.location.href = href;
          }, 1200);
        }
      });
    });
  }

  function initDevice() {
    let deviceId = localStorage.getItem("mx_device_id");
    if (deviceId && /^mx-[0-9a-f]{8}$/i.test(deviceId)) {
      deviceId = "";
      localStorage.removeItem("mx_device_id");
    }
    if (!deviceId) {
      if (window.crypto && window.crypto.randomUUID) {
        deviceId = `mx-${window.crypto.randomUUID()}`;
      } else {
        deviceId = `${buildDeviceFingerprint()}-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
      }
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

  function getPageKey() {
    const p = window.location.pathname || "/";
    if (p === "/") return "home";
    if (p === "/my-videos") return "my-videos";
    if (p.startsWith("/buy/")) return "buy";
    return "";
  }

  async function maybeShowGlobalNotice() {
    const page = getPageKey();
    if (!page) return;
    try {
      const res = await fetch(`/api/global-notice?page=${encodeURIComponent(page)}`);
      const data = await res.json();
      if (!(res.ok && data.ok && data.enabled && data.text)) return;
      const key = `mx_global_notice_seen_${page}_${btoa(unescape(encodeURIComponent(data.text))).slice(0, 20)}`;
      if (sessionStorage.getItem(key) === "1") return;
      sessionStorage.setItem(key, "1");
      showSiteNotice(data.text, data.color, data.duration_ms, {
        position: data.position || "top-right",
        fontSizePx: data.font_size_px || 14,
        maxWidthPx: data.max_width_px || 320,
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
    setInterval(() => sendPresence(deviceId), 500000);
    maybeShowGlobalNotice();
    const videosBadge = document.getElementById("my-videos-badge");
    async function refreshVideosBadge() {
      if (!videosBadge) return;
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
    refreshVideosBadge();
    setInterval(refreshVideosBadge, 12000);

    const reportForm = document.getElementById("report-form");
    const reportResult = document.getElementById("report-result");
    const reportDeviceInput = document.getElementById("report_device_id");
    const reportPanel = document.getElementById("report-panel");
    const reportToggle = document.getElementById("report-toggle");
    const supportToggle = document.getElementById("support-toggle");
    const surveyToggle = document.getElementById("survey-toggle");
    const surveyPanel = document.getElementById("survey-panel");
    const surveyForm = document.getElementById("survey-form");
    const surveyResult = document.getElementById("survey-result");
    const surveyDeviceInput = document.getElementById("survey_device_id");
    const reportReplies = document.getElementById("report-replies");
    const messagesToggle = document.getElementById("admin-messages-toggle");
    const messagesCountBadge = document.getElementById("admin-messages-count");
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
          if (reportTypeSelect) reportTypeSelect.value = "مستحجن";
          reportPanel.scrollIntoView({ behavior: "smooth", block: "start" });
          const textArea = reportForm ? reportForm.querySelector("textarea[name='report_text']") : null;
          if (textArea) textArea.focus({ preventScroll: true });
        }
      });
    }
    if (supportToggle && reportPanel) {
      supportToggle.addEventListener("click", () => {
        window.location.href = "/messages";
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
    const params = new URLSearchParams(window.location.search);
    if (params.get("open_survey") === "1" && surveyPanel) {
      surveyPanel.classList.remove("hidden");
      reportPanel?.classList.add("hidden");
      surveyPanel.scrollIntoView({ behavior: "smooth", block: "start" });
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
          playNotifyFeedback();
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
        if (messagesCountBadge) {
          messagesCountBadge.classList.toggle("hidden", unseenCount <= 0);
          messagesCountBadge.textContent = String(unseenCount);
        }
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
