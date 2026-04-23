(function () {
  const list = document.getElementById("messages-list");
  if (!list) return;

  const deviceId = (window.MX && window.MX.ensureDeviceId && window.MX.ensureDeviceId())
    || localStorage.getItem("mx_device_id")
    || "";
  if (!deviceId) {
    list.innerHTML = "<div class='card'>شناسه دستگاه پیدا نشد.</div>";
    return;
  }

  async function loadMessages() {
    try {
      const res = await fetch(`/api/my-report-replies?device_id=${encodeURIComponent(deviceId)}`);
      const data = await res.json();
      if (!res.ok || !data.ok) {
        list.innerHTML = "<div class='card'>خطا در دریافت پیام‌ها.</div>";
        return;
      }
      const items = data.items || [];
      if (!items.length) {
        list.innerHTML = "<div class='card'>فعلاً پیامی از ادمین ثبت نشده است.</div>";
      } else {
        list.innerHTML = "";
        items.forEach((item) => {
          const card = document.createElement("details");
          card.className = "accordion-item";
          const summary = document.createElement("summary");
          summary.textContent = `${item.report_type} | ${item.replied_at}`;
          card.appendChild(summary);
          const body = document.createElement("div");
          body.className = "card";
          body.innerHTML = `<p><strong>پیام شما:</strong> ${item.report_text}</p><p><strong>پاسخ ادمین:</strong> ${item.admin_reply}</p>`;
          card.appendChild(body);
          list.appendChild(card);
        });
      }
      await fetch("/api/my-report-replies/mark-seen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: deviceId }),
      });
    } catch (_err) {
      list.innerHTML = "<div class='card'>خطای ارتباط با سرور.</div>";
    }
  }

  loadMessages();
})();
