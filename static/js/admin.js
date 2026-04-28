(function () {
  const categoryForm = document.getElementById("category-form");
  const videoForm = document.getElementById("video-form");
  const progressWrap = document.getElementById("upload-progress-wrap");
  const progressBar = document.getElementById("upload-progress-bar");
  const progressText = document.getElementById("upload-progress-text");
  const statNodes = document.querySelectorAll("[data-stat-key]");
  const notifToggleBtn = document.getElementById("notif-toggle-btn");
  const onlineByPageBody = document.getElementById("online-by-page-body");
  const settingsForm = document.getElementById("settings-form");
  const backupAllBtn = document.getElementById("download-all-backup-btn");
  const purchaseRowsBody = document.getElementById("purchase-rows-body");
  const reportRowsBody = document.getElementById("report-rows-body");
  const userSearchForm = document.getElementById("admin-user-search-form");
  const userSearchInput = document.getElementById("admin-user-search-input");
  const liveToast = document.getElementById("admin-live-toast");
  const receiptModal = document.getElementById("receipt-modal");
  const receiptModalImage = document.getElementById("receipt-modal-image");
  const receiptModalClose = document.getElementById("receipt-modal-close");
  const receiptModalActions = document.getElementById("receipt-modal-actions");
  let refreshLiveStats = async () => {};
  let lastPurchaseId = 0;
  let lastReportId = 0;
  let lastTestimonialId = 0;
  const NOTIF_KEY = "mx_admin_notif_enabled";
  let notificationsEnabled = localStorage.getItem(NOTIF_KEY) === "1";
  let receiptModalOpen = false;
  const categoryChips = Array.from(document.querySelectorAll(".category-title-input")).map((input) => ({
    id: input.dataset.categoryId,
    title: input.value,
  }));

  function showPopup(message, tone) {
    const backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop";
    backdrop.innerHTML = `
      <div class="modal-card">
        <h3>${tone === "error" ? "خطا" : "پیام"}</h3>
        <p>${message}</p>
        <button class="btn ${tone === "error" ? "btn-danger" : ""}" type="button">متوجه شدم</button>
      </div>
    `;
    const close = () => backdrop.remove();
    backdrop.querySelector("button")?.addEventListener("click", close);
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) close();
    });
    document.body.appendChild(backdrop);
  }
  window.alert = (msg) => showPopup(String(msg || ""));

  function setStat(key, value) {
    const el = document.querySelector(`[data-stat-key='${key}']`);
    if (!el) return;
    el.textContent = String(value);
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function renderPendingActions(rid, requestedCategory = "") {
    const chips = categoryChips
      .map((c) => `<label><input type="checkbox" name="category_ids" value="${escapeHtml(c.id)}" ${c.title === requestedCategory ? "checked" : ""} />${escapeHtml(c.title)}</label>`)
      .join("");
    return `<form class="approve-form" data-request-id="${rid}">
      <div class="chips">${chips}</div>
      <button class="btn small" type="submit">تایید</button>
      <label>دلیل رد</label>
      <textarea name="reject_reason" rows="2" placeholder="دلیل رد را بنویسید..."></textarea>
      <button class="btn btn-danger small reject-btn" type="button" data-request-id="${rid}">رد</button>
      <button class="btn small btn-ghost fake-btn" type="button" data-request-id="${rid}">فیک</button>
    </form>`;
  }

  function renderResetAction(rid) {
    return `<button class="btn small reset-pending-btn" type="button" data-request-id="${rid}">برگشت به pending</button>`;
  }

  function highlightUserPurchases(userId) {
    if (!purchaseRowsBody) return false;
    const rows = Array.from(purchaseRowsBody.querySelectorAll("tr"));
    let matched = false;
    rows.forEach((row) => {
      const isTarget = String(row.dataset.userId || "") === String(userId);
      row.classList.toggle("row-highlight", isTarget);
      if (isTarget && !matched) {
        matched = true;
        row.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });
    return matched;
  }

  function normalizeDigits(value) {
    const fa = "۰۱۲۳۴۵۶۷۸۹";
    const ar = "٠١٢٣٤٥٦٧٨٩";
    return String(value || "").replace(/[۰-۹٠-٩]/g, (ch) => {
      const faIdx = fa.indexOf(ch);
      if (faIdx >= 0) return String(faIdx);
      const arIdx = ar.indexOf(ch);
      if (arIdx >= 0) return String(arIdx);
      return ch;
    });
  }

  function statusBadge(text) {
    const value = String(text || "").trim();
    if (value.includes("فیک")) return `<span class="status-pill status-pill-fake">🟧 ${escapeHtml(value)}</span>`;
    if (value.includes("تایید شده")) return `<span class="status-pill status-pill-ok">🟩 ${escapeHtml(value)}</span>`;
    if (value.includes("تایید نشده")) return `<span class="status-pill status-pill-bad">🟥 ${escapeHtml(value)}</span>`;
    return `<span class="status-pill status-pill-pending">🟨 ${escapeHtml(value || "-")}</span>`;
  }

  function applyStatusBadges() {
    document.querySelectorAll(".status-cell").forEach((cell) => {
      const raw = cell.getAttribute("data-raw-status") || cell.textContent || "";
      cell.setAttribute("data-raw-status", raw);
      cell.innerHTML = statusBadge(raw);
    });
  }

  document.addEventListener("click", async (evt) => {
    const target = evt.target;
    if (!(target instanceof Element)) return;
    const resetBtn = target.closest(".reset-pending-btn");
    if (resetBtn) {
      const rid = resetBtn.dataset.requestId;
      const res = await fetch(`/admin/api/requests/${rid}/reset-pending`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) return showPopup(data.message || "خطا در بازگشت به pending");
      showPopup("وضعیت به pending برگشت.");
      const row = resetBtn.closest("tr");
      if (row) {
        const cells = row.querySelectorAll("td");
        if (cells[7]) {
          cells[7].setAttribute("data-raw-status", "در انتظار بررسی");
          cells[7].innerHTML = statusBadge("در انتظار بررسی");
        }
        if (cells[9]) cells[9].textContent = "-";
        if (cells[10]) cells[10].innerHTML = renderPendingActions(rid, row.dataset.requestedCategory || "");
        row.querySelectorAll(".approve-form").forEach((form) => bindApproveForm(form));
      }
      refreshLiveStats();
      refreshLiveFeed();
      return;
    }
    const rejectBtn = target.closest(".reject-btn");
    if (rejectBtn) {
      const rid = rejectBtn.dataset.requestId;
      const form = rejectBtn.closest("form");
      const reasonInput = form ? form.querySelector("textarea[name='reject_reason']") : null;
      const reason = reasonInput ? reasonInput.value.trim() : "";
      if (!reason) return showPopup("دلیل رد را وارد کنید.");
      const fd = new FormData();
      fd.append("reason", reason);
      const res = await fetch(`/admin/api/requests/${rid}/reject`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) return showPopup(data.message || "خطا در رد درخواست");
      showPopup("رد شد");
      const row = rejectBtn.closest("tr");
      if (row) {
        const cells = row.querySelectorAll("td");
        if (cells[7]) {
          cells[7].setAttribute("data-raw-status", "تایید نشده");
          cells[7].innerHTML = statusBadge("تایید نشده");
        }
        if (cells[9]) cells[9].textContent = reason || "-";
        if (cells[10]) cells[10].innerHTML = renderResetAction(rid);
      }
      refreshLiveStats();
      refreshLiveFeed();
      return;
    }
    const fakeBtn = target.closest(".fake-btn");
    if (fakeBtn) {
      const rid = fakeBtn.dataset.requestId;
      const form = fakeBtn.closest("form");
      const reasonInput = form ? form.querySelector("textarea[name='reject_reason']") : null;
      const reason = (reasonInput ? reasonInput.value.trim() : "") || "فیش نامعتبر تشخیص داده شد.";
      const fd = new FormData();
      fd.append("reason", reason);
      const res = await fetch(`/admin/api/requests/${rid}/fake`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) return showPopup(data.message || "خطا در ثبت فیک");
      showPopup("به عنوان فیک علامت‌گذاری شد.");
      const row = fakeBtn.closest("tr");
      if (row) {
        const cells = row.querySelectorAll("td");
        if (cells[7]) {
          cells[7].setAttribute("data-raw-status", "تایید نشده | فیک");
          cells[7].innerHTML = statusBadge("تایید نشده | فیک");
        }
        if (cells[9]) cells[9].textContent = reason || "-";
        if (cells[10]) cells[10].innerHTML = renderResetAction(rid);
      }
      refreshLiveStats();
      refreshLiveFeed();
      return;
    }
    const reportBanBtn = target.closest(".report-ban-btn");
    if (reportBanBtn) {
      const fd = new FormData();
      fd.append("device_id", reportBanBtn.dataset.deviceId || "");
      const res = await fetch("/admin/api/device-ban", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) return showPopup(data.message || "خطا در بن");
      showPopup("کاربر گزارش‌دهنده بن شد");
      reportBanBtn.disabled = true;
      refreshLiveStats();
      return;
    }
    const receiptLink = target.closest(".receipt-open-link");
    if (receiptLink && receiptModal && receiptModalImage && receiptModalActions) {
      evt.preventDefault();
      const row = receiptLink.closest("tr");
      const rid = row?.dataset.requestId || "";
      receiptModalActions.dataset.requestId = rid;
      receiptModalActions.querySelector(".reject-btn")?.setAttribute("data-request-id", rid);
      receiptModalActions.querySelector(".fake-btn")?.setAttribute("data-request-id", rid);
      receiptModalActions.querySelectorAll("input[name='category_ids']").forEach((x) => { x.checked = false; });
      receiptModalImage.src = receiptLink.dataset.receiptUrl || receiptLink.getAttribute("href") || "";
      receiptModal.classList.remove("hidden");
      receiptModalOpen = true;
      const seenCell = row ? row.querySelector(".receipt-seen-cell") : null;
      if (seenCell) seenCell.innerHTML = '<span style="color:#22c55e">👁️</span>';
      return;
    }
  });

  setInterval(() => {
    const now = new Date();
    const t = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: true, timeZone: "Asia/Tehran" });
    const d = now.toLocaleDateString("en-US", { year: "numeric", month: "2-digit", day: "2-digit", timeZone: "Asia/Tehran" });
    setStat("server_now", t);
    setStat("server_day", d);
  }, 1000);

  function notifyAdmin(title, body) {
    if (!notificationsEnabled) return;
    if (!("Notification" in window)) return;
    if (Notification.permission === "granted") {
      new Notification(title, { body });
      return;
    }
    if (Notification.permission !== "denied") {
      Notification.requestPermission().then((permission) => {
        if (permission === "granted") {
          new Notification(title, { body });
        }
      });
    }
  }

  function showLiveToast(text) {
    if (!liveToast) return;
    liveToast.innerHTML = `<div class="modal-card">${text}</div>`;
    liveToast.classList.remove("hidden");
    setTimeout(() => liveToast.classList.add("hidden"), 3000);
  }

  function renderNotifToggle() {
    if (!notifToggleBtn) return;
    notifToggleBtn.textContent = notificationsEnabled ? "نوتیف: روشن" : "نوتیف: خاموش";
    notifToggleBtn.classList.toggle("btn-danger", notificationsEnabled);
  }

  if (notifToggleBtn) {
    renderNotifToggle();
    notifToggleBtn.addEventListener("click", async () => {
      if (!notificationsEnabled && "Notification" in window && Notification.permission !== "granted") {
        const perm = await Notification.requestPermission();
        if (perm !== "granted") {
          showPopup("اجازه نوتیف داده نشد.");
          return;
        }
      }
      notificationsEnabled = !notificationsEnabled;
      localStorage.setItem(NOTIF_KEY, notificationsEnabled ? "1" : "0");
      renderNotifToggle();
    });
  }

  if (settingsForm) {
    settingsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(settingsForm);
      const res = await fetch("/admin/api/settings", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در ذخیره تنظیمات");
        return;
      }
      showPopup("تنظیمات ذخیره شد");
      refreshLiveStats();
    });
  }

  if (categoryForm) {
    categoryForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(categoryForm);
      const res = await fetch("/admin/api/categories", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا");
        return;
      }
      showPopup("دسته ثبت شد");
      refreshLiveStats();
    });
  }

  if (backupAllBtn) {
    backupAllBtn.addEventListener("click", () => {
      window.location.href = "/admin/api/backup-all";
    });
  }

  if (userSearchForm && userSearchInput) {
    userSearchForm.addEventListener("submit", (evt) => {
      evt.preventDefault();
      const value = normalizeDigits((userSearchInput.value || "").trim());
      const match = value.match(/(\d+)/);
      if (!match) return showPopup("شماره کاربر را درست وارد کنید. مثال: کاربر 5");
      const userId = Number(match[1]);
      const found = highlightUserPurchases(userId);
      if (!found) showPopup("این کاربر خریدی نکرده.");
    });
  }

  document.querySelectorAll(".save-category-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.categoryId;
      const titleInput = document.querySelector(`.category-title-input[data-category-id='${id}']`);
      const paymentInput = document.querySelector(`.category-payment-input[data-category-id='${id}']`);
      const fd = new FormData();
      fd.append("title", titleInput ? titleInput.value : "");
      fd.append("payment_text", paymentInput ? paymentInput.value : "");
      const res = await fetch(`/admin/api/categories/${id}/update`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در ذخیره دسته");
        return;
      }
      showPopup("دسته بروزرسانی شد");
    });
  });

  document.querySelectorAll(".delete-category-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("این دسته و فایل‌های مربوط به آن حذف شود؟")) return;
      const id = btn.dataset.categoryId;
      const res = await fetch(`/admin/api/categories/${id}/delete`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در حذف دسته");
        return;
      }
      showPopup("دسته حذف شد");
      btn.closest("tr")?.remove();
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".delete-video-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("این فایل حذف شود؟")) return;
      const id = btn.dataset.videoId;
      const res = await fetch(`/admin/api/videos/${id}/delete`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در حذف فایل");
        return;
      }
      showPopup("فایل حذف شد");
      btn.closest("tr")?.remove();
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".delete-testimonial-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("این نظر حذف شود؟")) return;
      const id = btn.dataset.testimonialId;
      const res = await fetch(`/admin/api/testimonials/${id}/delete`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در حذف نظر");
        return;
      }
      showPopup("نظر حذف شد");
      btn.closest("tr")?.remove();
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".approve-testimonial-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.testimonialId;
      const res = await fetch(`/admin/api/testimonials/${id}/approve`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در تایید نظر");
        return;
      }
      showPopup("نظر تایید شد");
      const row = btn.closest("tr");
      if (row) {
        const cells = row.querySelectorAll("td");
        if (cells[3]) cells[3].textContent = "approved";
      }
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".reject-testimonial-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.testimonialId;
      const res = await fetch(`/admin/api/testimonials/${id}/reject`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در رد نظر");
        return;
      }
      showPopup("نظر رد شد");
      const row = btn.closest("tr");
      if (row) {
        const cells = row.querySelectorAll("td");
        if (cells[3]) cells[3].textContent = "rejected";
      }
      refreshLiveStats();
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
            showPopup(data.message || "خطا");
            return;
          }
          if (progressBar && progressText) {
            progressBar.style.width = "100%";
            progressText.textContent = "100%";
          }
          showPopup("فایل ثبت شد");
          refreshLiveStats();
        } catch (_err) {
          showPopup("خطا در پاسخ سرور");
        }
      };

      xhr.onerror = () => {
        showPopup("خطا در آپلود فایل");
      };

      xhr.send(fd);
    });
  }

  function bindApproveForm(form) {
    if (!form || form.dataset.bound === "1") return;
    form.dataset.bound = "1";
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const rid = form.dataset.requestId;
      const fd = new FormData(form);
      const res = await fetch(`/admin/api/requests/${rid}/approve`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در تایید");
        return;
      }
      showPopup("تایید شد");
      if (receiptModal) { receiptModal.classList.add("hidden"); receiptModalOpen = false; }
      const row = form.closest("tr");
      if (row) {
        const cells = row.querySelectorAll("td");
        if (cells[7]) {
          cells[7].setAttribute("data-raw-status", "تایید شده");
          cells[7].innerHTML = statusBadge("تایید شده");
        }
        if (cells[9]) cells[9].textContent = "-";
        if (cells[10]) cells[10].innerHTML = renderResetAction(rid);
      }
      refreshLiveStats();
    });
  }
  document.querySelectorAll(".approve-form").forEach((form) => bindApproveForm(form));
  if (receiptModalActions) bindApproveForm(receiptModalActions);


  document.querySelectorAll(".ban-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.visitorId;
      const res = await fetch(`/admin/api/visitors/${id}/ban`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در بن");
        return;
      }
      showPopup("کاربر بن شد");
      btn.textContent = "بن شد";
      btn.disabled = true;
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".unban-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.visitorId;
      const res = await fetch(`/admin/api/visitors/${id}/unban`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در آن‌بن");
        return;
      }
      showPopup("کاربر آن‌بن شد");
      btn.textContent = "آن‌بن شد";
      btn.disabled = true;
      refreshLiveStats();
    });
  });

  document.querySelectorAll(".reply-form").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const rid = form.dataset.reportId;
      const fd = new FormData(form);
      const res = await fetch(`/admin/api/reports/${rid}/reply`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        showPopup(data.message || "خطا در ثبت پاسخ");
        return;
      }
      showPopup("پاسخ ثبت شد");
      const row = form.closest("tr");
      const thread = row ? row.querySelector(".ticket-thread") : null;
      const text = form.querySelector("textarea[name='reply_text']")?.value || "";
      if (thread) {
        const item = document.createElement("div");
        item.className = "ticket-msg ticket-admin";
        item.innerHTML = `<strong>ادمین</strong>: ${text}`;
        thread.appendChild(item);
      }
      refreshLiveStats();
      setTimeout(() => window.location.reload(), 350);
    });
  });
  const adminReadyToggle = document.getElementById("admin-ready-toggle");
  const adminReadySelect = document.getElementById("admin-ready-select");
  if (adminReadyToggle && adminReadySelect) {
    adminReadyToggle.addEventListener("click", () => adminReadySelect.classList.toggle("hidden"));
    adminReadySelect.addEventListener("change", () => {
      const ta = document.querySelector(".reply-form textarea[name='reply_text']");
      if (ta && adminReadySelect.value) ta.value = adminReadySelect.value;
    });
  }
  document.querySelectorAll(".delete-admin-msg-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const rid = btn.dataset.reportId;
      const msgId = btn.dataset.msgId;
      const res = await fetch(`/admin/api/reports/${rid}/messages/${msgId}/delete`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) return showPopup(data.message || "خطا در حذف پیام");
      window.location.reload();
    });
  });

  if (receiptModalClose && receiptModal) receiptModalClose.addEventListener("click", () => { receiptModal.classList.add("hidden"); receiptModalOpen = false; });
  if (receiptModal) receiptModal.addEventListener("click", (e) => { if (e.target === receiptModal) { receiptModal.classList.add("hidden"); receiptModalOpen = false; } });

  async function refreshLiveFeed() {
    if (!purchaseRowsBody && !reportRowsBody) return;
    try {
      const res = await fetch("/admin/api/live-feed");
      const data = await res.json();
      if (!res.ok || !data.ok) return;
      if (purchaseRowsBody && Array.isArray(data.purchases)) {
        if (receiptModalOpen) return;
        const activeEl = document.activeElement;
        const isEditingPurchase =
          !!activeEl &&
          purchaseRowsBody.contains(activeEl) &&
          activeEl instanceof HTMLElement &&
          (activeEl.tagName === "TEXTAREA" || activeEl.tagName === "INPUT");
        if (isEditingPurchase) return;
        purchaseRowsBody.innerHTML = data.purchases.map((r) => `
          <tr data-request-id="${r.id}" data-requested-category="${escapeHtml(r.requested_category)}" data-user-id="${escapeHtml(r.user_id)}">
            <td>کاربر ${r.user_id || "-"}</td>
            <td class="device-id">${escapeHtml(r.device_id)}</td>
            <td>${escapeHtml(r.requested_category)}</td>
            <td class="tiny-text">${escapeHtml(r.category_titles)}</td>
            <td>${escapeHtml(r.created_at_clock)}<br><span class="tiny-text">${escapeHtml(r.created_at_day)}</span></td>
            <td><a class="receipt-open-link" data-receipt-url="/admin/receipt/${encodeURI(r.receipt_path || "")}?rid=${encodeURIComponent(r.id || "")}" href="/admin/receipt/${encodeURI(r.receipt_path || "")}?rid=${encodeURIComponent(r.id || "")}">مشاهده</a></td>
            <td class="receipt-seen-cell">${r.receipt_seen ? '<span style="color:#22c55e">👁️</span>' : '<span style="color:#ef4444">🙈</span>'}</td>
            <td class="status-cell" data-raw-status="${escapeHtml(r.status_label)}">${statusBadge(r.status_label)}</td>
            <td>${escapeHtml(r.user_note || "-")}</td>
            <td>${escapeHtml(r.admin_note || "-")}</td>
            <td>${r.status === "pending" ? renderPendingActions(r.id, r.requested_category) : renderResetAction(r.id)}</td>
          </tr>
        `).join("");
        purchaseRowsBody.querySelectorAll(".approve-form").forEach((form) => bindApproveForm(form));
        applyStatusBadges();
      }
      if (reportRowsBody && Array.isArray(data.reports)) {
        reportRowsBody.innerHTML = data.reports.map((rp) => `
          <tr>
            <td>${escapeHtml(rp.reporter_name)}</td>
            <td class="device-id">${escapeHtml(rp.device_id)}</td>
            <td>${escapeHtml(rp.report_type)}</td>
            <td><div class="tiny-text">${escapeHtml(rp.last_sender)}: ${escapeHtml(rp.last_text)}</div><div class="tiny-text">${escapeHtml(rp.last_at_clock)}<br>${escapeHtml(rp.last_at_day)}</div></td>
            <td class="tiny-text">${escapeHtml(rp.category_titles)}</td>
            <td>${escapeHtml(rp.created_at_clock)}<br><span class="tiny-text">${escapeHtml(rp.created_at_day)}</span></td>
            <td><a class="btn small" href="/admin/reports/${rp.id}">باز کردن تیکت</a> <button class="btn small btn-danger report-ban-btn" data-device-id="${escapeHtml(rp.device_id)}" type="button">بن</button></td>
          </tr>
        `).join("");
      }
    } catch (_err) {}
  }

  if (statNodes.length > 0) {
    let primed = false;
    refreshLiveStats = async () => {
      try {
        const res = await fetch("/admin/api/live-stats");
        const data = await res.json();
        if (!res.ok || !data.ok) return;
        const stats = data.stats || {};
        Object.keys(stats).forEach((key) => {
          if (key === "latest_purchase_id" || key === "latest_report_id") return;
          setStat(key, stats[key]);
        });
        const latestPurchase = Number(stats.latest_purchase_id || 0);
        const latestReport = Number(stats.latest_report_id || 0);
        const latestTestimonial = Number(stats.latest_testimonial_id || 0);
        if (!primed) {
          lastPurchaseId = latestPurchase;
          lastReportId = latestReport;
          lastTestimonialId = latestTestimonial;
          primed = true;
          return;
        }
        const unseenPurchase = Math.max(0, latestPurchase - lastPurchaseId);
        const unseenReport = Math.max(0, latestReport - lastReportId);
        const unseenTestimonial = Math.max(0, latestTestimonial - lastTestimonialId);
        if (unseenPurchase > 0) {
          notifyAdmin("درخواست خرید جدید", `${unseenPurchase} خرید جدید ثبت شد.`);
          showLiveToast("🛒 خرید جدید ثبت شد");
          lastPurchaseId = latestPurchase;
        }
        if (unseenReport > 0) {
          notifyAdmin("ریپورت جدید", `${unseenReport} ریپورت جدید ثبت شد.`);
          showLiveToast("📩 ریپورت جدید ثبت شد");
          lastReportId = latestReport;
        }
        if (unseenTestimonial > 0) {
          notifyAdmin("نظر جدید", `${unseenTestimonial} نظر جدید ثبت شد.`);
          showLiveToast("💬 نظر جدید ثبت شد");
          lastTestimonialId = latestTestimonial;
        }
        if (unseenPurchase > 0 || unseenReport > 0 || unseenTestimonial > 0) {
          refreshLiveFeed();
        }
        if (onlineByPageBody && data.online_by_page) {
          const rows = Object.entries(data.online_by_page)
            .map(([page, count]) => `<tr><td>${page}</td><td>${count}</td></tr>`)
            .join("");
          onlineByPageBody.innerHTML = rows || "<tr><td colspan='2'>-</td></tr>";
        }
      } catch (_err) {
        // silent
      }
    };
    refreshLiveStats();
    refreshLiveFeed();
    applyStatusBadges();
    setInterval(refreshLiveStats, 700);
    setInterval(refreshLiveFeed, 900);
  }
})();
