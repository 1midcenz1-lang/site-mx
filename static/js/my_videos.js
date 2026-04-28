(function () {
  const approvedText = document.getElementById("approved-text");
  const listBox = document.getElementById("video-list");
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

  function renderZipTutorialsInline(container) {
    if (!container) return;
    const wrap = document.createElement("div");
    wrap.className = "tutorial-grid";
    wrap.innerHTML = `
      <article class="card tutorial-card">
        <h3>آموزش باز کردن ZIP در iPhone</h3>
        <video class="video-box" controls preload="metadata" playsinline src="https://mxdomain.storage.c2.liara.space/iphone.MOV"></video>
      </article>
      <article class="card tutorial-card">
        <h3>آموزش باز کردن ZIP در Android</h3>
        <video class="video-box" controls preload="metadata" playsinline src="https://mxdomain.storage.c2.liara.space/android.MOV"></video>
      </article>
    `;
    container.appendChild(wrap);
  }

  function showNotificationGuidePopup() {
    if (!("Notification" in window)) return;
    const guideKey = `mx_notif_guide_shown_${new Date().toISOString().slice(0, 10)}`;
    if (localStorage.getItem(guideKey) === "1") return;
    if (Notification.permission === "granted") {
      (window.MX && window.MX.showPopup ? window.MX.showPopup : window.alert)("پس از تایید ادمین از طریق نوتیف به شما اطلاع داده میشود.");
    } else {
      (window.MX && window.MX.showPopup ? window.MX.showPopup : window.alert)("لطفا درخواست نوتیف را تایید کنید تا بعد از تایید ادمین به شما اطلاع داده شود.");
      if (Notification.permission === "default") {
        Notification.requestPermission().catch(() => {});
      }
    }
    localStorage.setItem(guideKey, "1");
  }

  function showZipHelpModal() {
    const backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop";
    backdrop.innerHTML = `
      <div class="modal-card">
        <h3>راهنمای باز کردن ZIP</h3>
        <p>دانلود انجام شد ✅ لطفا ویدیوهای آموزش باز کردن ZIP (iPhone/Android) را در همین صفحه ببینید.</p>
        <button class="btn" type="button">باشه</button>
      </div>
    `;
    const btn = backdrop.querySelector("button");
    if (btn) btn.addEventListener("click", () => backdrop.remove());
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) backdrop.remove();
    });
    document.body.appendChild(backdrop);
  }

  function showSurveyBoostPopup() {
    const key = `mx_survey_boost_${deviceId}`;
    if (localStorage.getItem(key) === "1") return;
    const backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop";
    backdrop.innerHTML = `
      <div class="modal-card">
        <h3>🎁 دسترسی طولانی‌تر</h3>
        <p>با ثبت نظر، شانس تمدید بیشتر دسترسی فایل‌ها را دارید.</p>
        <button class="btn" id="go-survey-btn" type="button">بریم نظر بدیم</button>
      </div>
    `;
    backdrop.querySelector("#go-survey-btn")?.addEventListener("click", () => {
      localStorage.setItem(key, "1");
      window.location.href = "/?open_survey=1";
    });
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) {
        localStorage.setItem(key, "1");
        backdrop.remove();
      }
    });
    document.body.appendChild(backdrop);
  }

  async function loadVideos() {
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
        listBox.innerHTML = "";
        listBox.innerHTML = "<div class='card'>هنوز دسترسی فعالی برای این دستگاه ثبت نشده است.</div>";
        return;
      }
      showSurveyBoostPopup();
      const openIds = new Set(
        Array.from(listBox.querySelectorAll("details[data-cat-id]"))
          .filter((d) => d.open)
          .map((d) => String(d.dataset.catId)),
      );
      const nextHtml = [];
      data.categories.forEach((cat) => {
        const wrapper = document.createElement("details");
        wrapper.className = "accordion-item";
        wrapper.dataset.catId = String(cat.id);
        wrapper.open = openIds.has(String(cat.id));
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
          link.addEventListener("click", () => {
            setTimeout(() => {
              showZipHelpModal();
            }, 1100);
          });
          card.appendChild(link);
          const info = document.createElement("div");
          info.className = "tiny-text";
          info.textContent = `حجم: ${v.file_size || "-"}${v.file_count ? ` | تعداد فایل داخل ZIP: ${v.file_count}` : ""}`;
          card.appendChild(info);
          card.appendChild(document.createElement("br"));
          card.appendChild(document.createElement("br"));
        });
        renderZipTutorialsInline(card);

        wrapper.appendChild(card);
        nextHtml.push(wrapper.outerHTML);
      });
      listBox.innerHTML = nextHtml.join("");

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
  setInterval(loadVideos, 8000);
})();
