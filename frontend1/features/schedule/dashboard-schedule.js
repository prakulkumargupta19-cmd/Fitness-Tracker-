(function (global) {
  "use strict";

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[character]));
  let currentRole = "student";
  const api = async (path, method = "GET", body) => {
    const base = (global.FITNESS_API_BASE || global.APP_CONFIG?.API_BASE || "").replace(/\/$/, "");
    const headers = { "X-Portal-Role": currentRole };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (method !== "GET") {
      const tokenResponse = await fetch(`${base}/api/csrf-token`, { credentials: "include", headers: { "X-Portal-Role": currentRole } });
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
    currentRole = role;
    root = typeof root === "string" ? document.querySelector(root) : root;
    if (!root || root.dataset.scheduleMounted) return;
    root.dataset.scheduleMounted = "true";

    let cursor = new Date();
    cursor.setDate(1);
    let selectedDate = null;
    let items = [];
    let pastSessions = [];
    const canManage = role === "admin";
    const canRequest = role === "coach";
    const panel = document.createElement("section");
    panel.className = "dashboard-schedule";
    panel.innerHTML = `
      <div class="schedule-heading">
        <div><span class="schedule-kicker">SHARED SCHEDULE</span><h2>Calendar &amp; upcoming sessions</h2></div>
        ${canManage || canRequest ? `<button type="button" class="schedule-add-toggle" aria-expanded="false">${canManage ? "Add session" : "Request extra session"}</button>` : ""}
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
      <dialog class="schedule-clock-dialog" aria-label="Choose session time"><div class="schedule-clock-panel"><button type="button" class="schedule-clock-close" aria-label="Close">×</button><span class="schedule-clock-caption">SELECT TIME</span><div class="schedule-clock-display"><span data-clock-hour>08</span><b>:</b><span data-clock-minute>30</span><span data-clock-period>AM</span></div><div class="schedule-clock-controls"><label>Hour<select data-clock-hour-select></select></label><label>Minute<select data-clock-minute-select></select></label><div class="schedule-clock-periods"><button type="button" data-period="AM">AM</button><button type="button" data-period="PM">PM</button></div></div><button type="button" class="schedule-clock-confirm">Set time</button></div></dialog>
      ${canManage ? `<form class="schedule-form" hidden>
        <h3>Publish a session</h3>
        <div class="schedule-form-grid">
          <label>Session type<select name="session_type" required><option value="Assessment">Assessment</option><option value="Practice">Practice</option><option value="Training">Training</option></select></label>
          <label>Sport<select name="sport_id" required><option value="">Loading sports…</option></select></label>
          <label>Date<input name="session_date" type="date" required></label>
          <label>Start<div class="schedule-time-field"><div class="schedule-time-entry"><input name="start_hour" type="text" inputmode="numeric" maxlength="2" placeholder="HH" autocomplete="off" required aria-label="Start hour"><span>:</span><input name="start_minute" type="text" inputmode="numeric" maxlength="2" placeholder="MM" autocomplete="off" required aria-label="Start minute"></div><select name="start_period" aria-label="Start AM or PM"><option>AM</option><option>PM</option></select></div></label>
          <label>End<div class="schedule-time-field"><div class="schedule-time-entry"><input name="end_hour" type="text" inputmode="numeric" maxlength="2" placeholder="HH" autocomplete="off" required aria-label="End hour"><span>:</span><input name="end_minute" type="text" inputmode="numeric" maxlength="2" placeholder="MM" autocomplete="off" required aria-label="End minute"></div><select name="end_period" aria-label="End AM or PM"><option>AM</option><option>PM</option></select></div></label>
          <label>Venue<input name="venue" maxlength="255" placeholder="Training location" required></label>
          <label class="wide">Notes<textarea name="notes" maxlength="1000" rows="3" style="resize: none;" placeholder="Session instructions or details" required></textarea></label>
        </div>
        <button type="submit">Publish session</button>
        <p class="schedule-status" aria-live="polite"></p>
      </form>
      <section class="schedule-admin schedule-past-sessions" aria-labelledby="pastSessionsHeading">
        <div class="schedule-past-heading"><div><h3 id="pastSessionsHeading">Past sessions</h3><p>Review sessions before today in reverse chronological order.</p></div></div>
        <div class="schedule-past-filters">
          <label>Sport<select data-past-sport><option value="all">All sports</option></select></label>
          <label>Date<input type="date" data-past-date aria-label="Filter past sessions by date"></label>
          <button type="button" class="schedule-past-clear" data-past-clear>Clear date</button>
        </div>
        <div class="schedule-past-list" data-past-list aria-live="polite">Loading past sessions…</div>
      </section>
      <dialog class="schedule-past-dialog" aria-labelledby="schedulePastDialogTitle">
        <div class="schedule-past-dialog-body"></div>
      </dialog>` : ""}`;
    root.append(panel);

    const renderPastSessions = () => {
      if (!canManage) return;
      const sportFilter = panel.querySelector("[data-past-sport]").value;
      const dateFilter = panel.querySelector("[data-past-date]").value;
      const today = localDateKey(new Date());
      const shown = pastSessions
        .filter((session) => dateKey(session.date) < today)
        .filter((session) => sportFilter === "all" || String(session.sport_id) === sportFilter)
        .filter((session) => !dateFilter || dateKey(session.date) === dateFilter)
        .sort((a, b) => `${dateKey(b.date)} ${b.start_time || ""}`.localeCompare(`${dateKey(a.date)} ${a.start_time || ""}`));
      panel.querySelector("[data-past-list]").innerHTML = shown.map((session) => `
        <button type="button" class="schedule-past-session" data-past-session="${Number(session.id)}">
          <span class="schedule-past-session-main">
            <strong>${escapeHtml(session.title || "Training session")}</strong>
            <small>${escapeHtml(session.sport || "Sport")} · ${escapeHtml(formatDate(session.date))} · ${escapeHtml(session.time || "")}</small>
            <small>${escapeHtml(session.venue || "Venue TBA")}${session.coach ? ` · ${escapeHtml(session.coach)}` : ""}</small>
          </span>
          <span class="schedule-past-status">${escapeHtml(session.status || "Scheduled")}</span>
        </button>
      `).join("") || `<p class="schedule-muted">${dateFilter ? "No past sessions match this date and sport." : "No past sessions found."}</p>`;
    };

    const pastDialog = canManage ? panel.querySelector(".schedule-past-dialog") : null;
    const showPastDialog = (sessionId) => {
      const body = pastDialog.querySelector(".schedule-past-dialog-body");
      pastDialog.dataset.sessionId = sessionId;
      body.innerHTML = `<p class="schedule-muted">Loading attendance and assessment…</p>`;
      pastDialog.showModal();
      api(`/api/admin/fit-track/schedule/${sessionId}/attendance`).then((data) => {
        const session = data.session;
        const savedRecords = Object.fromEntries((data.records || []).map((record) => [
          record.student_id,
          String(record.status || "absent").toLowerCase()
        ]));
        const savedAssessments = Object.fromEntries((data.assessments || []).map((entry) => [
          entry.student_id,
          entry
        ]));
        const athletes = (data.students || []).map((student) => {
          const assessment = savedAssessments[student.id] || { values: {}, remarks: "" };
          const status = savedRecords[student.id] || "absent";
          return `<article class="schedule-past-athlete" data-student-id="${Number(student.id)}" data-current-status="${escapeHtml(status)}">
            <div class="schedule-past-athlete-header">
              <strong>${escapeHtml(student.name)}</strong>
              <div class="schedule-past-status-buttons">
                ${["present", "absent", "late", "excused"].map((choice) => `<button type="button" data-attendance-status="${choice}" class="${status === choice ? "active" : ""}" aria-pressed="${status === choice}">${choice[0].toUpperCase()}${choice.slice(1)}</button>`).join("")}
              </div>
            </div>
            ${data.fields?.length ? `<div class="schedule-past-assessment-fields">${data.fields.map((field) => `
              <label>${escapeHtml(field.field_label)} (0-${escapeHtml(field.max_score || 10)})
                <input type="number" min="0" max="${escapeHtml(field.max_score || 10)}" step="0.1" data-assessment-field="${escapeHtml(field.field_key)}" value="${escapeHtml(assessment.values?.[field.field_key] ?? "")}">
              </label>`).join("")}</div>
              <label class="schedule-past-remarks">Coach feedback (optional)<textarea rows="2" data-assessment-remarks>${escapeHtml(assessment.remarks || "")}</textarea></label>` : ""}
          </article>`;
        }).join("");
        const detail = data.attendance_taken
          ? `<p class="schedule-past-info">Coach attendance is recorded. Update the register and assessment fields below as needed.</p>
             <div class="schedule-past-athletes">${athletes || `<p class="schedule-muted">No active students are assigned to this sport.</p>`}</div>
             <div class="schedule-past-dialog-actions"><button type="button" class="schedule-past-close">Close</button><button type="button" class="schedule-past-save">Save changes</button></div>`
          : `<p class="schedule-past-info">${session.status === "Not Held" ? "This session is already marked as not held." : "No coach attendance was submitted for this session."}</p>
             <div class="schedule-past-dialog-actions"><button type="button" class="schedule-past-close">Close</button>${session.status === "Not Held" ? "" : '<button type="button" class="schedule-past-not-held">Mark as not held</button>'}</div>`;
        body.innerHTML = `<div class="schedule-past-dialog-heading"><div><span class="schedule-kicker">${escapeHtml(session.sport || "SPORT")}</span><h2 id="schedulePastDialogTitle">${escapeHtml(session.title || "Past session")}</h2><p>${escapeHtml(formatDate(session.session_date))}${session.start_time ? ` · ${escapeHtml(session.start_time)}` : ""}</p></div><button type="button" class="schedule-past-dialog-x" aria-label="Close">×</button></div>
          <p class="schedule-past-dialog-status" role="status" hidden></p>${detail}`;
      }).catch((error) => {
        body.innerHTML = `<p class="schedule-past-error">${escapeHtml(error.message)}</p><div class="schedule-past-dialog-actions"><button type="button" class="schedule-past-close">Close</button></div>`;
      });
    };

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
      renderPastSessions();
    };

    const reload = async () => {
      const status = panel.querySelector(".schedule-load-status");
      panel.querySelector(".schedule-items").textContent = "Loading schedule…";
      const [sessionsResult, eventsResult] = await Promise.allSettled([
        api("/api/fit-track/schedule"),
        api("/api/tournaments")
      ]);
      const errors = [];
      const sessions = sessionsResult.status === "fulfilled" && Array.isArray(sessionsResult.value) ? sessionsResult.value : [];
      const events = eventsResult.status === "fulfilled" && Array.isArray(eventsResult.value) ? eventsResult.value : [];
      if (sessionsResult.status === "rejected" || !Array.isArray(sessionsResult.value)) {
        errors.push(sessionsResult.reason?.message || "Sessions could not be loaded.");
      }
      if (eventsResult.status === "rejected" || !Array.isArray(eventsResult.value)) {
        errors.push(eventsResult.reason?.message || "Events could not be loaded.");
      }
      pastSessions = sessions.map((session) => ({
        id: session.id,
        sport_id: session.sport_id,
        date: session.session_date,
        start_time: session.start_time,
        time: `${session.start_time || ""}${session.end_time ? `–${session.end_time}` : ""}`,
        title: session.title || `${session.session_type || "Training"} session`,
        sport: session.sport,
        venue: session.venue,
        coach: session.coach,
        status: session.status || "Scheduled",
      })).filter((session) => session.date && session.status !== "Cancelled");
      items = sessions.map((session) => ({
        id: session.id,
        date: session.session_date,
        time: `${session.start_time || ""}${session.end_time ? `–${session.end_time}` : ""}`,
        title: session.title || `${session.session_type || "Training"} session`,
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

    if (canManage) {
      const sportFilter = panel.querySelector("[data-past-sport]");
      api("/api/fit-track/sports").then((sports) => {
        sportFilter.innerHTML = '<option value="all">All sports</option>' + sports.map((sport) =>
          `<option value="${Number(sport.id)}">${escapeHtml(sport.name)}</option>`
        ).join("");
      }).catch((error) => {
        const status = panel.querySelector(".schedule-load-status");
        status.hidden = false;
        status.textContent = `Sports could not be loaded for past-session filters: ${error.message}`;
      });
      sportFilter.addEventListener("change", renderPastSessions);
      panel.querySelector("[data-past-date]").addEventListener("change", renderPastSessions);
      panel.querySelector("[data-past-clear]").addEventListener("click", () => {
        panel.querySelector("[data-past-date]").value = "";
        renderPastSessions();
      });
      panel.querySelector("[data-past-list]").addEventListener("click", (event) => {
        const button = event.target.closest("[data-past-session]");
        if (button) showPastDialog(button.dataset.pastSession);
      });
      pastDialog.addEventListener("click", async (event) => {
        const target = event.target;
        if (target.closest(".schedule-past-close, .schedule-past-dialog-x")) {
          pastDialog.close();
          return;
        }
        const statusButton = target.closest("[data-attendance-status]");
        if (statusButton) {
          const athlete = statusButton.closest("[data-student-id]");
          athlete.dataset.currentStatus = statusButton.dataset.attendanceStatus;
          athlete.querySelectorAll("[data-attendance-status]").forEach((button) => {
            const active = button === statusButton;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", String(active));
          });
          return;
        }
        if (target.closest(".schedule-past-not-held")) {
          const dialogStatus = pastDialog.querySelector(".schedule-past-dialog-status");
          const currentSessionId = pastDialog.dataset.sessionId;
          if (!currentSessionId) return;
          dialogStatus.hidden = false;
          dialogStatus.textContent = "Updating session…";
          try {
            await api(`/api/admin/fit-track/schedule/${currentSessionId}/not-held`, "POST", {});
            pastDialog.close();
            await reload();
          } catch (error) {
            dialogStatus.textContent = error.message;
            dialogStatus.classList.add("error");
          }
          return;
        }
        if (target.closest(".schedule-past-save")) {
          const sessionId = pastDialog.dataset.sessionId;
          const dialogStatus = pastDialog.querySelector(".schedule-past-dialog-status");
          const athletes = [...pastDialog.querySelectorAll("[data-student-id]")];
          const records = athletes.map((athlete) => ({
            student_id: Number(athlete.dataset.studentId),
            status: athlete.dataset.currentStatus,
          }));
          const fields = [...pastDialog.querySelectorAll("[data-assessment-field]")];
          const assessments = fields.length
            ? athletes.map((athlete) => {
              const status = athlete.dataset.currentStatus;
              const values = {};
              athlete.querySelectorAll("[data-assessment-field]").forEach((input) => {
                if (input.value !== "") values[input.dataset.assessmentField] = Number(input.value);
              });
              return {
                student_id: Number(athlete.dataset.studentId),
                attendance_status: status,
                values: status === "present" || status === "late" ? values : {},
                remarks: status === "present" || status === "late"
                  ? athlete.querySelector("[data-assessment-remarks]")?.value || ""
                  : "",
              };
            })
            : undefined;
          if (assessments) {
            const incomplete = assessments.find((assessment) =>
              (assessment.attendance_status === "present" || assessment.attendance_status === "late")
              && fields.some((field) => !Object.prototype.hasOwnProperty.call(assessment.values, field.dataset.assessmentField))
            );
            if (incomplete) {
              dialogStatus.hidden = false;
              dialogStatus.textContent = "Complete every assessment score for students marked present or late.";
              dialogStatus.classList.add("error");
              return;
            }
          }
          const saveButton = target.closest(".schedule-past-save");
          saveButton.disabled = true;
          dialogStatus.hidden = false;
          dialogStatus.classList.remove("error");
          dialogStatus.textContent = "Saving attendance and assessment…";
          try {
            await api(`/api/admin/fit-track/schedule/${sessionId}/attendance`, "PUT", { records, assessments });
            pastDialog.close();
            await reload();
          } catch (error) {
            dialogStatus.textContent = error.message;
            dialogStatus.classList.add("error");
            saveButton.disabled = false;
          }
        }
      });
      pastDialog.addEventListener("close", () => {
        delete pastDialog.dataset.sessionId;
      });
    }

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
    toggle?.addEventListener("click", () => {
      if (canRequest) {
        const requestDialog = document.getElementById("extraSessionDialog");
        if (requestDialog && !requestDialog.open) requestDialog.showModal();
        return;
      }
      form.hidden = !form.hidden;
      toggle.setAttribute("aria-expanded", String(!form.hidden));
      if (!form.hidden) form.elements.session_date.focus();
    });

    if (form) {
      const dateInput = form.elements.session_date;
      dateInput.min = localDateKey(new Date());
      dateInput.value = dateInput.min;
      const sessionSportSelect = form.elements.sport_id;
      const publishButton = form.querySelector('button[type="submit"]');
      const formStatus = form.querySelector(".schedule-status");
      let scheduleSports = [];

      const loadSports = async () => {
        scheduleSports = await api("/api/fit-track/sports");
        sessionSportSelect.innerHTML = '<option value="">Choose sport</option>' + scheduleSports.map((sport) =>
          `<option value="${sport.id}">${escapeHtml(sport.name)}</option>`
        ).join("");
      };

      loadSports().catch((error) => {
        publishButton.disabled = true;
        formStatus.dataset.state = "error";
        formStatus.textContent = `Sports could not be loaded: ${error.message}`;
      });
      const clearFormStatus = () => {
        const message = form.querySelector(".schedule-status");
        message.textContent = "";
        delete message.dataset.state;
      };
      const updatePublishAvailability = () => {
        publishButton.disabled = !form.checkValidity();
      };
      form.addEventListener("input", () => {
        clearFormStatus();
        updatePublishAvailability();
      });
      form.addEventListener("change", () => {
        clearFormStatus();
        updatePublishAvailability();
      });
      
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        const button = form.querySelector('button[type="submit"]');
        const values = Object.fromEntries(new FormData(form));

        const toApiTime = (key) => {
          const rawHour = String(values[`${key}_hour`] || "");
          const rawMinute = String(values[`${key}_minute`] || "");
          const period = String(values[`${key}_period`] || "");
          if (!/^\d{1,2}$/.test(rawHour) || !/^\d{2}$/.test(rawMinute) || !["AM", "PM"].includes(period)) return null;
          let hour = Number(rawHour);
          const minute = Number(rawMinute);
          if (hour < 1 || hour > 12 || minute < 0 || minute > 59) return null;
          hour = (hour % 12) + (period === "PM" ? 12 : 0);
          return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
        };

        const startTime = toApiTime("start");
        const endTime = toApiTime("end");
        const message = form.querySelector(".schedule-status");
        if (!startTime || !endTime) {
          message.dataset.state = "error";
          message.textContent = "Enter a valid hour, minute, and AM/PM for both times.";
          return;
        }

        const body = {
          sport_id: Number(values.sport_id),
          session_date: values.session_date,
          start_time: startTime,
          end_time: endTime,
          venue: values.venue || "",
          notes: values.notes || "",
          status: "Scheduled",
          session_type: String(values.session_type || "").toLowerCase(),
        };

        button.disabled = true;
        message.dataset.state = "info";
        message.textContent = "Publishing session…";
        try {
          await api("/api/fit-track/schedule", "POST", body);
          const publishedSport = sessionSportSelect.value;
          form.reset();
          sessionSportSelect.value = publishedSport;
          dateInput.value = dateInput.min;
          message.dataset.state = "success";
          message.textContent = "Session published and added to the shared schedule.";
          await reload();
        } catch (error) {
          message.dataset.state = "error";
          message.textContent = error.message;
        } finally {
          updatePublishAvailability();
        }
      });
    }

    // Assessment-related functions (attached globally or scoped appropriately)
    window.loadAssessmentFields = async function(sportId) {
      try {
        const result = await api(`/api/sports/${sportId}/assessment-fields`);
        const fields = result.fields || result.data?.fields || [];
        const container = document.getElementById('assessment-fields-container');
        if (!container) return;
        
        if (fields.length === 0) {
          container.innerHTML = '<p class="text-muted">No active assessment fields for this sport.</p>';
          return;
        }
        
        let html = '';
        fields.forEach((field) => {
          html += `
            <div class="mb-2">
              <label>${escapeHtml(field.field_label)} <span class="text-danger">*</span></label>
              <input type="number" class="score-input" 
                     data-field-key="${escapeHtml(field.field_key)}"
                     min="0" max="${field.max_score || 10}"
                     step="0.1"
                     placeholder="Score (0-${field.max_score || 10})"
                     required>
            </div>
          `;
        });
        container.innerHTML = html;
      } catch (error) {
        console.error('Error loading assessment fields:', error);
        alert('Failed to load assessment fields: ' + error.message);
      }
    };

    reload();
  }

  global.DashboardSchedule = { mount };
})(window);