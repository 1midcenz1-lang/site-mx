(function () {
  const form = document.getElementById("login-form");
  const resultBox = document.getElementById("login-result");
  const nextInput = document.getElementById("next_url");
  const registerBtn = document.getElementById("register-btn");
  const loginBtn = document.getElementById("login-btn");
  if (!form || !resultBox) return;
  let mode = "login";

  function getDeviceId() {
    return (window.MX && window.MX.ensureDeviceId && window.MX.ensureDeviceId()) || localStorage.getItem("mx_device_id") || "";
  }

  function getNextUrl() {
    return (nextInput && nextInput.value) || "/";
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = (document.getElementById("login-username")?.value || "").trim().toLowerCase();
    const password = (document.getElementById("login-password")?.value || "").trim();
    const deviceId = getDeviceId();
    if (!deviceId) {
      resultBox.classList.add("error");
      resultBox.textContent = "شناسه دستگاه پیدا نشد. صفحه را رفرش کنید.";
      return;
    }
    if (!username || !password) {
      resultBox.classList.add("error");
      resultBox.textContent = "نام کاربری و رمز عبور لازم است.";
      return;
    }
    resultBox.classList.remove("error");
    resultBox.textContent = "در حال ورود...";
    try {
      const endpoint = mode === "register" ? "/api/auth/register" : "/api/auth/login";
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, device_id: deviceId }),
      });
      const data = await res.json();
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

  if (registerBtn) {
    registerBtn.addEventListener("click", () => {
      mode = "register";
      form.requestSubmit();
    });
  }
  if (loginBtn) {
    loginBtn.addEventListener("click", () => {
      mode = "login";
    });
  }
})();
