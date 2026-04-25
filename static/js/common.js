(function () {
  function hashFNV1a(input) {
    let hash = 0x811c9dc5;
    for (let i = 0; i < input.length; i += 1) {
      hash ^= input.charCodeAt(i);
      hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
    }
    return (hash >>> 0).toString(16).padStart(8, "0");
  }

  function normalizeUserAgentForFingerprint(ua) {
    return String(ua || "")
      .replace(/(crios|fxios|edgios|opios|duckduckgo|yaapp_ios|safari)\/[\d._]+/gi, "$1")
      .replace(/version\/[\d._]+/gi, "version")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function generateDeterministicDeviceId() {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "unknown";
    const nav = window.navigator || {};
    const screenData = window.screen || {};
    const fingerprintRaw = [
      normalizeUserAgentForFingerprint(nav.userAgent),
      nav.platform || "",
      nav.language || "",
      nav.languages ? nav.languages.join(",") : "",
      tz,
      screenData.width || "",
      screenData.height || "",
      screenData.colorDepth || "",
      nav.hardwareConcurrency || "",
      nav.maxTouchPoints || "",
    ].join("|");
    const fingerprintHash = hashFNV1a(fingerprintRaw);
    return `mx-${fingerprintHash}`;
  }

  function isIPhone() {
    const ua = navigator.userAgent || "";
    return /iPhone/i.test(ua);
  }

  function isChromeOnIOS() {
    const ua = navigator.userAgent || "";
    return /CriOS/i.test(ua);
  }

  function showChromeRequiredGate() {
    const gate = document.createElement("div");
    gate.className = "chrome-required-gate";
    gate.innerHTML = `
      <div class="chrome-required-card">
        <h3>فقط با Chrome آیفون وارد شوید</h3>
        <p>برای ادامه، این صفحه باید با Google Chrome باز شود.</p>
        <button type="button" class="btn" id="open-in-chrome-btn">باز کردن در Chrome</button>
        <p class="hint">اگر خودکار باز نشد، لینک را کپی کنید و داخل Chrome باز کنید.</p>
      </div>
    `;
    document.body.appendChild(gate);

    const chromeUrl = `googlechromes://${window.location.href.replace(/^https?:\/\//i, "")}`;
    const openBtn = document.getElementById("open-in-chrome-btn");
    if (openBtn) {
      openBtn.addEventListener("click", () => {
        window.location.href = chromeUrl;
      });
    }
    setTimeout(() => {
      window.location.href = chromeUrl;
    }, 450);
  }

  function initDevice() {
    const stableId = generateDeterministicDeviceId();
    localStorage.setItem("mx_device_id", stableId);
    let deviceId = stableId;
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
    if (isIPhone() && !isChromeOnIOS()) {
      showChromeRequiredGate();
      return;
    }

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
    const reportReplies = document.getElementById("report-replies");

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

    if (reportReplies) {
      try {
        const res = await fetch(`/api/my-report-replies?device_id=${encodeURIComponent(deviceId)}`);
        const data = await res.json();
        if (res.ok && data.ok && data.items && data.items.length) {
          reportReplies.classList.remove("hidden");
          reportReplies.textContent = data.items
            .map((item) => `${item.report_type} | ${item.created_at}\n${item.report_text}\nپاسخ ادمین (${item.replied_at}): ${item.admin_reply}`)
            .join("\n\n------------------\n\n");
        }
      } catch (_err) {
        // silent
      }
    }
  }

  setup();
})();
