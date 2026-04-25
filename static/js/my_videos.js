(function () {
  const approvedText = document.getElementById("approved-text");
  const listBox = document.getElementById("video-list");
  const showCodeBtn = document.getElementById("show-code-btn");
  const myCodeBox = document.getElementById("my-code-box");
  if (!approvedText || !listBox) return;

  const deviceId = (window.MX && window.MX.ensureDeviceId())
    || localStorage.getItem("mx_device_id")
    || "";
  if (!deviceId) {
    approvedText.classList.add("error");
    approvedText.textContent = "شناسه دستگاه پیدا نشد. صفحه را دوباره باز کنید.";
    return;
  }
  const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent || "");

  if (showCodeBtn && myCodeBox) {
    showCodeBtn.addEventListener("click", async () => {
      myCodeBox.classList.remove("hidden", "error");
      myCodeBox.textContent = "در حال دریافت کد...";
      try {
        const res = await fetch(`/api/auth/my-code?device_id=${encodeURIComponent(deviceId)}`);
        const data = await res.json();
        if (!res.ok || !data.ok) {
          myCodeBox.classList.add("error");
          if (data && data.login_required) {
            const next = encodeURIComponent(window.location.pathname + window.location.search);
            window.location.href = `/login?next=${next}`;
            return;
          }
          myCodeBox.textContent = data.message || "کد پیدا نشد.";
          return;
        }
        myCodeBox.textContent = `کد شما: ${data.access_code}`;
      } catch (_err) {
        myCodeBox.classList.add("error");
        myCodeBox.textContent = "خطای ارتباط با سرور";
      }
    });
  }

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
