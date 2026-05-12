(function () {
  const form = document.getElementById("login-form");
  const resultBox = document.getElementById("login-result");
  const nextInput = document.getElementById("next_url");
  const firstBuyBtn = document.getElementById("first-buy-btn");
  if (!form || !resultBox) return;

  function getDeviceId() {
    return (window.MX && window.MX.ensureDeviceId && window.MX.ensureDeviceId()) || localStorage.getItem("mx_device_id") || "";
  }

  function getNextUrl() {
    return (nextInput && nextInput.value) || "/";
  }

  async function loginWithCode(accessCode, deviceId) {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ access_code: accessCode, device_id: deviceId }),
    });
    return res.json().then((data) => ({ res, data }));
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const accessCode = (document.getElementById("login-code")?.value || "").trim().toUpperCase();
    const deviceId = getDeviceId();
    if (!deviceId) {
      resultBox.classList.add("error");
      resultBox.textContent = "شناسه دستگاه پیدا نشد. صفحه را رفرش کنید.";
      return;
    }
    if (accessCode.length !== 16) {
      resultBox.classList.add("error");
      resultBox.textContent = "کد باید دقیقا ۱۶ کاراکتر باشد.";
      return;
    }
    resultBox.classList.remove("error");
    resultBox.textContent = "در حال ورود...";
    try {
      const { res, data } = await loginWithCode(accessCode, deviceId);
      if (!res.ok || !data.ok) {
        resultBox.classList.add("error");
        resultBox.textContent = data.message || "خطا در ورود";
        return;
      }
      window.location.href = getNextUrl();
    } catch (_err) {
      resultBox.classList.add("error");
      resultBox.textContent = "خطای ارتباط با سرور";
    }
  });

  if (firstBuyBtn) {
    firstBuyBtn.addEventListener("click", async () => {
      const deviceId = getDeviceId();
      if (!deviceId) {
        resultBox.classList.add("error");
        resultBox.textContent = "شناسه دستگاه پیدا نشد. صفحه را رفرش کنید.";
        return;
      }
      resultBox.classList.remove("error");
      resultBox.textContent = "در حال ساخت کد...";
      try {
        const res = await fetch("/api/auth/create-code", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ device_id: deviceId }),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          resultBox.classList.add("error");
          resultBox.textContent = data.message || "خطا در ساخت کد";
          return;
        }
        (window.MX && window.MX.showPopup ? window.MX.showPopup : window.alert)(`کد شما: ${data.access_code}\nحتما این کد را نگه دارید؛ در صورت گم شدن دسترسی شما قطع می‌شود.`);
        resultBox.textContent = `کد ساخته شد: ${data.access_code}`;
        setTimeout(() => {
          window.location.href = getNextUrl();
        }, 1200);
      } catch (_err) {
        resultBox.classList.add("error");
        resultBox.textContent = "خطای ارتباط با سرور";
      }
    });
  }
})();
