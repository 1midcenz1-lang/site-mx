(function () {
  const form = document.getElementById("buy-form");
  if (!form) return;

  const output = document.getElementById("form-result");
  const authForm = document.getElementById("auth-form");
  const authResult = document.getElementById("auth-result");
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
    || "";
  if (!deviceId) {
    output.classList.add("error");
    output.textContent = "شناسه دستگاه پیدا نشد. صفحه را دوباره باز کنید.";
    return;
  }
  deviceInput.value = deviceId;
  let isLoggedIn = false;

  function setBuyEnabled(enabled) {
    form.style.opacity = enabled ? "1" : "0.6";
    form.style.pointerEvents = enabled ? "auto" : "none";
  }

  async function refreshAuthStatus() {
    try {
      const res = await fetch(`/api/auth/status?device_id=${encodeURIComponent(deviceId)}`);
      const data = await res.json();
      isLoggedIn = Boolean(res.ok && data.ok && data.logged_in);
      if (!isLoggedIn) {
        output.classList.add("error");
        output.textContent = "برای ثبت خرید ابتدا وارد حساب کاربری شوید.";
      } else {
        output.classList.remove("error");
        output.textContent = `وارد شده‌اید: ${data.username || "-"}`;
      }
      setBuyEnabled(isLoggedIn);
    } catch (_err) {
      setBuyEnabled(false);
    }
  }

  if (authForm) {
    authForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      authResult.classList.remove("error");
      authResult.textContent = "در حال ورود...";
      const username = (document.getElementById("auth-username")?.value || "").trim();
      const password = (document.getElementById("auth-password")?.value || "").trim();
      try {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password, device_id: deviceId }),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          authResult.classList.add("error");
          authResult.textContent = data.message || "خطا در ورود";
          return;
        }
        authResult.textContent = `ورود موفق: ${data.username}`;
        await refreshAuthStatus();
      } catch (_err) {
        authResult.classList.add("error");
        authResult.textContent = "خطای ارتباط با سرور";
      }
    });
  }

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
    if (!isLoggedIn) {
      output.classList.add("error");
      output.textContent = "ابتدا وارد حساب شوید.";
      return;
    }
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

  setBuyEnabled(false);
  refreshAuthStatus().then(() => {
    if (isLoggedIn) recoverFromPendingState();
  });
})();
