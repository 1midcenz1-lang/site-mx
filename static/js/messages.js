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
          summary.textContent = `تیکت #${item.id} | ${item.report_type} | ${item.created_at}`;
          card.appendChild(summary);
          const body = document.createElement("div");
          body.className = "card";
          const messages = item.messages && item.messages.length
            ? item.messages
            : [{ sender: "user", text: item.report_text, at: item.created_at }];
          body.innerHTML = messages
            .map((m) => `<p><strong>${m.sender === "admin" ? "ادمین" : "شما"}:</strong> ${m.text} <span class='tiny-text'>(${m.at || "-"})</span></p>`)
            .join("");
          const form = document.createElement("form");
          form.className = "ticket-reply-form";
          form.innerHTML = `
            <textarea rows="2" placeholder="پاسخ شما به ادمین..." required></textarea>
            <button class="btn small" type="submit">ارسال پیام</button>
          `;
          form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const text = (form.querySelector("textarea")?.value || "").trim();
            if (!text) return;
            const res = await fetch(`/api/reports/${item.id}/reply`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ device_id: deviceId, text }),
            });
            const data = await res.json();
            if (!res.ok || !data.ok) {
              alert(data.message || "خطا در ارسال پیام");
              return;
            }
            loadMessages();
          });
          body.appendChild(form);
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
