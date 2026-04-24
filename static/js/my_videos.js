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
  const approvedText = document.getElementById("approved-text");
  const listBox = document.getElementById("video-list");
  if (!approvedText || !listBox) return;

  const deviceId = (window.MX && window.MX.ensureDeviceId())
    || localStorage.getItem("mx_device_id")
    || generateUUID();
  localStorage.setItem("mx_device_id", deviceId);
  const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent || "");

  function showNotificationGuidePopup() {
    if (!("Notification" in window)) return;
    const guideKey = `mx_notif_guide_shown_${new Date().toISOString().slice(0, 10)}`;
    if (localStorage.getItem(guideKey) === "1") return;
    if (Notification.permission === "granted") {
      alert("پس از تایید ادمین از طریق نوتیف به شما اطلاع داده میشود.");
    } else {
      alert("لطفا درخواست نوتیف را تایید کنید تا بعد از تایید ادمین به شما اطلاع داده شود.");
      if (Notification.permission === "default") {
        Notification.requestPermission().catch(() => {});
      }
    }
    localStorage.setItem(guideKey, "1");
  }

  async function loadVideos() {
    listBox.innerHTML = "";
    approvedText.classList.remove("error");
    approvedText.textContent = "در حال بررسی...";

    const url = `/api/my-videos?device_id=${encodeURIComponent(deviceId)}`;

    try {
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok || !data.ok) {
        approvedText.classList.add("error");
        approvedText.textContent = data.message || "خطا";
        return;
      }

      approvedText.classList.remove("error");
      approvedText.textContent = data.approved_text;
      showNotificationGuidePopup();

      if (!data.categories.length) {
        listBox.innerHTML = "<div class='card'>هنوز دسترسی فعالی برای این دستگاه ثبت نشده است.</div>";
        return;
      }

      data.categories.forEach((cat) => {
        const wrapper = document.createElement("details");
        wrapper.className = "accordion-item";
        const summary = document.createElement("summary");
        summary.textContent = `دسته ${cat.title}`;
        wrapper.appendChild(summary);

        const card = document.createElement("div");
        card.className = "card";

        if (!cat.videos.length) {
          const p = document.createElement("p");
          p.textContent = "این دسته فعلا فایل ندارد.";
          card.appendChild(p);
        }

        cat.videos.forEach((v) => {
          const link = document.createElement("a");
          const watch = `${v.watch_url}?device_id=${encodeURIComponent(deviceId)}`;
          link.href = v.type === "url" && v.external_url ? v.external_url : watch;
          link.className = "btn";
          link.target = isIOS ? "_self" : "_blank";
          link.textContent = v.title;
          if (isIOS) {
            link.addEventListener("click", () => {
              approvedText.textContent = "در iPhone لینک دانلود با مرورگر پیش‌فرض (Safari/Chrome) باز می‌شود.";
            });
          }
          card.appendChild(link);
          card.appendChild(document.createElement("br"));
          card.appendChild(document.createElement("br"));
        });

        wrapper.appendChild(card);
        listBox.appendChild(wrapper);
      });

      fetch("/api/my-videos/mark-seen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: deviceId }),
      }).catch(() => {});
    } catch (_err) {
      approvedText.classList.add("error");
      approvedText.textContent = "خطای ارتباط با سرور";
    }
  }

  loadVideos();
})();
