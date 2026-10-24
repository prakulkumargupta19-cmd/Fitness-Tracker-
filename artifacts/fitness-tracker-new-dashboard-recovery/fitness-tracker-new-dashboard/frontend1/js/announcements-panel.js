(function (global) {
  "use strict";

  const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>'"]/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c])
    );

  function apiBase() {
    return (global.FITNESS_API_BASE || global.APP_CONFIG?.API_BASE || "").replace(/\/$/, "");
  }

  async function request(method, path, body, multipart) {
    const options = { method, credentials: "include", headers: {} };
    if (body !== undefined) {
      if (multipart) options.body = body;
      else {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
      }
    }
    const response = await fetch(apiBase() + path, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.success === false) {
      throw new Error(payload.message || "The request could not be completed.");
    }
    return payload.data !== undefined ? payload.data : payload;
  }

  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString(undefined, {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  }

  function renderList(items, canManage) {
    if (!items.length) {
      return `<div class="announcement-empty">No announcements have been shared yet.</div>`;
    }
    return items.map((item) => {
    const image = item.image_path
        ? `<img class="announcement-card-image" src="${apiBase()}/api/fit-track/announcements/${item.id}/image" alt="${escapeHtml(item.title)}" onerror="this.style.display='none'">`
        : "";
      const actions = canManage
        ? `<button type="button" class="announcement-delete-btn" data-delete-announcement="${item.id}"><i class="bi bi-trash"></i> Delete</button>`
        : "";
      return `<article class="announcement-card">${image}<div class="announcement-card-body"><div class="announcement-card-meta">${escapeHtml(formatDate(item.created_at))}</div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.message)}</p>${actions}</div></article>`;
    }).join("");
  }

  function setStatus(message, isError) {
    const status = document.getElementById("announcementStatus");
    if (!status) return;
    status.hidden = !message;
    status.textContent = message || "";
    status.classList.toggle("error", Boolean(isError));
  }

  async function loadAndRender(root, canManage) {
    const list = root.querySelector("[data-announcement-list]");
    if (!list) return;
    list.innerHTML = `<div class="announcement-empty">Loading announcements…</div>`;
    try {
      const items = await request("GET", "/api/fit-track/announcements");
      const rows = Array.isArray(items) ? items : [];
      list.innerHTML = renderList(rows, canManage);
      bindDelete(root, canManage);
    } catch (error) {
      list.innerHTML = `<div class="announcement-empty error">${escapeHtml(error.message || "Could not load announcements.")}</div>`;
    }
  }

  function bindDelete(root, canManage) {
    if (!canManage) return;
    root.querySelectorAll("[data-delete-announcement]").forEach((button) => {
      button.addEventListener("click", async () => {
        const id = button.dataset.deleteAnnouncement;
        if (!id) return;
        if (!global.confirm("Delete this announcement for everyone?")) return;
        button.disabled = true;
        try {
          await request("DELETE", `/api/fit-track/announcements/${id}`);
          await loadAndRender(root, canManage);
        } catch (error) {
          alert(error.message || "Could not delete announcement.");
          button.disabled = false;
        }
      });
    });
  }

  function bindComposer(root, canManage) {
    if (!canManage) return;
    const form = root.querySelector("#dashboardAnnouncementForm");
    if (!form) return;
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submit = form.querySelector('button[type="submit"]');
      if (submit) submit.disabled = true;
      setStatus("Publishing…", false);
      try {
        await request("POST", "/api/fit-track/announcements/upload", new FormData(form), true);
        form.reset();
        setStatus("Announcement published across all dashboards.", false);
        await loadAndRender(root, canManage);
      } catch (error) {
        setStatus(error.message || "Could not publish announcement.", true);
      } finally {
        if (submit) submit.disabled = false;
      }
    });
  }

  function mount(options = {}) {
    const root = typeof options.root === "string"
      ? document.querySelector(options.root)
      : options.root;
    if (!root) return;
    const canManage = Boolean(options.canManage);
    if (!root.querySelector("[data-announcement-list]")) {
      root.insertAdjacentHTML("beforeend", '<div class="announcement-feed" data-announcement-list></div>');
    }
    bindComposer(root, canManage);
    loadAndRender(root, canManage);
  }

  global.AnnouncementsPanel = { mount, loadAndRender, request };
})(window);
