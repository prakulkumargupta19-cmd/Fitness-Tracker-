(function () {
  "use strict";

  const root = document.getElementById("referenceApp");
  if (!root) return;

  const page = root.dataset.page || "hub";
  const apiBase = (window.FITNESS_API_BASE || window.APP_CONFIG?.API_BASE || "").replace(/\/$/, "");
  let currentUser = null;

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  }[char]));
  const role = () => currentUser?.role || "student";
  const isAdmin = () => role() === "admin";
  const isStaff = () => role() === "admin" || role() === "coach";
  const initials = (value) => String(value || "FT").split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();

  async function request(method, path, body, multipart = false) {
    const options = { method, credentials: "include", headers: {} };
    if (body !== undefined) {
      if (multipart) options.body = body;
      else {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
      }
    }
    const response = await fetch(apiBase + path, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.success === false) throw new Error(payload.message || "The request could not be completed.");
    return payload.data !== undefined ? payload.data : payload;
  }

  function formValues(form, fields) {
    return Object.fromEntries(fields.map((name) => [name, form.elements[name]?.value?.trim() || null]).filter(([, value]) => value !== null));
  }

  function showAlert(message) {
    const alert = document.getElementById("referenceAlert");
    if (!alert) return;
    alert.textContent = message;
    alert.classList.add("show");
  }

  function hideAlert() { document.getElementById("referenceAlert")?.classList.remove("show"); }

  function card(value, label, accent = "") {
    return `<article class="reference-card"><div class="reference-stat ${accent}">${escapeHtml(value)}</div><div class="reference-stat-label">${escapeHtml(label)}</div></article>`;
  }

  const nav = [
    ["hub", "grid-1x2-fill", "Overview", "fit-track-features.html"],
    ["profile", "person-badge-fill", "My Passport", "fit-track-profile.html"],
    ["coaching", "people-fill", "Programmes", "fit-track-coaching.html"],
    ["schedule", "calendar-check-fill", "Coaching Schedule", "fit-track-schedule.html"],
    ["events", "trophy-fill", "Events & Calendar", "fit-track-events.html"],
    ["matches", "activity", "Live Scores", "fit-track-matches.html"],
    ["sports", "dribbble", "Sports & Facilities", "fit-track-sports.html"],
    ["gallery", "images", "Event Gallery", "fit-track-gallery.html"],
    ["announcements", "megaphone-fill", "Announcements", "fit-track-announcements.html"],
    ["chat", "chat-dots-fill", "Chat", "fit-track-chat.html"],
    ["reports", "bar-chart-fill", "Reports & Analytics", "fit-track-reports.html"]
  ];

  function layout(title, subtitle, content) {
    root.innerHTML = `<div class="reference-shell fit-role-${escapeHtml(role())}">
      <aside class="reference-sidebar" id="referenceSidebar">
        <div class="reference-brand"><div class="reference-brand-mark">FT</div><div><strong>Fit <span>Track</span></strong><small>${escapeHtml(role().toUpperCase())} PORTAL</small></div></div>
        <div class="reference-nav-label">MAIN MENU</div>
        <nav class="reference-nav">${nav.map(([key, icon, label, href]) => `<a class="${page === key ? "active" : ""}" href="${href}"><i class="bi bi-${icon}"></i><span>${escapeHtml(label)}</span></a>`).join("")}</nav>
        <div class="reference-identity"><strong>${escapeHtml(currentUser?.full_name || currentUser?.email || "Account")}</strong><span>${escapeHtml(role().toUpperCase())} · Root account connected</span></div>
      </aside>
      <main class="reference-main">
        <header class="reference-topbar"><div class="reference-heading"><button class="reference-menu-button" id="menuButton" aria-label="Open navigation"><i class="bi bi-list"></i></button><div><h1>${escapeHtml(title)}</h1><p>${escapeHtml(subtitle)}</p></div></div><div class="reference-inline"><span class="reference-user">${escapeHtml(currentUser?.full_name || currentUser?.email || "Signed in")}</span><button class="reference-button secondary small" id="themeButton" type="button"><i class="bi bi-moon-stars"></i></button></div></header>
        <section class="reference-content"><div id="referenceAlert" class="reference-alert"></div>${content}</section>
      </main>
    </div>`;
    document.getElementById("menuButton")?.addEventListener("click", () => document.getElementById("referenceSidebar")?.classList.toggle("open"));
    document.getElementById("themeButton")?.addEventListener("click", () => {
      document.body.classList.toggle("dark-mode");
      localStorage.setItem("fit-track-theme", document.body.classList.contains("dark-mode") ? "dark" : "light");
    });
    if (localStorage.getItem("fit-track-theme") === "dark") document.body.classList.add("dark-mode");
  }

  function bindForm(selector, handler) {
    document.querySelector(selector)?.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideAlert();
      try { await handler(event.currentTarget); location.reload(); }
      catch (error) { showAlert(error.message); }
    });
  }

  function bindAction(selector, handler) {
    document.querySelectorAll(selector).forEach((element) => element.addEventListener("click", async (event) => {
      event.preventDefault();
      try { await handler(element, event); }
      catch (error) { showAlert(error.message); }
    }));
  }

  function openModal(title, body) {
    const existing = document.querySelector(".reference-modal-backdrop");
    if (existing) existing.remove();
    const backdrop = document.createElement("div");
    backdrop.className = "reference-modal-backdrop";
    backdrop.innerHTML = `<article class="reference-modal"><div class="reference-modal-header"><h2>${escapeHtml(title)}</h2><button class="reference-modal-close" aria-label="Close">&times;</button></div><div class="reference-modal-body">${body}</div></article>`;
    backdrop.addEventListener("click", (event) => { if (event.target === backdrop || event.target.closest(".reference-modal-close")) backdrop.remove(); });
    document.body.appendChild(backdrop);
    return backdrop;
  }

  async function renderHub() {
    const [stats, announcements] = await Promise.all([
      request("GET", "/api/fit-track/dashboard"),
      request("GET", "/api/fit-track/announcements")
    ]);
    layout("Fit-Track operations", "Your sports performance workspace, connected to the existing portal account.", `<div class="reference-toolbar"><div><h2>Sports operations hub</h2><p>Live data from your programmes, events, athletes and reports.</p></div></div><div class="reference-grid">${card(stats.sports, "Active sports")}${card(stats.programmes, "Active programmes")}${card(stats.tournaments, "Upcoming events")}${card(stats.live_matches, "Live matches")}</div><div class="reference-grid two" style="margin-top:18px"><article class="reference-card"><h2>Recent announcements</h2>${announcements.slice(0, 5).map((item) => `<p><strong>${escapeHtml(item.title)}</strong><br><span class="reference-muted">${escapeHtml(item.created_at || "")}</span><br>${escapeHtml(item.message)}</p>`).join("") || `<p class="reference-empty">No announcements have been published.</p>`}</article><article class="reference-card"><h2>Continue working</h2><p>Open a section to work with the live Fit-Track records available to your role.</p><div class="reference-actions"><a class="reference-button" href="fit-track-events.html">Open events</a><a class="reference-button secondary" href="fit-track-reports.html">View reports</a></div></article></div>`);
  }

  async function renderProfile() {
    const profileResponse = await request("GET", "/api/profile");
    const profile = profileResponse.profile || {};
    if (role() !== "student") {
      layout("My account", "Your existing authenticated portal account remains connected to Fit-Track.", `<article class="reference-card"><div class="reference-inline"><div class="reference-brand-mark">${escapeHtml(initials(currentUser?.full_name))}</div><div><h2>${escapeHtml(currentUser?.full_name || "Account")}</h2><span class="reference-muted">${escapeHtml(currentUser?.email || "")} · ${escapeHtml(role().toUpperCase())}</span></div></div><p>Fit-Track records available to this account are controlled by the existing role and assignment permissions.</p></article>`);
      return;
    }
    const [achievements, certificates] = await Promise.all([
      request("GET", `/api/fit-track/students/${currentUser.id}/achievements`),
      request("GET", `/api/fit-track/students/${currentUser.id}/certificates`)
    ]);
    layout("My Sports Passport", "Your personal profile, achievements and certificates.", `<div class="reference-grid two"><article class="reference-card"><div class="reference-inline"><div class="reference-brand-mark">${escapeHtml(initials(currentUser?.full_name))}</div><div><h2>${escapeHtml(currentUser?.full_name || "Student")}</h2><span class="reference-muted">${escapeHtml(currentUser?.email || "")}</span></div></div><form id="profileForm" class="reference-form"><label>Sports Passport ID<input value="${escapeHtml(profile.passport_id || "Generating on save")}" readonly></label><label>Student number<input name="student_number" value="${escapeHtml(profile.student_number || "")}"></label><label>Full name<input name="full_name" value="${escapeHtml(currentUser?.full_name || "")}"></label><label>Phone<input name="contact_number" value="${escapeHtml(currentUser?.contact_number || "")}"></label><label>Date of birth<input name="date_of_birth" type="date" value="${escapeHtml(profile.date_of_birth || "")}"></label><label>Emergency contact<input name="emergency_contact" value="${escapeHtml(profile.emergency_contact || "")}"></label><label>Department<input name="department" value="${escapeHtml(profile.department || "")}"></label><label>Semester<input name="semester" value="${escapeHtml(profile.semester || "")}"></label><label>Blood group<input name="blood_group" value="${escapeHtml(profile.blood_group || "")}"></label><label class="full">Bio<textarea name="bio">${escapeHtml(profile.bio || "")}</textarea></label><div class="full"><button class="reference-button">Save passport</button></div></form></article><div><article class="reference-card"><h2>Achievements</h2>${achievements.map((item) => `<p><strong>${escapeHtml(item.title)}</strong><br><span class="reference-muted">${escapeHtml(item.sport || "")} ${escapeHtml(item.level || "")} ${escapeHtml(item.achievement_year || "")}</span></p>`).join("") || `<p class="reference-empty">No achievements recorded yet.</p>`}</article><article class="reference-card" style="margin-top:18px"><h2>Certificates</h2>${certificates.map((item) => `<p><strong>${escapeHtml(item.title)}</strong><br><span class="reference-muted">${escapeHtml(item.issuer || "")} ${escapeHtml(item.certificate_no || "")}</span></p>`).join("") || `<p class="reference-empty">No certificates recorded yet.</p>`}</article></div></div>`);
    bindForm("#profileForm", (form) => request("PATCH", `/api/fit-track/students/${currentUser.id}`, formValues(form, ["full_name", "contact_number", "date_of_birth", "emergency_contact", "student_number", "semester", "department", "blood_group", "bio"])));
  }

  async function renderSports() {
    const [sports, media] = await Promise.all([request("GET", "/api/fit-track/sports"), request("GET", "/api/fit-track/facilities")]);
    const mediaBySport = media.reduce((map, item) => { (map[item.sport] ||= []).push(item); return map; }, {});
    layout("Sports & facilities", "The same sports catalogue and venue information used by the existing portals.", `${isAdmin() ? `<article class="reference-card" style="margin-bottom:18px"><h2>Add a sport</h2><form id="sportForm" class="reference-form"><label>Name<input name="name" required></label><label>Activity type<input name="activity_type"></label><label class="full">Venue<input name="venue"></label><div class="full"><button class="reference-button">Save sport</button></div></form></article>` : ""}<div class="reference-grid three">${sports.map((sport) => `<article class="reference-card"><div class="reference-inline"><h2>${escapeHtml(sport.name)}</h2><span class="reference-pill">${escapeHtml(sport.activity_type || "Activity")}</span></div><p>${escapeHtml(sport.venue || "Venue not set")}</p>${(mediaBySport[sport.name] || []).slice(0, 3).map((item) => `<img src="${apiBase}/api/fit-track/facility-media/${item.id}/download" alt="${escapeHtml(item.caption || sport.name)}" style="width:100%;height:110px;object-fit:cover;border-radius:9px;margin-top:8px" onerror="this.style.display='none'">`).join("")}${isAdmin() ? `<form class="facilityForm reference-form" data-sport-id="${sport.id}"><label class="full">Facility image<input name="file" type="file" accept="image/*"></label><label class="full">Caption<input name="caption"></label><div class="full"><button class="reference-button small">Upload facility image</button></div></form>` : ""}</article>`).join("") || `<article class="reference-card reference-empty">No sports are available.</article>`}</div>`);
    bindForm("#sportForm", (form) => request("POST", "/api/fit-track/sports", formValues(form, ["name", "activity_type", "venue"])));
    document.querySelectorAll(".facilityForm").forEach((form) => form.addEventListener("submit", async (event) => { event.preventDefault(); const payload = new FormData(form); payload.append("sport_id", form.dataset.sportId); try { await request("POST", `/api/fit-track/facilities/${form.dataset.sportId}/media`, payload, true); location.reload(); } catch (error) { showAlert(error.message); } }));
  }

  async function renderCoaching() {
    const [programmes, sports, assessments] = await Promise.all([request("GET", "/api/fit-track/programmes"), request("GET", "/api/fit-track/sports"), request("GET", "/api/fit-track/assessments/daily")]);
    const students = isStaff() ? await request("GET", "/api/fit-track/students") : [];
    layout("Programmes & athlete development", "Coaching programmes, assigned athletes and daily development records.", `${isStaff() ? `<div class="reference-grid two"><article class="reference-card"><h2>Create programme</h2><form id="programmeForm" class="reference-form"><label>Name<input name="name" required></label><label>Sport<select name="sport_id" required>${sports.map((sport) => `<option value="${sport.id}">${escapeHtml(sport.name)}</option>`).join("")}</select></label><label>Schedule<input name="schedule"></label><label>Venue<input name="venue"></label><div class="full"><button class="reference-button">Create programme</button></div></form></article><article class="reference-card"><h2>Bulk enrol athletes</h2><form id="bulkEnrollmentForm" class="reference-form"><label class="full">Programme<select name="programme_id" required>${programmes.map((item) => `<option value="${item.id}">${escapeHtml(item.name)} · ${escapeHtml(item.sport)}</option>`).join("")}</select></label><div class="full reference-checklist">${students.map((student) => `<label><input type="checkbox" name="student_ids" value="${student.id}"> ${escapeHtml(student.name)}</label>`).join("") || `<span class="reference-muted">No assigned athletes available.</span>`}</div><div class="full"><button class="reference-button">Enrol selected athletes</button></div></form></article></div>` : ""}<div class="reference-grid two" style="margin-top:18px"><article class="reference-card"><h2>Programmes</h2><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>Name</th><th>Sport</th><th>Coach</th><th>Athletes</th></tr></thead><tbody>${programmes.map((item) => `<tr><td><strong>${escapeHtml(item.name)}</strong><br><span class="reference-muted">${escapeHtml(item.schedule || "Schedule not set")}</span></td><td>${escapeHtml(item.sport)}</td><td>${escapeHtml(item.coach || "TBA")}</td><td>${escapeHtml(item.enrolment_count)}</td></tr>`).join("") || `<tr><td colspan="4" class="reference-empty">No programmes yet.</td></tr>`}</tbody></table></div></article><article class="reference-card"><h2>Daily assessments</h2><p>${escapeHtml(assessments.length)} record(s) are available to this account.</p><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>Athlete</th><th>Date</th><th>Overall</th><th>Remarks</th></tr></thead><tbody>${assessments.slice(0, 15).map((item) => `<tr><td>${escapeHtml(item.student_name)}</td><td>${escapeHtml(item.session_date)}</td><td>${escapeHtml(item.overall_performance || "—")}</td><td>${escapeHtml(item.remarks || "—")}</td></tr>`).join("") || `<tr><td colspan="4" class="reference-empty">No assessment records yet.</td></tr>`}</tbody></table></div></article></div>`);
    bindForm("#programmeForm", (form) => request("POST", "/api/fit-track/programmes", formValues(form, ["name", "sport_id", "schedule", "venue"])));
    document.getElementById("bulkEnrollmentForm")?.addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; const payload = { programme_id: form.elements.programme_id.value, student_ids: [...form.querySelectorAll("input[name=student_ids]:checked")].map((input) => input.value) }; try { await request("POST", "/api/fit-track/enrollments/bulk", payload); location.reload(); } catch (error) { showAlert(error.message); } });
  }

  async function renderSchedule() {
    const month = new Date().toISOString().slice(0, 7);
    const selectedMonth = new URLSearchParams(window.location.search).get("month") || month;
    const sessions = await request("GET", `/api/fit-track/schedule?month=${encodeURIComponent(selectedMonth)}`);
    const programmes = await request("GET", "/api/fit-track/programmes");
    layout("Coaching schedule", "Dated sessions, timings, venues and coach notes.", `${isStaff() ? `<div class="reference-grid two"><article class="reference-card"><h2>Publish a session</h2><form id="scheduleForm" class="reference-form"><label>Programme<select name="programme_id" required>${programmes.map((item) => `<option value="${item.id}">${escapeHtml(item.name)} · ${escapeHtml(item.sport)}</option>`).join("")}</select></label><label>Date<input name="session_date" type="date" required></label><label>Start<input name="start_time" type="time" required></label><label>End<input name="end_time" type="time" required></label><label>Venue<input name="venue"></label><label>Status<select name="status"><option>Scheduled</option><option>Rescheduled</option><option>Cancelled</option><option>Completed</option></select></label><label class="full">Notes<textarea name="notes"></textarea></label><div class="full"><button class="reference-button">Publish session</button></div></form></article><article class="reference-card"><h2>Filter schedule</h2><form id="monthForm" class="reference-form"><label>Month<input name="month" type="month" value="${escapeHtml(selectedMonth)}"></label><div class="full"><button class="reference-button secondary">Apply filter</button></div></form><p class="reference-muted">Students have read-only access to published sessions.</p></article></div>` : ""}<article class="reference-card" style="margin-top:18px"><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>Date</th><th>Programme</th><th>Time</th><th>Venue</th><th>Status</th><th></th></tr></thead><tbody>${sessions.map((item) => `<tr><td><strong>${escapeHtml(item.session_date)}</strong></td><td>${escapeHtml(item.programme)}<br><span class="reference-muted">${escapeHtml(item.sport)} · ${escapeHtml(item.coach || "Coach TBA")}</span></td><td>${escapeHtml(item.start_time)} – ${escapeHtml(item.end_time)}</td><td>${escapeHtml(item.venue || "TBA")}</td><td><span class="reference-pill ${item.status === "Cancelled" ? "live" : "success"}">${escapeHtml(item.status)}</span></td><td>${isStaff() ? `<button class="reference-button danger small" data-delete-session="${item.id}">Delete</button>` : ""}</td></tr>`).join("") || `<tr><td colspan="6" class="reference-empty">No sessions scheduled for this month.</td></tr>`}</tbody></table></div></article>`);
    bindForm("#scheduleForm", (form) => request("POST", "/api/fit-track/schedule", formValues(form, ["programme_id", "session_date", "start_time", "end_time", "venue", "status", "notes"])));
    document.getElementById("monthForm")?.addEventListener("submit", (event) => { event.preventDefault(); window.location.href = `fit-track-schedule.html?month=${encodeURIComponent(event.currentTarget.elements.month.value)}`; });
    bindAction("[data-delete-session]", async (button) => { await request("DELETE", `/api/fit-track/schedule/${button.dataset.deleteSession}`); location.reload(); });
  }

  async function renderEvents() {
    const [events, sports] = await Promise.all([request("GET", "/api/fit-track/tournaments"), request("GET", "/api/fit-track/sports")]);
    layout("Events & calendar", "Events, registrations, official participants and results.", `${isAdmin() ? `<article class="reference-card" style="margin-bottom:18px"><h2>Create event</h2><form id="eventForm" class="reference-form"><label>Name<input name="name" required></label><label>Sport<select name="sport_id" required>${sports.map((sport) => `<option value="${sport.id}">${escapeHtml(sport.name)}</option>`).join("")}</select></label><label>Start date<input name="start_date" type="date" required></label><label>End date<input name="end_date" type="date"></label><label>Venue<input name="venue"></label><label>Status<select name="status"><option>Upcoming</option><option>Live</option><option>Completed</option><option>Postponed</option></select></label><label class="full">Description<textarea name="description"></textarea></label><div class="full"><button class="reference-button">Create event</button></div></form></article>` : ""}<div class="reference-grid three">${events.map((event) => `<article class="reference-card"><div class="reference-inline"><span class="reference-pill ${event.status === "Live" ? "live" : ""}">${escapeHtml(event.status)}</span><span class="reference-muted">${escapeHtml(event.start_date)}</span></div><h2 style="margin-top:12px">${escapeHtml(event.name)}</h2><p>${escapeHtml(event.sport)} · ${escapeHtml(event.venue || "Venue TBA")}</p><p>${escapeHtml(event.description || "No description provided.")}</p><div class="reference-actions"><button class="reference-button small" data-event-details="${event.id}">Open event</button><button class="reference-button secondary small" data-register="${event.id}">Register me</button></div></article>`).join("") || `<article class="reference-card reference-empty">No events have been created.</article>`}</div>`);
    bindForm("#eventForm", (form) => request("POST", "/api/fit-track/tournaments", formValues(form, ["name", "sport_id", "start_date", "end_date", "venue", "status", "description"])));
    bindAction("[data-register]", async (button) => { await request("POST", `/api/fit-track/tournaments/${button.dataset.register}/register`, {}); button.textContent = "Registered"; button.disabled = true; });
    bindAction("[data-event-details]", async (button) => showEventDetails(button.dataset.eventDetails));
  }

  async function showEventDetails(eventId) {
    const detail = await request("GET", `/api/fit-track/tournaments/${eventId}/details`);
    const event = detail.tournament;
    const modal = openModal(event.name, `<p>${escapeHtml(event.description || "No description provided.")}</p><div class="reference-grid two"><article><h3>Official participants</h3><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>Name</th><th>Department</th><th>Category</th><th>Year</th></tr></thead><tbody>${detail.participants.map((item) => `<tr><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.department)}</td><td>${escapeHtml(item.category)}</td><td>${escapeHtml(item.year)}</td></tr>`).join("") || `<tr><td colspan="4" class="reference-empty">No official participants.</td></tr>`}</tbody></table></div></article><article><h3>Results</h3>${detail.results.map((item) => `<p><strong>${escapeHtml(item.category)}</strong><br>Winner: ${escapeHtml(item.winner)}<br>Runner-up: ${escapeHtml(item.runner_up)}</p>`).join("") || `<p class="reference-empty">No results entered.</p>`}</article></div>${isAdmin() ? `<div class="reference-grid two" style="margin-top:18px"><form id="participantImportForm" class="reference-form"><h3 class="full">Import official participants</h3><label class="full">XLSX or XLS file<input name="file" type="file" accept=".xlsx,.xls" required></label><div class="full"><button class="reference-button">Import participants</button></div></form><form id="drawUploadForm" class="reference-form"><h3 class="full">Upload draw projection</h3><input type="hidden" name="tournament_id" value="${escapeHtml(eventId)}"><label>Category<select name="category"><option>Boys</option><option>Girls</option></select></label><label>Format<select name="format_type"><option>League</option><option>Knockout</option></select></label><label class="full">PDF file<input name="file" type="file" accept="application/pdf" required></label><div class="full"><button class="reference-button">Upload draw</button></div></form></div>` : ""}`);
    modal.querySelector("#participantImportForm")?.addEventListener("submit", async (event) => { event.preventDefault(); try { await request("POST", `/api/fit-track/tournaments/${eventId}/participants/import`, new FormData(event.currentTarget), true); location.reload(); } catch (error) { showAlert(error.message); } });
    modal.querySelector("#drawUploadForm")?.addEventListener("submit", async (event) => { event.preventDefault(); try { await request("POST", "/api/fit-track/draws/upload", new FormData(event.currentTarget), true); location.reload(); } catch (error) { showAlert(error.message); } });
  }

  async function renderMatches() {
    const [matches, events] = await Promise.all([request("GET", "/api/fit-track/matches"), request("GET", "/api/fit-track/tournaments")]);
    layout("Live scores", "Fixtures, scores, squads and sport-aware match updates.", `${isAdmin() ? `<article class="reference-card" style="margin-bottom:18px"><h2>Create fixture</h2><form id="matchForm" class="reference-form"><label>Tournament<select name="tournament_id" required>${events.map((event) => `<option value="${event.id}">${escapeHtml(event.name)}</option>`).join("")}</select></label><label>Category<select name="category"><option>Boys</option><option>Girls</option></select></label><label>Round<input name="round_name"></label><label>Team A<input name="team_a" required></label><label>Team B<input name="team_b" required></label><label>Date/time<input name="match_date" type="datetime-local"></label><label>Venue<input name="venue"></label><div class="full"><button class="reference-button">Create fixture</button></div></form></article>` : ""}<div class="reference-grid two">${matches.map((item) => `<article class="reference-card"><div class="reference-inline"><span class="reference-pill">${escapeHtml(item.tournament)}</span><span class="reference-pill ${item.status === "Live" ? "live" : "success"}">${escapeHtml(item.status)}</span></div><h2 style="margin-top:10px">${escapeHtml(item.sport)}</h2><p>${escapeHtml(item.category)} · ${escapeHtml(item.round_name || "Match")} · ${escapeHtml(item.match_date || "Date TBA")} · ${escapeHtml(item.venue || "Venue TBA")}</p><div class="reference-score"><div><strong>${escapeHtml(item.score_a)}</strong><span>${escapeHtml(item.team_a)}</span></div><b>VS</b><div><strong>${escapeHtml(item.score_b)}</strong><span>${escapeHtml(item.team_b)}</span></div></div>${isAdmin() ? `<form class="scoreForm reference-form" data-match-id="${item.id}"><label>Team A score<input name="score_a" value="${escapeHtml(item.score_a || "0")}"></label><label>Team B score<input name="score_b" value="${escapeHtml(item.score_b || "0")}"></label><label>Status<select name="status"><option ${item.status === "Scheduled" ? "selected" : ""}>Scheduled</option><option ${item.status === "Live" ? "selected" : ""}>Live</option><option ${item.status === "Completed" ? "selected" : ""}>Completed</option></select></label><div class="full reference-actions"><button class="reference-button small">Update score</button><button type="button" class="reference-button danger small" data-delete-match="${item.id}">Delete fixture</button></div></form>` : ""}</article>`).join("") || `<article class="reference-card reference-empty">No fixtures have been created.</article>`}</div>`);
    bindForm("#matchForm", (form) => request("POST", "/api/fit-track/matches", formValues(form, ["tournament_id", "category", "round_name", "team_a", "team_b", "match_date", "venue"])));
    document.querySelectorAll(".scoreForm").forEach((form) => form.addEventListener("submit", async (event) => { event.preventDefault(); try { await request("PATCH", `/api/fit-track/matches/${form.dataset.matchId}`, formValues(form, ["score_a", "score_b", "status"])); location.reload(); } catch (error) { showAlert(error.message); } }));
    bindAction("[data-delete-match]", async (button) => { await request("DELETE", `/api/fit-track/matches/${button.dataset.deleteMatch}`); location.reload(); });
  }

  async function renderGallery() {
    const media = await request("GET", "/api/fit-track/gallery");
    layout("Event gallery", "Media published from events, matches and campus facilities.", `${isAdmin() ? `<article class="reference-card" style="margin-bottom:18px"><h2>Publish media</h2><form id="mediaUploadForm" class="reference-form"><label>File<input name="file" type="file" accept="image/*,video/*,.pdf" required></label><label>Media type<select name="media_type"><option>photo</option><option>video</option><option>document</option></select></label><label class="full">Caption<input name="caption"></label><div class="full"><button class="reference-button">Publish media</button></div></form></article>` : ""}<div class="reference-media-grid">${media.map((item) => `<article class="reference-media">${item.media_type === "photo" ? `<img src="${apiBase}/api/fit-track/media/${item.id}/download" alt="${escapeHtml(item.caption || "Event media")}" onerror="this.style.display='none'">` : ""}<div class="reference-media-body"><strong>${escapeHtml(item.caption || "Event media")}</strong><span>${escapeHtml(item.tournament || "Campus media")} · ${escapeHtml(item.media_type)}</span><div class="reference-actions"><a class="reference-button secondary small" href="${apiBase}/api/fit-track/media/${item.id}/download">Download</a>${isAdmin() ? `<button class="reference-button danger small" data-delete-media="${item.id}">Delete</button>` : ""}</div></div></article>`).join("") || `<article class="reference-card reference-empty">No media has been published.</article>`}</div>`);
    document.getElementById("mediaUploadForm")?.addEventListener("submit", async (event) => { event.preventDefault(); try { await request("POST", "/api/fit-track/gallery/upload", new FormData(event.currentTarget), true); location.reload(); } catch (error) { showAlert(error.message); } });
    bindAction("[data-delete-media]", async (button) => { await request("DELETE", `/api/fit-track/media/${button.dataset.deleteMedia}`); location.reload(); });
  }

  async function renderAnnouncements() {
    const announcements = await request("GET", "/api/fit-track/announcements");
    layout("Announcements", "Updates shared across students, coaches and administrators.", `${isAdmin() ? `<article class="reference-card" style="margin-bottom:18px"><h2>Publish announcement</h2><form id="announcementForm" class="reference-form"><label>Title<input name="title" required></label><label>Image<input name="image" type="file" accept="image/*"></label><label class="full">Message<textarea name="message" required></textarea></label><div class="full"><button class="reference-button">Publish announcement</button></div></form></article>` : ""}<div class="reference-grid">${announcements.map((item) => `<article class="reference-card">${item.image_path ? `<img src="${apiBase}/api/fit-track/announcements/${item.id}/image" alt="${escapeHtml(item.title)}" style="width:100%;max-height:190px;object-fit:cover;border-radius:9px;margin-bottom:12px" onerror="this.style.display='none'">` : ""}<span class="reference-pill">${escapeHtml(item.created_at || "")}</span><h2 style="margin-top:12px">${escapeHtml(item.title)}</h2><p>${escapeHtml(item.message)}</p>${isAdmin() ? `<button class="reference-button danger small" data-delete-announcement="${item.id}">Archive</button>` : ""}</article>`).join("") || `<article class="reference-card reference-empty">No announcements yet.</article>`}</div>`);
    document.getElementById("announcementForm")?.addEventListener("submit", async (event) => { event.preventDefault(); try { await request("POST", "/api/fit-track/announcements/upload", new FormData(event.currentTarget), true); location.reload(); } catch (error) { showAlert(error.message); } });
    bindAction("[data-delete-announcement]", async (button) => { await request("DELETE", `/api/fit-track/announcements/${button.dataset.deleteAnnouncement}`); location.reload(); });
  }

  async function contacts() {
    if (role() === "admin") { const result = await request("GET", "/api/users"); return result.users || []; }
    if (role() === "coach") { const students = await request("GET", "/api/fit-track/students"); return students.map((student) => ({ id: student.id, full_name: student.name, email: student.email })); }
    const result = await request("GET", "/api/student/coach"); return result.coach ? [result.coach] : [];
  }

  async function renderChat() {
    const people = await contacts();
    const selected = root.dataset.contact || people[0]?.id || "";
    const messages = selected ? await request("GET", `/api/fit-track/messages?with_user_id=${encodeURIComponent(selected)}`) : [];
    layout("Chat", "Stay connected with the coaches and athletes available to your account.", `<div class="reference-grid two"><article class="reference-card"><h2>Contacts</h2><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>Name</th><th>Role</th><th></th></tr></thead><tbody>${people.map((person) => `<tr><td>${escapeHtml(person.full_name || person.name || person.email)}</td><td>${escapeHtml(person.role || (role() === "student" ? "Coach" : "Student"))}</td><td><button class="reference-button secondary small" data-contact="${person.id}">Open</button></td></tr>`).join("") || `<tr><td colspan="3" class="reference-empty">No permitted contacts are available.</td></tr>`}</tbody></table></div></article><article class="reference-card"><h2>Conversation</h2>${selected ? `<form id="messageForm" class="reference-form"><label class="full">Message<textarea name="message" required></textarea></label><input type="hidden" name="receiver_user_id" value="${escapeHtml(selected)}"><div class="full"><button class="reference-button">Send message</button></div></form><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>From</th><th>Message</th><th>Sent</th></tr></thead><tbody>${messages.map((item) => `<tr><td>${escapeHtml(item.sender_name)}</td><td>${escapeHtml(item.message)}</td><td>${escapeHtml(item.created_at)}</td></tr>`).join("") || `<tr><td colspan="3" class="reference-empty">No messages yet.</td></tr>`}</tbody></table></div>` : `<p class="reference-empty">Choose a permitted contact to start.</p>`}</article></div>`);
    bindAction("[data-contact]", async (button) => { root.dataset.contact = button.dataset.contact; await renderChat(); });
    bindForm("#messageForm", (form) => request("POST", "/api/fit-track/messages", formValues(form, ["receiver_user_id", "message"])));
  }

  async function renderReports() {
    const [report, projection] = await Promise.all([request("GET", "/api/fit-track/reports"), request("GET", "/api/fit-track/reports/projection?period=monthly")]);
    layout("Reports & analytics", "Privacy-scoped summaries and cumulative projections for your role.", `<div class="reference-grid">${card(report.summary.students, "Students in scope")}${card(report.summary.programmes, "Programmes in scope")}${card(report.summary.enrollments, "Active enrollments")}${card(report.summary.assessments, "Assessment records")}</div><article class="reference-card" style="margin-top:18px"><div class="reference-toolbar"><div><h2>${escapeHtml(projection.period)} projection</h2><p>${escapeHtml(projection.from_date)} to ${escapeHtml(projection.to_date)}</p></div><div class="reference-actions"><a class="reference-button secondary small" href="${apiBase}/api/fit-track/reports/projection.csv?period=weekly">Weekly CSV</a><a class="reference-button secondary small" href="${apiBase}/api/fit-track/reports/projection.csv?period=monthly">Monthly CSV</a><a class="reference-button secondary small" href="${apiBase}/api/fit-track/reports/projection.csv?period=yearly">Yearly CSV</a></div></div><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>Sport</th><th>Athletes</th><th>Sessions</th><th>Attendance</th><th>Average performance</th><th>Metrics</th></tr></thead><tbody>${projection.sports.map((item) => `<tr><td>${escapeHtml(item.sport)}</td><td>${escapeHtml(item.athletes)}</td><td>${escapeHtml(item.sessions)}</td><td>${escapeHtml(item.attendance_rate)}%</td><td>${escapeHtml(item.avg_performance)}</td><td>${escapeHtml((item.metrics || []).map((metric) => `${metric.metric_label}: ${metric.avg_score}`).join(" · ") || "—")}</td></tr>`).join("") || `<tr><td colspan="6" class="reference-empty">No projection data yet.</td></tr>`}</tbody></table></div></article><article class="reference-card" style="margin-top:18px"><h2>Programme performance</h2><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>Programme</th><th>Sport</th><th>Athletes</th><th>Present sessions</th><th>Total sessions</th></tr></thead><tbody>${report.by_programme.map((item) => `<tr><td>${escapeHtml(item.programme)}</td><td>${escapeHtml(item.sport)}</td><td>${escapeHtml(item.athletes)}</td><td>${escapeHtml(item.present_sessions)}</td><td>${escapeHtml(item.total_sessions)}</td></tr>`).join("") || `<tr><td colspan="5" class="reference-empty">No programme data yet.</td></tr>`}</tbody></table></div></article>`);
  }

  async function mount() {
    try {
      const sessionData = await request("GET", "/api/session");
      currentUser = sessionData.user || sessionData;
      if (page === "hub") return renderHub();
      if (page === "profile") return renderProfile();
      if (page === "sports") return renderSports();
      if (page === "coaching") return renderCoaching();
      if (page === "schedule") return renderSchedule();
      if (page === "events") return renderEvents();
      if (page === "matches") return renderMatches();
      if (page === "gallery") return renderGallery();
      if (page === "announcements") return renderAnnouncements();
      if (page === "chat") return renderChat();
      if (page === "reports") return renderReports();
      return renderHub();
    } catch (error) {
      root.innerHTML = `<div class="reference-card" style="margin:30px"><h2>Unable to load this page</h2><p>${escapeHtml(error.message)}</p><a href="fit-track-features.html">Return to Fit-Track overview</a></div>`;
    }
  }

  mount();
})();
