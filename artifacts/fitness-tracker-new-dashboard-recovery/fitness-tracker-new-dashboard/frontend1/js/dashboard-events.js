(function (global) {
  "use strict";
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const apiBase = () => (global.FITNESS_API_BASE || global.APP_CONFIG?.API_BASE || "").replace(/\/$/, "");
  async function request(method, path, body) {
    const options = { method, credentials: "include", headers: {} };
    if (body !== undefined) { options.headers["Content-Type"] = "application/json"; options.body = JSON.stringify(body); }
    const response = await fetch(apiBase() + path, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.success === false) throw new Error(payload.message || "Request failed.");
    return payload.data !== undefined ? payload.data : payload;
  }
  const formatDate = (date) => { const parsed = new Date(date); return Number.isNaN(parsed.getTime()) ? date : parsed.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); };
    function mount({ root, role }) {
    root = typeof root === "string" ? document.querySelector(root) : root;
    if (!root) return;
    const staff = role === "admin" || role === "coach";
    let events = [];
    if (!root.querySelector("[data-event-list]")) {
      root.insertAdjacentHTML("beforeend", '<div class="event-card-grid" data-event-list><div class="announcement-empty">Loading events…</div></div>');
    }
    if (!root.querySelector("[data-event-modal]")) {
      root.insertAdjacentHTML("beforeend", '<div class="event-modal" data-event-modal hidden><div class="event-modal-dialog" role="dialog" aria-modal="true" aria-labelledby="eventModalTitle"><button type="button" class="event-modal-close" aria-label="Close">×</button><div data-event-modal-content></div></div></div>');
    }
    const list = root.querySelector("[data-event-list]");
    const refresh = async () => {
      list.innerHTML = '<div class="announcement-empty">Loading events…</div>';
      try {
        events = await request("GET", "/api/dashboard/events");
        list.innerHTML = events.length ? events.map((e) => `<article class="announcement-card event-card"><div class="event-date-badge"><i class="bi bi-calendar-event"></i></div><div class="announcement-card-body"><div class="announcement-card-meta">${escapeHtml(formatDate(e.event_date))}${e.venue ? ` · ${escapeHtml(e.venue)}` : ""}</div><h3>${escapeHtml(e.title)}</h3><p>${escapeHtml(e.description)}</p>${staff ? `<p class="event-registration-count"><strong>${e.registration_count || 0}</strong> registered</p>${(e.registrants || []).length ? `<details class="event-registrants"><summary>View registrants</summary><div>${e.registrants.map((r) => `<p><strong>${escapeHtml(r.full_name)}</strong> · ${escapeHtml(r.email)} · ${escapeHtml(r.contact_number || "No phone")}</p>`).join("")}</div></details>` : ""}<button class="announcement-delete-btn" data-event-delete="${e.id}" type="button"><i class="bi bi-trash"></i> Delete event</button>` : `<div class="event-card-actions"><button class="announcement-primary-btn secondary" data-event-details="${e.id}" type="button">View details</button>${e.registered ? '<button type="button" class="announcement-primary-btn" disabled>Registered</button>' : `<button class="announcement-primary-btn" data-event-register="${e.id}" type="button">Register</button>`}</div>`}</div></article>`).join("") : '<div class="announcement-empty">No events have been added yet.</div>';
        bind();
      } catch (error) { list.innerHTML = `<div class="announcement-empty error">${escapeHtml(error.message)}</div>`; }
    };
    const modal = root.querySelector("[data-event-modal]");
    const hideModal = () => { modal.hidden = true; };
    root.querySelector(".event-modal-close")?.addEventListener("click", hideModal);
    modal.addEventListener("click", (event) => { if (event.target === modal) hideModal(); });
    const showDetails = (e) => { modal.querySelector("[data-event-modal-content]").innerHTML = `<div class="announcement-card-meta">${escapeHtml(formatDate(e.event_date))}${e.venue ? ` · ${escapeHtml(e.venue)}` : ""}</div><h2 id="eventModalTitle">${escapeHtml(e.title)}</h2><p>${escapeHtml(e.description)}</p>`; modal.hidden = false; };
    function bind() {
      root.querySelectorAll("[data-event-details]").forEach((b) => b.addEventListener("click", () => { const e = events.find((x) => String(x.id) === b.dataset.eventDetails); if (e) showDetails(e); }));
      root.querySelectorAll("[data-event-delete]").forEach((b) => b.addEventListener("click", async () => { if (!global.confirm("Delete this event for everyone?")) return; try { await request("DELETE", `/api/dashboard/events/${b.dataset.eventDelete}`); await refresh(); } catch (e) { global.alert(e.message); } }));
      root.querySelectorAll("[data-event-register]").forEach((b) => b.addEventListener("click", () => {
        const e = events.find((x) => String(x.id) === b.dataset.eventRegister);
        modal.querySelector("[data-event-modal-content]").innerHTML = `<div class="announcement-card-meta">${escapeHtml(formatDate(e.event_date))}</div><h2 id="eventModalTitle">Register: ${escapeHtml(e.title)}</h2><p>${escapeHtml(e.description)}</p><form class="announcement-form" id="eventRegistrationForm"><label>Full name<input name="full_name" required maxlength="150" autocomplete="name"></label><label>Email<input name="email" type="email" required maxlength="150" autocomplete="email"></label><label class="full">Contact number<input name="contact_number" type="tel" required maxlength="30" autocomplete="tel"></label><div class="full"><button class="announcement-primary-btn" type="submit">Submit registration</button></div></form><div class="announcement-status" data-registration-status hidden></div>`;
        modal.hidden = false;
        modal.querySelector("#eventRegistrationForm").addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; const button = form.querySelector("button[type=submit]"); button.disabled = true; try { await request("POST", `/api/dashboard/events/${e.id}/register`, Object.fromEntries(new FormData(form))); hideModal(); await refresh(); } catch (err) { const status = modal.querySelector("[data-registration-status]"); status.hidden = false; status.classList.add("error"); status.textContent = err.message; button.disabled = false; } });
      }));
    }
    const form = root.querySelector("#dashboardEventForm");
    if (form) form.addEventListener("submit", async (event) => { event.preventDefault(); const submit = form.querySelector("button[type=submit]"); submit.disabled = true; try { await request("POST", "/api/dashboard/events", Object.fromEntries(new FormData(form))); form.reset(); await refresh(); } catch (error) { const status = root.querySelector("#eventStatus"); status.hidden = false; status.classList.add("error"); status.textContent = error.message; } finally { submit.disabled = false; } });
    refresh();
  }
  global.DashboardEvents = { mount };
})(window);