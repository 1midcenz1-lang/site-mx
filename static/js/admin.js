(function () {
  const categoryForm = document.getElementById("category-form");
  const videoForm = document.getElementById("video-form");
  const progressWrap = document.getElementById("upload-progress-wrap");
  const progressBar = document.getElementById("upload-progress-bar");
  const progressText = document.getElementById("upload-progress-text");

  if (categoryForm) {
    categoryForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(categoryForm);
      const res = await fetch("/admin/api/categories", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا");
        return;
      }
      alert("دسته ثبت شد");
      window.location.reload();
    });
  }

  document.querySelectorAll(".delete-category-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("این دسته و فایل‌های مربوط به آن حذف شود؟")) return;
      const id = btn.dataset.categoryId;
      const res = await fetch(`/admin/api/categories/${id}/delete`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا در حذف دسته");
        return;
      }
      alert("دسته حذف شد");
      window.location.reload();
    });
  });

  if (videoForm) {
    videoForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(videoForm);
      if (progressWrap && progressBar && progressText) {
        progressWrap.classList.remove("hidden");
        progressBar.style.width = "0%";
        progressText.textContent = "0%";
      }

      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/admin/api/videos");

      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable || !progressBar || !progressText) return;
        const percent = Math.round((event.loaded / event.total) * 100);
        progressBar.style.width = `${percent}%`;
        progressText.textContent = `${percent}%`;
      };

      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText || "{}");
          if (xhr.status < 200 || xhr.status >= 300 || !data.ok) {
            alert(data.message || "خطا");
            return;
          }
          if (progressBar && progressText) {
            progressBar.style.width = "100%";
            progressText.textContent = "100%";
          }
          alert("فایل ثبت شد");
          window.location.reload();
        } catch (_err) {
          alert("خطا در پاسخ سرور");
        }
      };

      xhr.onerror = () => {
        alert("خطا در آپلود فایل");
      };

      xhr.send(fd);
    });
  }

  document.querySelectorAll(".approve-form").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const rid = form.dataset.requestId;
      const fd = new FormData(form);
      const res = await fetch(`/admin/api/requests/${rid}/approve`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا در تایید");
        return;
      }
      alert("تایید شد");
      window.location.reload();
    });
  });

  document.querySelectorAll(".reject-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const rid = btn.dataset.requestId;
      const form = btn.closest("form");
      const reasonInput = form ? form.querySelector("textarea[name='reject_reason']") : null;
      const reason = reasonInput ? reasonInput.value.trim() : "";
      if (reason.length < 5) {
        alert("دلیل رد را کامل وارد کنید.");
        return;
      }
      const fd = new FormData();
      fd.append("reason", reason);
      const res = await fetch(`/admin/api/requests/${rid}/reject`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا در رد درخواست");
        return;
      }
      alert("رد شد");
      window.location.reload();
    });
  });

  document.querySelectorAll(".ban-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.visitorId;
      const res = await fetch(`/admin/api/visitors/${id}/ban`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا در بن");
        return;
      }
      alert("کاربر بن شد");
      window.location.reload();
    });
  });

  document.querySelectorAll(".unban-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.visitorId;
      const res = await fetch(`/admin/api/visitors/${id}/unban`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا در آن‌بن");
        return;
      }
      alert("کاربر آن‌بن شد");
      window.location.reload();
    });
  });

  document.querySelectorAll(".report-ban-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const fd = new FormData();
      fd.append("device_id", btn.dataset.deviceId);
      const res = await fetch("/admin/api/device-ban", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        alert(data.message || "خطا در بن");
        return;
      }
      alert("کاربر گزارش‌دهنده بن شد");
      window.location.reload();
    });
  });
})();
