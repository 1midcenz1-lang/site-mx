(function () {
  const form = document.getElementById("buy-form");
  if (!form) return;

  const output = document.getElementById("form-result");
  const pendingNote = document.getElementById("pending-note");
  const deviceInput = document.getElementById("device_id");
  const submitBtn = form.querySelector("button[type='submit']");

  function lockForm(withError) {
    form.classList.add("hidden");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.classList.add("hidden");
    }
    const fileInput = form.querySelector("input[type='file']");
    if (fileInput) fileInput.disabled = true;
    if (withError) output.classList.add("error");
  }

  const deviceId = (window.MX && window.MX.ensureDeviceId())
    || localStorage.getItem("mx_device_id")
    || crypto.randomUUID();
  localStorage.setItem("mx_device_id", deviceId);
  deviceInput.value = deviceId;

  async function recoverFromPendingState() {
    try {
      const res = await fetch(`/api/purchase-status?device_id=${encodeURIComponent(deviceId)}`);
      const data = await res.json();
      if (res.ok && data.ok && data.has_pending) {
        output.classList.add("error");
        output.textContent = data.message || "درحال بررسی پرداختت هستیم.";
        lockForm(true);
        if (pendingNote) pendingNote.classList.remove("hidden");
        return true;
      }
      if (res.ok && data.ok && data.is_rejected && data.rejected_note) {
        output.classList.add("error");
        output.textContent = `درخواست قبلی شما رد شد: ${data.rejected_note}`;
      }
    } catch (_err) {
      // silent
    }
    return false;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    output.classList.remove("error");
    output.textContent = "در حال ارسال فیش...";
    if (pendingNote) pendingNote.classList.add("hidden");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "درحال ارسال...";
    }

    const fd = new FormData(form);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 30000);

    try {
      const res = await fetch("/api/submit-request", {
        method: "POST",
        body: fd,
        signal: controller.signal,
      });
      clearTimeout(timer);
      const data = await res.json();
      if (!res.ok || !data.ok) {
        output.classList.add("error");
        output.textContent = data.message || "خطا در ثبت درخواست";
        if (data.pending_exists) {
          lockForm(true);
          if (pendingNote) pendingNote.classList.remove("hidden");
          return;
        }
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "ارسال فیش و ثبت درخواست";
        }
        return;
      }

      output.classList.remove("error");
      output.textContent = data.message;
      if (pendingNote) pendingNote.classList.remove("hidden");

      setTimeout(() => {
        window.location.href = data.next_url;
      }, 1800);
    } catch (_err) {
      clearTimeout(timer);
      const recovered = await recoverFromPendingState();
      if (!recovered) {
        output.classList.add("error");
        output.textContent = "ارتباط کند بود. دوباره تلاش کنید.";
      }
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "ارسال فیش و ثبت درخواست";
      }
    }
  });

  recoverFromPendingState();
})();
