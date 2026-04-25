(function () {
  const form = document.getElementById("login-form");
  const resultBox = document.getElementById("login-result");
  const nextInput = document.getElementById("next_url");
  if (!form || !resultBox) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = (document.getElementById("login-username")?.value || "").trim();
    const password = (document.getElementById("login-password")?.value || "").trim();
    const deviceId = (window.MX && window.MX.ensureDeviceId && window.MX.ensureDeviceId()) || localStorage.getItem("mx_device_id") || "";
    if (!deviceId) {
      resultBox.classList.add("error");
      resultBox.textContent = "شناسه دستگاه پیدا نشد. صفحه را رفرش کنید.";
      return;
    }
    resultBox.classList.remove("error");
    resultBox.textContent = "در حال ورود...";
    try {
      const res = await fetch("/api/auth/login", {
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
      const nextUrl = (nextInput && nextInput.value) || "/";
      window.location.href = nextUrl;
    } catch (_err) {
      resultBox.classList.add("error");
      resultBox.textContent = "خطای ارتباط با سرور";
    }
  });
})();
