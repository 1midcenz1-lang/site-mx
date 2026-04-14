(function () {
  const button = document.getElementById("load-videos-btn");
  if (!button) return;

  const approvedText = document.getElementById("approved-text");
  const listBox = document.getElementById("video-list");

  const deviceId = (window.MX && window.MX.ensureDeviceId())
    || localStorage.getItem("mx_device_id")
    || crypto.randomUUID();
  localStorage.setItem("mx_device_id", deviceId);

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

      if (!data.categories.length) {
        listBox.innerHTML = "<div class='card'>هنوز دسترسی فعالی برای این دستگاه ثبت نشده است.</div>";
        return;
      }

      data.categories.forEach((cat) => {
        const card = document.createElement("article");
        card.className = "card";
        const title = document.createElement("h3");
        title.textContent = `دسته ${cat.title}`;
        card.appendChild(title);

        if (!cat.videos.length) {
          const p = document.createElement("p");
          p.textContent = "این دسته فعلا فایل ندارد.";
          card.appendChild(p);
        }

        cat.videos.forEach((v) => {
          const link = document.createElement("a");
          const watch = `${v.watch_url}?device_id=${encodeURIComponent(deviceId)}`;
          link.href = watch;
          link.className = "btn";
          link.target = "_blank";
          link.textContent = v.title;
          card.appendChild(link);
          card.appendChild(document.createElement("br"));
          card.appendChild(document.createElement("br"));
        });

        listBox.appendChild(card);
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

  button.addEventListener("click", loadVideos);
  loadVideos();
})();
