(function () {
  "use strict";

  const storageKey = "fit-track-theme";
  const role = location.pathname.toLowerCase().includes("/student/") ? "student"
    : location.pathname.toLowerCase().includes("/coach/") ? "coach" : "admin";
  const topbar = document.querySelector(".topbar-right");
  if (!topbar) return;

  const controls = document.createElement("div");
  controls.className = "dashboard-chrome-controls";
  controls.innerHTML = `
    <button class="chrome-icon-button" type="button" data-chrome-theme aria-label="Switch to dark mode" title="Switch theme"><i class="bi bi-moon-stars-fill"></i></button>
    <div class="notification-wrap">
      <button class="chrome-icon-button notification-trigger" type="button" data-notification-toggle aria-label="Open announcements" aria-expanded="false" title="Announcements">
        <i class="bi bi-bell"></i><span class="notification-count" data-notification-count hidden></span>
      </button>
      <section class="notification-popover" data-notification-popover hidden aria-label="Announcements">
        <div class="notification-heading"><div><strong>Announcements</strong><span>Latest updates for your portal</span></div><span class="notification-live"><i></i> Live</span></div>
        <div class="notification-list" data-notification-list><div class="notification-loading">Loading announcements…</div></div>
        <button class="notification-view-all" type="button" data-notification-view-all>View all announcements <i class="bi bi-arrow-up-right"></i></button>
      </section>
    </div>`;
  if (role === "student") controls.querySelector("[data-chrome-theme]").remove();
  topbar.prepend(controls);

  const themeButton = role === "student" ? document.getElementById("themeButton") : controls.querySelector("[data-chrome-theme]");
  const applyTheme = (dark) => {
    document.body.classList.toggle("dark-mode", dark);
    const icon = themeButton?.querySelector("i");
    if (icon) icon.className = dark ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
    themeButton?.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    if (themeButton) themeButton.title = dark ? "Switch to light mode" : "Switch to dark mode";
    const settingsToggle = document.getElementById("darkModeToggle");
    if (settingsToggle) settingsToggle.checked = dark;
    localStorage.setItem(storageKey, dark ? "dark" : "light");
    if (role === "student") localStorage.setItem("studentTheme", dark ? "dark" : "light");
    if (typeof window.initCharts === "function") window.initCharts();
  };
  const savedTheme = localStorage.getItem(storageKey) || localStorage.getItem("studentTheme");
  applyTheme(savedTheme === "dark");
  if (role !== "student") themeButton.addEventListener("click", () => applyTheme(!document.body.classList.contains("dark-mode")));
  window.addEventListener("storage", (event) => {
    if (event.key === storageKey) applyTheme(event.newValue === "dark");
  });

  const popover = controls.querySelector("[data-notification-popover]");
  const toggle = controls.querySelector("[data-notification-toggle]");
  const list = controls.querySelector("[data-notification-list]");
  const count = controls.querySelector("[data-notification-count]");
  const safeText = (value) => String(value ?? "");
  const formatDate = (value) => {
    const date = new Date(value);
    return value && !Number.isNaN(date.getTime()) ? date.toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "Recently";
  };
  async function loadNotices() {
    list.innerHTML = '<div class="notification-loading"><span class="notification-spinner"></span>Checking for announcements…</div>';
    try {
      const rows = await window.AnnouncementsPanel.request("GET", "/api/fit-track/announcements");
      const items = Array.isArray(rows) ? rows : [];
      count.textContent = items.length > 99 ? "99+" : String(items.length);
      count.hidden = items.length === 0;
      if (!items.length) {
        list.innerHTML = '<div class="notification-empty"><i class="bi bi-megaphone"></i><strong>You’re all caught up</strong><span>New announcements will appear here.</span></div>';
        return;
      }
      list.replaceChildren(...items.slice(0, 8).map((item) => {
        const card = document.createElement("article");
        card.className = "notification-item";
        const dot = document.createElement("span"); dot.className = "notification-item-dot";
        const content = document.createElement("div"); content.className = "notification-item-copy";
        const title = document.createElement("strong"); title.textContent = safeText(item.title || "Announcement");
        const message = document.createElement("p"); message.textContent = safeText(item.message);
        const date = document.createElement("time"); date.textContent = formatDate(item.created_at);
        content.append(title, message, date); card.append(dot, content); return card;
      }));
    } catch (error) {
      list.replaceChildren();
      const message = document.createElement("p"); message.className = "notification-error";
      message.textContent = error.message || "Announcements could not be loaded.";
      const retry = document.createElement("button"); retry.className = "notification-retry"; retry.type = "button"; retry.textContent = "Try again";
      retry.addEventListener("click", loadNotices, { once: true }); list.append(message, retry);
      count.hidden = true;
    }
  }
  toggle.addEventListener("click", () => {
    const opening = popover.hidden;
    popover.hidden = !opening;
    toggle.setAttribute("aria-expanded", String(opening));
    if (opening) loadNotices();
  });
  document.addEventListener("click", (event) => {
    if (!controls.querySelector(".notification-wrap").contains(event.target)) {
      popover.hidden = true; toggle.setAttribute("aria-expanded", "false");
    }
  });
  controls.querySelector("[data-notification-view-all]").addEventListener("click", () => {
    popover.hidden = true; toggle.setAttribute("aria-expanded", "false");
    if (role === "student") document.querySelector('[data-section="announcements"]')?.click();
    else if (typeof window.showSectionByName === "function") window.showSectionByName("announcements");
    else document.querySelector('[onclick*="showSection(\'announcements\'"]')?.click();
  });
  loadNotices();
})();
