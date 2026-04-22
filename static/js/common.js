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

  async function setup() {
    const onboard = await initDevice();
    const deviceId = onboard.deviceId;

    window.MX = window.MX || {};
    window.MX.deviceId = deviceId;
    window.MX.ensureDeviceId = () => deviceId;

    registerVisit(deviceId);
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
  }

  setup();
})();
