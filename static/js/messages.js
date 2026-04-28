(function () {
  const list = document.getElementById("messages-list");
  const newSupportForm = document.getElementById("new-support-form");
  const newSupportText = document.getElementById("new-support-text");
  const newSupportResult = document.getElementById("new-support-result");
  if (!list) return;

  const deviceId = (window.MX && window.MX.ensureDeviceId && window.MX.ensureDeviceId())
    || localStorage.getItem("mx_device_id")
    || "";
  if (!deviceId) {
    list.innerHTML = "<div class='card'>شناسه دستگاه پیدا نشد.</div>";
    return;
  }

  function fmtTime(v) {
    if (!v) return "-";
    const d = new Date(v);
    if (Number.isNaN(d.getTime())) return v;
    const t = d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: true, timeZone: "Asia/Tehran" });
    const dt = d.toLocaleDateString("en-US", { year: "numeric", month: "2-digit", day: "2-digit", timeZone: "Asia/Tehran" });
    return `${t}<br><span class='tiny-text'>${dt}</span>`;
  }
  function fmtTimeParts(v) {
    const html = fmtTime(v);
    const [clock = "-", day = ""] = String(html).split("<br>");
    return { clock, day };
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
          const created = fmtTimeParts(item.created_at);
          const cleanDay = created.day.replace("<span class='tiny-text'>", "").replace("</span>", "");
          summary.innerHTML = `تیکت #${item.id} | ${item.report_type} | ${created.clock} <span class='tiny-text'>${cleanDay}</span>`;
          card.appendChild(summary);
          const body = document.createElement("div");
          body.className = "card";
          const messages = item.messages && item.messages.length
            ? item.messages
            : [{ sender: "user", text: item.report_text, at: item.created_at }];
          body.innerHTML = `<div class="ticket-thread">${
            messages
              .map((m) => `<div class="ticket-msg ${m.sender === "admin" ? "ticket-admin" : "ticket-user"}"><strong>${m.sender === "admin" ? "ادمین" : "شما"}:</strong> ${m.text} <span class="tiny-text">${m.sender === "admin" ? "✓✓" : "✓"}</span><button class="msg-menu-btn" data-msg-id="${m.id}" data-rid="${item.id}" ${m.sender === "admin" ? "disabled" : ""}>حذف پیام</button><div class='tiny-text'>${fmtTime(m.at)}</div></div>`)
              .join("")
          }</div>`;
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
              (window.MX && window.MX.showPopup ? window.MX.showPopup : window.alert)(data.message || "خطا در ارسال پیام");
              return;
            }
            loadMessages();
          });
          body.appendChild(form);
          body.querySelectorAll(".msg-menu-btn").forEach((btn) => {
            btn.addEventListener("click", async () => {
              const rid = btn.getAttribute("data-rid");
              const msgId = btn.getAttribute("data-msg-id");
              if (!rid || !msgId) return;
              const res = await fetch(`/api/reports/${rid}/messages/${msgId}/delete`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ device_id: deviceId }),
              });
              const out = await res.json();
              if (!res.ok || !out.ok) return;
              loadMessages();
            });
          });
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
  if (newSupportForm && newSupportText && newSupportResult) {
    newSupportForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = (newSupportText.value || "").trim();
      if (!text) return;
      const fd = new FormData();
      fd.append("device_id", deviceId);
      fd.append("report_type", "پشتیبانی");
      fd.append("report_text", text);
      const res = await fetch("/api/report", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        newSupportResult.classList.add("error");
        newSupportResult.textContent = data.message || "خطا در ارسال تیکت";
        return;
      }
      newSupportResult.classList.remove("error");
      newSupportResult.textContent = "تیکت جدید ثبت شد.";
      newSupportForm.reset();
      loadMessages();
    });
  }
  setInterval(loadMessages, 120000);
})();
