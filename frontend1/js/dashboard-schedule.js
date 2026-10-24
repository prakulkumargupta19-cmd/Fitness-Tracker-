(function (global) {
  "use strict";

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[character]));
  const api = async (path, method = "GET", body) => {
    const base = (global.FITNESS_API_BASE || global.APP_CONFIG?.API_BASE || "").replace(/\/$/, "");
    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (method !== "GET") {
      const tokenResponse = await fetch(`${base}/api/csrf-token`, { credentials: "include" });
      const tokenData = await tokenResponse.json().catch(() => ({}));
      if (!tokenResponse.ok || !tokenData.csrf_token) throw Error("Your session could not be verified. Refresh the page and try again.");
      headers["X-CSRFToken"] = tokenData.csrf_token;
    }
    const response = await fetch(base + path, {
      method,
      credentials: "include",
      cache: "no-store",
      headers,
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || result.success === false) throw Error(result.message || "The schedule request could not be completed.");
    return result.data ?? result;
  };
  const localDateKey = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  const dateKey = (value) => String(value || "").slice(0, 10);
  const formatDate = (value) => {
    const key = dateKey(value);
    const parsed = new Date(`${key}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? key : parsed.toLocaleDateString(undefined, { dateStyle: "medium" });
  };

  function mount({ root, role }) {
    root = typeof root === "string" ? document.querySelector(root) : root;
    if (!root || root.dataset.scheduleMounted) return;
    root.dataset.scheduleMounted = "true";

    let cursor = new Date();
    cursor.setDate(1);
    let selectedDate = null;
    let items = [];
    const canManage = role === "admin" || role === "coach";
    const panel = document.createElement("section");
    panel.className = "dashboard-schedule";
    panel.innerHTML = `
      <div class="schedule-heading">
        <div><span class="schedule-kicker">SHARED SCHEDULE</span><h2>Calendar &amp; upcoming sessions</h2></div>
        ${canManage ? '<button type="button" class="schedule-add-toggle" aria-expanded="false">Add session</button>' : ""}
      </div>
      <div class="schedule-layout">
        <div class="schedule-calendar">
          <div class="schedule-calendar-head">
            <button type="button" data-month="-1" aria-label="Previous month">‹</button>
            <strong data-month-label></strong>
            <button type="button" data-month="1" aria-label="Next month">›</button>
          </div>
          <div class="schedule-week">${["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => `<span>${day}</span>`).join("")}</div>
          <div class="schedule-days" aria-label="Schedule calendar"></div>
          <div class="schedule-legend"><span class="practice">Practice</span><span class="event">Event</span></div>
        </div>
        <div class="schedule-upcoming"><h3 data-items-heading>Upcoming</h3><div class="schedule-items" aria-live="polite">Loading schedule…</div></div>
      </div>
      <p class="schedule-load-status" aria-live="polite" hidden></p>
      ${canManage ? `
      <dialog class="schedule-programme-dialog" aria-labelledby="scheduleProgrammeSetupTitle">
      <section class="schedule-programme-setup">
        <div>
          <h3 id="scheduleProgrammeSetupTitle">Create a programme</h3>
          <p>Create a programme for one of the registered sports. It will then be available in this dropdown.</p>
        </div>
        <div class="schedule-programme-grid">
          <label>Programme name<input data-programme-name maxlength="120" placeholder="e.g. Cricket Training" required></label>
          <label>Sport<select data-programme-sport required><option value="">Loading sports…</option></select></label>
          <label>Coach <span class="schedule-optional">(optional)</span><select data-programme-coach><option value="">Unassigned</option></select></label>
        </div>
        <button type="button" data-create-programme>Create programme</button>
        <button type="button" class="schedule-programme-close" data-close-programme>Cancel</button>
        <p class="schedule-programme-status" aria-live="polite"></p>
      </section>
      </dialog>
      <form class="schedule-form" hidden>
        <h3>Publish a session</h3>
        <div class="schedule-form-grid">
          <label>Programme<select name="programme_id" required><option value="">Loading programmes…</option></select></label>
          <label>Date<input name="session_date" type="date" required></label>
          <label>Start<input name="start_time" type="time" required></label>
          <label>End<input name="end_time" type="time" required></label>
          <label>Venue<input name="venue" maxlength="255" placeholder="Training location"></label>
          <label class="wide">Notes<textarea name="notes" maxlength="1000" rows="3" placeholder="Session instructions or details"></textarea></label>
        </div>
        <button type="submit">Publish session</button>
        <p class="schedule-status" aria-live="polite"></p>
      </form>` : ""}`;
    root.append(panel);

    const render = () => {
      const year = cursor.getFullYear();
      const month = cursor.getMonth();
      const today = localDateKey(new Date());
      panel.querySelector("[data-month-label]").textContent = cursor.toLocaleDateString(undefined, { month: "long", year: "numeric" });
      const offset = (new Date(year, month, 1).getDay() + 6) % 7;
      const dayCount = new Date(year, month + 1, 0).getDate();
      const days = Array(offset).fill(null).concat(Array.from({ length: dayCount }, (_, index) => index + 1));
      while (days.length % 7) days.push(null);
      panel.querySelector(".schedule-days").innerHTML = days.map((day) => {
        if (!day) return '<span class="schedule-day empty" aria-hidden="true"></span>';
        const key = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        const found = items.filter((item) => dateKey(item.date) === key);
        const kinds = [...new Set(found.map((item) => item.kind))].map((kind) => `<b class="${kind}"></b>`).join("");
        const classes = ["schedule-day", key === today && "today", key === selectedDate && "selected"].filter(Boolean).join(" ");
        const label = `${formatDate(key)}${found.length ? `, ${found.length} scheduled item${found.length === 1 ? "" : "s"}` : ""}`;
        return `<button type="button" class="${classes}" data-day="${key}" aria-label="${escapeHtml(label)}" aria-pressed="${key === selectedDate}"><span>${day}</span><i aria-hidden="true">${kinds}</i></button>`;
      }).join("");

      const shownItems = selectedDate
        ? items.filter((item) => dateKey(item.date) === selectedDate)
        : items.filter((item) => dateKey(item.date) >= today).slice(0, 12);
      panel.querySelector("[data-items-heading]").textContent = selectedDate ? `Sessions on ${formatDate(selectedDate)}` : "Upcoming";
      panel.querySelector(".schedule-items").innerHTML = shownItems.map((item) => `
        <article class="schedule-item ${item.kind}${item.status === "Cancelled" ? " cancelled" : ""}">
          <div>
            <b>${escapeHtml(item.title || "Session")}</b>
            ${item.sport ? `<small>${escapeHtml(item.sport)}</small>` : ""}
            <small>${escapeHtml(formatDate(item.date))}${item.time ? ` · ${escapeHtml(item.time)}` : ""}</small>
            <small>${escapeHtml(item.venue || "Venue TBA")}${item.coach ? ` · ${escapeHtml(item.coach)}` : ""}</small>
            ${item.notes ? `<small>${escapeHtml(item.notes)}</small>` : ""}
          </div>
          <div class="schedule-item-side"><span>${escapeHtml(item.status || item.kind)}</span>
          ${canManage && item.kind === "practice" ? `<button type="button" class="schedule-session-action" data-session-status="${item.status === "Cancelled" ? "Scheduled" : "Cancelled"}" data-session-id="${Number(item.id)}">${item.status === "Cancelled" ? "Restore" : "Cancel"}</button>` : ""}</div>
        </article>`).join("") || `<p class="schedule-muted">${selectedDate ? "Nothing is scheduled for this date." : "No upcoming sessions or events."}</p>`;
    };

    const reload = async () => {
      const status = panel.querySelector(".schedule-load-status");
      panel.querySelector(".schedule-items").textContent = "Loading schedule…";
      const [sessionsResult, eventsResult] = await Promise.allSettled([
        api("/api/fit-track/schedule"),
        api("/api/tournaments")
      ]);
      const errors = [];
      const sessions = sessionsResult.status === "fulfilled" ? sessionsResult.value : (errors.push(sessionsResult.reason?.message || "Sessions could not be loaded."), []);
      const events = eventsResult.status === "fulfilled" ? eventsResult.value : (errors.push(eventsResult.reason?.message || "Events could not be loaded."), []);
      items = sessions.map((session) => ({
        id: session.id,
        date: session.session_date,
        time: `${session.start_time || ""}${session.end_time ? `–${session.end_time}` : ""}`,
        title: session.programme || "Training session",
        sport: session.sport,
        venue: session.venue,
        coach: session.coach,
        notes: session.notes,
        status: session.status || "Scheduled",
        kind: "practice"
      })).concat(events.map((event) => ({
        date: event.start_date,
        title: event.name,
        sport: event.sport,
        venue: event.venue,
        status: event.status || "Event",
        kind: "event"
      }))).filter((item) => item.date)
        .sort((first, second) => `${dateKey(first.date)} ${first.time || ""}`.localeCompare(`${dateKey(second.date)} ${second.time || ""}`));
      status.hidden = errors.length === 0;
      status.textContent = errors.length ? `Some schedule information could not be loaded: ${errors.join(" · ")}` : "";
      render();
    };

    panel.querySelectorAll("[data-month]").forEach((button) => button.addEventListener("click", () => {
      cursor.setMonth(cursor.getMonth() + Number(button.dataset.month));
      selectedDate = null;
      render();
    }));
    panel.querySelector(".schedule-days").addEventListener("click", (event) => {
      const button = event.target.closest("[data-day]");
      if (!button) return;
      selectedDate = selectedDate === button.dataset.day ? null : button.dataset.day;
      render();
    });
    panel.querySelector(".schedule-items").addEventListener("click", async (event) => {
      const button = event.target.closest("[data-session-status]");
      if (!button) return;
      const nextStatus = button.dataset.sessionStatus;
      if (!global.confirm(nextStatus === "Cancelled" ? "Cancel this scheduled session?" : "Restore this session to the schedule?")) return;
      button.disabled = true;
      try {
        await api(`/api/fit-track/schedule/${button.dataset.sessionId}`, "PATCH", { status: nextStatus });
        await reload();
      } catch (error) {
        button.disabled = false;
        const status = panel.querySelector(".schedule-load-status");
        status.hidden = false;
        status.textContent = error.message;
      }
    });

    const toggle = panel.querySelector(".schedule-add-toggle");
    const form = panel.querySelector(".schedule-form");
    const programmeDialog = panel.querySelector(".schedule-programme-dialog");
    toggle?.addEventListener("click", () => {
      form.hidden = !form.hidden;
      toggle.setAttribute("aria-expanded", String(!form.hidden));
      if (!form.hidden) form.elements.session_date.focus();
    });

    if (form) {
      const dateInput = form.elements.session_date;
      dateInput.min = localDateKey(new Date());
      dateInput.value = dateInput.min;
      const programmeSelect = form.elements.programme_id;
      const publishButton = form.querySelector('button[type="submit"]');
      const formStatus = form.querySelector(".schedule-status");
      const programmeName = panel.querySelector("[data-programme-name]");
      const sportSelect = panel.querySelector("[data-programme-sport]");
      const coachSelect = panel.querySelector("[data-programme-coach]");
      const createProgrammeButton = panel.querySelector("[data-create-programme]");
      const programmeSetupStatus = panel.querySelector(".schedule-programme-status");
      let programmeNameEdited = false;
      let currentProgrammes = [];
      let lastProgrammeSelection = "";
      let programmeSetupOptionsLoaded = false;

      const renderProgrammeOptions = (selectedId = "") => {
        const previousSelection = selectedId || (programmeSelect.value === "__create__" ? lastProgrammeSelection : programmeSelect.value);
        programmeSelect.innerHTML = '<option value="">Choose programme</option>' + currentProgrammes.map((programme) =>
          `<option value="${programme.id}">${escapeHtml(programme.name)} · ${escapeHtml(programme.sport || "Sport")}</option>`
        ).join("") + (role === "admin" ? '<option value="__create__">＋ Create a programme…</option>' : "");
        programmeSelect.disabled = !currentProgrammes.length && role !== "admin";
        publishButton.disabled = currentProgrammes.length === 0;
        if (previousSelection && currentProgrammes.some((programme) => String(programme.id) === String(previousSelection))) {
          programmeSelect.value = String(previousSelection);
          lastProgrammeSelection = String(previousSelection);
        }
      };

      const loadProgrammeSetupOptions = async () => {
        if (programmeSetupOptionsLoaded) return;
        const sports = await api("/api/fit-track/sports");
        sportSelect.innerHTML = '<option value="">Choose a sport</option>' + sports.map((sport) =>
          `<option value="${sport.id}">${escapeHtml(sport.name)}</option>`
        ).join("");
        if (!sports.length) {
          programmeSetupStatus.dataset.state = "error";
          programmeSetupStatus.textContent = "There are no active sports in the catalogue. Add a sport before creating a programme.";
          return;
        }
        const coachesResult = await api("/api/admin/coaches").catch(() => ({}));
        const coaches = (coachesResult.coaches || []).filter((coach) =>
          coach.is_active && ["approved", "active"].includes(String(coach.coach_status || "").toLowerCase())
        );
        coachSelect.innerHTML = '<option value="">Unassigned</option>' + coaches.map((coach) =>
          `<option value="${coach.id}">${escapeHtml(coach.full_name)}${coach.specialization ? ` · ${escapeHtml(coach.specialization)}` : ""}</option>`
        ).join("");
        programmeSetupStatus.textContent = "Choose a sport and create a programme. Assign a coach if you want it to appear in their schedule.";
        programmeSetupOptionsLoaded = true;
      };

      const loadProgrammes = async () => {
        currentProgrammes = await api("/api/fit-track/schedule/programmes");
        renderProgrammeOptions();
        if (currentProgrammes.length) {
          formStatus.textContent = "";
          delete formStatus.dataset.state;
          return;
        }

        formStatus.dataset.state = "info";
        if (role === "admin") {
          formStatus.textContent = "Choose “＋ Create a programme…” in the Programme dropdown to add the first programme.";
        } else {
          formStatus.textContent = "No active programmes are assigned to your account yet. Ask an admin to create or assign one before publishing a session.";
        }
      };

      sportSelect?.addEventListener("change", () => {
        if (!programmeNameEdited && sportSelect.value) {
          const sportName = sportSelect.options[sportSelect.selectedIndex]?.textContent || "";
          programmeName.value = `${sportName} Training`;
        }
      });
      programmeSelect.addEventListener("change", async () => {
        if (programmeSelect.value === "__create__") {
          programmeSelect.value = lastProgrammeSelection || "";
          formStatus.dataset.state = "info";
          try {
            await loadProgrammeSetupOptions();
            programmeDialog.showModal();
            programmeName.focus();
          } catch (error) {
            programmeSetupStatus.dataset.state = "error";
            programmeSetupStatus.textContent = error.message;
          }
          return;
        }
        lastProgrammeSelection = programmeSelect.value;
        publishButton.disabled = !lastProgrammeSelection;
      });
      programmeName?.addEventListener("input", () => { programmeNameEdited = true; });
      panel.querySelector("[data-close-programme]")?.addEventListener("click", () => programmeDialog.close());
      createProgrammeButton?.addEventListener("click", async () => {
        if (!sportSelect.value || !programmeName.value.trim()) {
          programmeSetupStatus.dataset.state = "error";
          programmeSetupStatus.textContent = "Enter a programme name and choose a sport.";
          return;
        }
        createProgrammeButton.disabled = true;
        programmeSetupStatus.dataset.state = "info";
        programmeSetupStatus.textContent = "Creating programme…";
        try {
          const created = await api("/api/fit-track/programmes", "POST", {
            name: programmeName.value.trim(),
            sport_id: Number(sportSelect.value),
            coach_id: coachSelect.value ? Number(coachSelect.value) : null
          });
          currentProgrammes = await api("/api/fit-track/schedule/programmes");
          renderProgrammeOptions(created.id);
          programmeDialog.close();
          programmeNameEdited = false;
          programmeName.value = "";
          sportSelect.value = "";
          coachSelect.value = "";
          formStatus.dataset.state = "success";
          formStatus.textContent = "Programme created. Complete the session details and publish.";
          programmeSetupStatus.textContent = "";
        } catch (error) {
          programmeSetupStatus.dataset.state = "error";
          programmeSetupStatus.textContent = error.message;
        } finally {
          createProgrammeButton.disabled = false;
        }
      });
      loadProgrammes().catch((error) => {
        programmeSelect.disabled = true;
        publishButton.disabled = true;
        formStatus.dataset.state = "error";
        formStatus.textContent = `Programmes could not be loaded: ${error.message}`;
      });
      form.addEventListener("input", () => {
        const message = form.querySelector(".schedule-status");
        message.textContent = "";
        delete message.dataset.state;
      });
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        const button = form.querySelector('button[type="submit"]');
        const values = Object.fromEntries(new FormData(form));
        const body = { ...values, programme_id: Number(values.programme_id) };
        const message = form.querySelector(".schedule-status");
        button.disabled = true;
        message.dataset.state = "info";
        message.textContent = "Publishing session…";
        try {
          await api("/api/fit-track/schedule", "POST", body);
          const publishedProgramme = programmeSelect.value;
          form.reset();
          programmeSelect.value = publishedProgramme;
          dateInput.value = dateInput.min;
          message.dataset.state = "success";
          message.textContent = "Session published and added to the shared schedule.";
          await reload();
        } catch (error) {
          message.dataset.state = "error";
          message.textContent = error.message;
        } finally {
          button.disabled = !programmeSelect.value || programmeSelect.value === "__create__";
        }
      });
    }

    reload();
  }

  global.DashboardSchedule = { mount };
})(window);
