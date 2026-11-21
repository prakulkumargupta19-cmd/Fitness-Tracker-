(function (global) {
  "use strict";
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safeExternalUrl = (value) => {
    try {
      const url = new URL(String(value || ""));
      return url.protocol === "https:" || url.protocol === "http:" ? url.href : "";
    } catch (_) { return ""; }
  };
  const apiBase = () => (global.FITNESS_API_BASE || global.APP_CONFIG?.API_BASE || "").replace(/\/$/, "");
  async function request(method, path, body) {
    const options = { method, credentials: "include", cache: "no-store", headers: {} };
    if (method !== "GET") {
      const tokenResponse = await fetch(`${apiBase()}/api/csrf-token`, { credentials: "include", cache: "no-store" });
      const tokenData = await tokenResponse.json().catch(() => ({}));
      if (!tokenResponse.ok || !tokenData.csrf_token) throw new Error("Your session could not be verified. Refresh the page and try again.");
      options.headers["X-CSRFToken"] = tokenData.csrf_token;
    }
    if (body !== undefined) { options.headers["Content-Type"] = "application/json"; options.body = JSON.stringify(body); }
    const controller = new AbortController();
    const timeout = global.setTimeout(() => controller.abort(), 15000);
    let response;
    try {
      response = await fetch(apiBase() + path, { ...options, signal: controller.signal });
    } catch (error) {
      if (error.name === "AbortError") throw new Error("The events service timed out. Please try again.");
      throw new Error("Could not connect to the events service. Check that the server is running and try again.");
    } finally {
      global.clearTimeout(timeout);
    }
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.success === false) throw new Error(payload.message || "Request failed.");
    return payload.data !== undefined ? payload.data : payload;
  }
  const formatDate = (value) => {
    if (!value) return "Date to be announced";
    const parsed = new Date(`${String(value).slice(0, 10)}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString(undefined, { dateStyle: "medium" });
  };
  const localDateKey = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  const sportKey = (value) => String(value ?? "").trim().toLocaleLowerCase();
  function uniqueSports(sports) {
    const unique = new Map();
    (Array.isArray(sports) ? sports : []).forEach((sport) => {
      const key = sportKey(sport?.name);
      if (!key) return;
      if (!unique.has(key)) unique.set(key, { ...sport, student_count: Number(sport.student_count) || 0 });
      else unique.get(key).student_count = Math.max(unique.get(key).student_count, Number(sport.student_count) || 0);
    });
    return [...unique.values()].sort((a, b) => String(a.name).localeCompare(String(b.name)));
  }
  function mount({ root, role }) {
    root = typeof root === "string" ? document.querySelector(root) : root;
    if (!root) return;
    const isAdmin = role === "admin";
    const isStudent = role === "student";
    const composer = root.querySelector(".announcement-composer");
    if (composer && isStudent) composer.hidden = true;
    if (root.dataset.eventsMounted === "true") return;
    root.dataset.eventsMounted = "true";
    let list = root.querySelector("[data-event-list]");
    if (!list) {
      list = document.createElement("div");
      list.className = "event-card-grid";
      list.dataset.eventList = "";
      list.innerHTML = '<div class="announcement-empty">Loading events…</div>';
      root.append(list);
    }
    let events = [];
    let selectedDate = "";
    let editingEventId = null;
    const calendarCursor = new Date();
    calendarCursor.setDate(1);
    const calendar = document.createElement("section");
    calendar.className = "event-calendar";
    calendar.setAttribute("aria-label", "Event calendar");
    calendar.innerHTML = `<div class="event-calendar-heading"><button type="button" data-calendar-month="-1" aria-label="Previous month">‹</button><h2 data-calendar-label></h2><button type="button" data-calendar-month="1" aria-label="Next month">›</button></div><div class="event-calendar-week">${["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => `<span>${day}</span>`).join("")}</div><div class="event-calendar-days" data-calendar-days></div><div class="event-calendar-footer"><span><i></i> Event</span><div class="event-calendar-actions"><button type="button" data-calendar-clear>Show all events</button></div></div>`;
    root.insertBefore(calendar, composer || list);
    const sportFilter = root.querySelector("[data-event-sport-filter], [data-coach-event-sport-filter]");
    const createDetails = root.querySelector("[data-event-create]");
    const visibleEvents = () => {
      if (sportFilter && sportFilter.value !== "all")
        return events.filter((item) => !item.sport_id || sportKey(item.sport) === sportFilter.value);
      return events;
    };
    const renderCalendar = () => {
      const year = calendarCursor.getFullYear();
      const month = calendarCursor.getMonth();
      calendar.querySelector("[data-calendar-label]").textContent = calendarCursor.toLocaleDateString(undefined, { month: "long", year: "numeric" });
      const offset = (new Date(year, month, 1).getDay() + 6) % 7;
      const count = new Date(year, month + 1, 0).getDate();
      const days = Array(offset).fill(null).concat(Array.from({ length: count }, (_, index) => index + 1));
      while (days.length % 7) days.push(null);
      const monthEvents = visibleEvents();
      calendar.querySelector("[data-calendar-days]").innerHTML = days.map((day) => {
        if (!day) return '<span class="event-calendar-day empty" aria-hidden="true"></span>';
        const key = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        const found = monthEvents.filter((item) => {
          const start = String(item.start_date || "").slice(0, 10);
          const end = String(item.end_date || item.start_date || "").slice(0, 10);
          return start && key >= start && key <= end;
        });
        const classes = ["event-calendar-day", found.length && "has-events", key === selectedDate && "selected"].filter(Boolean).join(" ");
        return `<button type="button" class="${classes}" data-calendar-day="${key}" aria-pressed="${key === selectedDate}" aria-label="${escapeHtml(formatDate(key))}${found.length ? `, ${found.length} event${found.length === 1 ? "" : "s"}` : ""}"><span>${day}</span>${found.length ? `<i>${found.length}</i>` : ""}</button>`;
      }).join("");
      calendar.querySelector("[data-calendar-clear]").hidden = !selectedDate;
    };
    const renderEvents = () => {
      renderCalendar();
      const shownEvents = visibleEvents().filter((item) => !selectedDate
        || (String(item.start_date || "").slice(0, 10) <= selectedDate
          && String(item.end_date || item.start_date || "").slice(0, 10) >= selectedDate));
      const emptyMessage = "No events have been added yet.";
      list.innerHTML = shownEvents.length ? shownEvents.map((e) => {
        const eventActions = isAdmin
          ? `<div class="event-admin-actions"><button type="button" data-event-edit="${escapeHtml(e.id)}"><i class="bi bi-pencil-square" aria-hidden="true"></i> Edit</button><button type="button" class="event-delete-button" data-event-delete="${escapeHtml(e.id)}"><i class="bi bi-trash3" aria-hidden="true"></i> Delete</button></div>`
          : "";
        const registrationAction = isStudent
          ? (e.registered ? '<button type="button" class="announcement-primary-btn" disabled>Registered</button>'
            : e.registration_open === false ? '<button type="button" class="announcement-primary-btn" disabled>Registration closed</button>'
              : safeExternalUrl(e.registration_url)
                ? `<a class="announcement-primary-btn event-registration-link" href="${escapeHtml(safeExternalUrl(e.registration_url))}" target="_blank" rel="noopener noreferrer" aria-label="Register for ${escapeHtml(e.name)} using the event registration form"><i class="bi bi-box-arrow-up-right" aria-hidden="true"></i> Register</a>`
                : '<button type="button" class="announcement-primary-btn event-registration-unavailable" disabled title="The administrator has not added an external registration link yet.">Registration link unavailable</button>')
          : "";
        return `<article class="announcement-card event-card"><div class="event-date-badge"><i class="bi bi-calendar-event"></i></div><div class="announcement-card-body"><div class="announcement-card-meta">${escapeHtml(formatDate(e.start_date))}${e.end_date && e.end_date !== e.start_date ? ` – ${escapeHtml(formatDate(e.end_date))}` : ""}${e.venue ? ` · ${escapeHtml(e.venue)}` : ""}</div><h3>${escapeHtml(e.name)}</h3><p>${escapeHtml(e.description || "")}</p><p>${escapeHtml(e.sport || "")}</p>${!isStudent ? `<p class="event-registration-count"><strong>${Number(e.registration_count) || 0}</strong> registered</p>` : ""}${registrationAction}${eventActions}</div></article>`;
      }).join("") : `<div class="announcement-empty">${escapeHtml(selectedDate ? `No events on ${formatDate(selectedDate)}.` : emptyMessage)}</div>`;
      bind();
    };
    const refresh = async () => {
      list.innerHTML = '<div class="announcement-empty">Loading events…</div>';
      try {
        const result = await request("GET", "/api/tournaments");
        events = Array.isArray(result) ? result : Array.isArray(result?.tournaments) ? result.tournaments : Array.isArray(result?.events) ? result.events : [];
        renderEvents();
      } catch (error) { list.innerHTML = `<div class="announcement-empty error">${escapeHtml(error.message)}</div>`; }
    };
    calendar.addEventListener("click", (event) => {
      const monthButton = event.target.closest("[data-calendar-month]");
      if (monthButton) {
        calendarCursor.setMonth(calendarCursor.getMonth() + Number(monthButton.dataset.calendarMonth));
        selectedDate = "";
        renderEvents();
        return;
      }
      const dayButton = event.target.closest("[data-calendar-day]");
      if (dayButton) {
        selectedDate = selectedDate === dayButton.dataset.calendarDay ? "" : dayButton.dataset.calendarDay;
        const dateInput = root.querySelector("#dashboardEventForm")?.elements.event_date;
        if (selectedDate && dateInput) dateInput.value = selectedDate;
        renderEvents();
      }
    });
    calendar.querySelector("[data-calendar-clear]").addEventListener("click", () => { selectedDate = ""; renderEvents(); });
    function bind() {
      root.querySelectorAll("[data-event-edit]").forEach((button) => button.addEventListener("click", () => {
        const item = events.find((event) => String(event.id) === button.dataset.eventEdit);
        if (!item || !form) return;
        if (form.dataset.eventHandlerReady !== "true") {
          const status = root.querySelector("#eventStatus");
          status.hidden = false;
          status.classList.remove("error");
          status.textContent = "The event form is still loading. Please try again in a moment.";
          return;
        }
        editingEventId = String(item.id);
        form.elements.title.value = item.name || "";
        form.elements.sport_id.value = item.sport_id == null ? "all" : String(item.sport_id);
        form.elements.event_date.value = String(item.start_date || "").slice(0, 10);
        form.elements.end_date.value = String(item.end_date || "").slice(0, 10);
        form.elements.venue.value = item.venue || "";
        form.elements.registration_url.value = item.registration_url || "";
        form.elements.description.value = item.description || "";
        if (createDetails) createDetails.open = true;
        const submit = form.querySelector("button[type=submit]");
        if (submit) submit.innerHTML = '<i class="bi bi-check2-circle"></i> Save changes';
        const cancel = form.querySelector("[data-event-cancel-edit]");
        if (cancel) cancel.hidden = false;
        const status = root.querySelector("#eventStatus");
        status.hidden = true;
        form.scrollIntoView({ behavior: "smooth", block: "center" });
        form.elements.title.focus({ preventScroll: true });
      }));
      root.querySelectorAll("[data-event-delete]").forEach((button) => button.addEventListener("click", async () => {
        const item = events.find((event) => String(event.id) === button.dataset.eventDelete);
        if (!item || !global.confirm(`Delete “${item.name}”? This also deletes its registrations, fixtures, and related event records.`)) return;
        button.disabled = true;
        try {
          await request("DELETE", `/api/tournaments/${encodeURIComponent(item.id)}`);
          if (editingEventId === String(item.id)) resetEditForm();
          const status = root.querySelector("#eventStatus");
          status.hidden = false;
          status.classList.remove("error");
          status.textContent = "Event deleted.";
          await refresh();
        } catch (error) {
          button.disabled = false;
          global.alert(error.message || "The event could not be deleted.");
        }
      }));
      root.querySelectorAll("[data-event-register]").forEach((button) => button.addEventListener("click", async () => {
        button.disabled = true;
        try { await request("POST", `/api/tournaments/${button.dataset.eventRegister}/register`, {}); await refresh(); }
        catch (error) { button.disabled = false; global.alert(error.message); }
      }));
    }
    const form = root.querySelector("#dashboardEventForm");
    function resetEditForm() {
      editingEventId = null;
      form?.reset();
      const submit = form?.querySelector("button[type=submit]");
      if (submit) submit.innerHTML = '<i class="bi bi-calendar-plus"></i> Add';
      const cancel = form?.querySelector("[data-event-cancel-edit]");
      if (cancel) cancel.hidden = true;
    }
    form?.querySelector("[data-event-cancel-edit]")?.addEventListener("click", resetEditForm);
    if (form && isAdmin) {
      const sportSelect = form.elements.sport_id;
      const submitButton = form.querySelector("button[type=submit]");
      const sportIdsByName = new Map();
      form.dataset.eventHandlerReady = "false";
      sportSelect.disabled = true;
      submitButton.disabled = true;
      form.addEventListener("submit", (event) => {
        // Never allow the browser's default GET navigation while the API-backed
        // sport list and JSON submit handler are still initializing.
        event.preventDefault();
        if (form.dataset.eventHandlerReady !== "true") {
          const status = root.querySelector("#eventStatus");
          status.hidden = false;
          status.classList.remove("error");
          status.textContent = "Sports are still loading. Please wait a moment and try again.";
        }
      });
      Promise.all([
        request("GET", "/api/sports"),
        isAdmin ? request("GET", "/api/admin/event-sports").catch(() => ({ sports: [] })) : Promise.resolve({ sports: [] })
      ]).then(async ([catalogPayload, registrationPayload]) => {
        const asSports = (payload) => {
          if (Array.isArray(payload)) return payload;
          if (Array.isArray(payload?.sports)) return payload.sports;
          if (Array.isArray(payload?.data)) return payload.data;
          if (Array.isArray(payload?.data?.sports)) return payload.data.sports;
          return [];
        };
        let catalogSports = asSports(catalogPayload);
        if (!catalogSports.length && isAdmin) catalogSports = asSports(await request("GET", "/api/fit-track/sports"));
        catalogSports = uniqueSports(catalogSports);
        const registeredSports = uniqueSports(asSports(registrationPayload));
        const countsByName = new Map(registeredSports.map((sport) => [sportKey(sport.name), Number(sport.student_count) || 0]));
        if (!catalogSports.length) throw new Error("The sports list is empty. Refresh the page or check the sports catalog.");
        const selectedSportName = sportSelect.selectedOptions[0]?.textContent?.split(" (")[0] || "";
        catalogSports.forEach((sport) => sportIdsByName.set(String(sport.name).trim().toLowerCase(), Number(sport.id)));
        sportSelect.innerHTML = '<option value="">Choose a sport</option><option value="all">All students</option>' + catalogSports.map((sport) => {
          const count = countsByName.get(sportKey(sport.name)) || 0;
          return `<option value="${sport.id}">${escapeHtml(sport.name)} (${count} students)</option>`;
        }).join("");
        const matchedOption = [...sportSelect.options].find((option) => option.textContent.split(" (")[0].toLowerCase() === selectedSportName.toLowerCase());
        if (matchedOption) sportSelect.value = matchedOption.value;
        sportSelect.disabled = false;
        submitButton.disabled = false;
        form.dataset.eventHandlerReady = "true";
        const status = root.querySelector("#eventStatus");
        status.hidden = true;
        status.classList.remove("error");
        status.textContent = "";
      }).catch((error) => {
        sportSelect.innerHTML = '<option value="">Sports unavailable</option>';
        sportSelect.disabled = true;
        submitButton.disabled = true;
        const status = root.querySelector("#eventStatus");
        status.hidden = false;
        status.classList.add("error");
        status.textContent = `${error.message || "The sports list could not be loaded."} Refresh the page before publishing.`;
      });
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const submit = submitButton;
        const values = Object.fromEntries(new FormData(form));
        const allStudents = String(values.sport_id).trim().toLowerCase() === "all";
        const resolvedSportId = allStudents ? null : sportIdsByName.get(String(values.sport_id).trim().toLowerCase()) || Number(values.sport_id);
        if (!allStudents && (!Number.isInteger(resolvedSportId) || resolvedSportId <= 0)) {
          const status = root.querySelector("#eventStatus");
          status.hidden = false;
          status.classList.add("error");
          status.textContent = "The selected sport could not be matched to the sports catalog. Refresh the page and try again.";
          return;
        }
        if (values.end_date && values.end_date < values.event_date) {
          const status = root.querySelector("#eventStatus");
          status.hidden = false;
          status.classList.add("error");
          status.textContent = "The end date must be on or after the event date.";
          return;
        }
        const body = { name: values.title, sport_id: resolvedSportId, start_date: values.event_date, end_date: values.end_date || null, venue: values.venue, description: values.description, registration_url: values.registration_url.trim() || null };
        submit.disabled = true;
        try {
          await request(editingEventId ? "PUT" : "POST", editingEventId ? `/api/tournaments/${encodeURIComponent(editingEventId)}` : "/api/tournaments", body);
          const wasEditing = Boolean(editingEventId);
          resetEditForm();
          selectedDate = body.start_date;
          const eventDate = new Date(`${body.start_date}T00:00:00`);
          calendarCursor.setFullYear(eventDate.getFullYear(), eventDate.getMonth(), 1);
          if (createDetails) createDetails.open = false;
          const status = root.querySelector("#eventStatus");
          status.hidden = false;
          status.classList.remove("error");
          status.textContent = wasEditing ? "Event updated." : "Event added to the calendar.";
          await refresh();
        }
        catch (error) { const status = root.querySelector("#eventStatus"); status.hidden = false; status.classList.add("error"); status.textContent = error.message; }
        finally { submit.disabled = false; }
      });
    }
    if (sportFilter) {
      sportFilter.addEventListener("change", renderEvents);
      request("GET", isAdmin ? "/api/admin/event-sports" : "/api/coach/event-sports").then((payload) => {
        const sports = uniqueSports(payload.sports || []);
        sportFilter.innerHTML = '<option value="all">All events</option>' + sports.map((sport) => `<option value="${escapeHtml(sportKey(sport.name))}">${escapeHtml(sport.name)} (${Number(sport.student_count) || 0} students)</option>`).join("");
        if (!sports.length) sportFilter.disabled = true;
        renderEvents();
      }).catch(() => {
        sportFilter.disabled = true;
        sportFilter.innerHTML = '<option value="all">All events</option>';
        renderEvents();
      });
    }
    renderCalendar();
    refresh();
  }
  global.DashboardEvents = { mount };
})(window);
