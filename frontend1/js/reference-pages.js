(function () {
  "use strict";

  const root = document.getElementById("referenceApp");
  if (!root) return;
  const page = root.dataset.page || "hub";
  const apiBase = (window.FITNESS_API_BASE || window.APP_CONFIG?.API_BASE || "").replace(/\/$/, "");
  let currentUser = null;

  const esc = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
  const request = async (method, path, body) => {
    const response = await fetch(apiBase + path, {
      method,
      credentials: "include",
      headers: {"Content-Type": "application/json"},
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.success === false) throw new Error(data.message || "Request failed.");
    return data.data ?? data;
  };
  const formValue = (form, name) => form.elements[name]?.value?.trim() || null;
  const formData = (form, fields) => Object.fromEntries(fields.map((field) => [field, formValue(form, field)]).filter(([, value]) => value !== null));
  const role = () => currentUser?.role || "student";
  const isStaff = () => ["admin", "coach"].includes(role());
  const isAdmin = () => role() === "admin";
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
    root.innerHTML = `<div class="reference-shell"><aside class="reference-sidebar" id="referenceSidebar">
      <div class="reference-brand"><div class="reference-brand-mark">FT</div><div><strong>Fit Track</strong><span>SPORTS PERFORMANCE</span></div></div>
      <div class="reference-nav-label">REFERENCE FEATURES</div><nav class="reference-nav">${nav.map(([key, icon, label, href]) => `<a class="${page === key ? "active" : ""}" href="${href}"><i class="bi bi-${icon}"></i>${label}</a>`).join("")}</nav>
      <div class="reference-identity"><strong>${esc(currentUser?.full_name || currentUser?.email || "Account")}</strong>${esc(role().toUpperCase())}<br><span>Root login preserved</span></div>
    </aside><main class="reference-main"><header class="reference-topbar"><div style="display:flex;align-items:center;gap:10px"><button class="reference-menu-button" onclick="document.getElementById('referenceSidebar').classList.toggle('open')" aria-label="Open menu">☰</button><div><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div></div><div class="reference-user">${esc(currentUser?.full_name || currentUser?.email || "Signed in")}</div></header><section class="reference-content"><div id="referenceAlert" class="reference-alert"></div>${content}</section></main></div>`;
  }
  function alertMessage(message) { const box = document.getElementById("referenceAlert"); if (box) { box.textContent = message; box.classList.add("show"); } }
  function bindForm(selector, callback) { document.querySelector(selector)?.addEventListener("submit", async (event) => { event.preventDefault(); try { await callback(event.currentTarget); location.reload(); } catch (error) { alertMessage(error.message); } }); }
  function card(title, value, label) { return `<article class="reference-card"><div class="reference-stat">${esc(value)}</div><div class="reference-stat-label">${esc(label || title)}</div></article>`; }

  async function renderHub() {
    const stats = await request("GET", "/api/fit-track/dashboard");
    layout("Fit-Track operations", "Reference features integrated with your existing Fitness Tracker portal.", `<div class="reference-toolbar"><div><h2>Sports operations hub</h2><p>Manage the same programme, athlete, event and reporting workflows as the reference project.</p></div></div><div class="reference-grid">${card("Sports", stats.sports, "Active sports")}${card("Programmes", stats.programmes, "Active programmes")}${card("Events", stats.tournaments, "Upcoming events")}${card("Live", stats.live_matches, "Live matches")}</div><div class="reference-grid two" style="margin-top:18px"><article class="reference-card"><h2>What is included</h2><p>Sports and facilities, student passports, programmes and enrollments, attendance and daily assessments, coaching schedules, tournaments, registrations, fixtures, live scoring, gallery media, announcements, certificates, reports and chat.</p></article><article class="reference-card"><h2>Data ownership</h2><p>Students and coaches continue to sign in through the root project. All new records are stored in PostgreSQL and connected to those authenticated accounts.</p><div class="reference-actions"><a class="reference-button" href="fit-track-events.html">Open events</a><a class="reference-button secondary" href="fit-track-reports.html">View reports</a></div></article></div>`);
  }

  async function renderSports() {
    const sports = await request("GET", "/api/fit-track/sports");
    layout("Sports & facilities", "The reference sports catalogue, venues and facility metadata.", `<div class="reference-toolbar"><div><h2>Sports catalogue</h2><p>Update the sports catalog without affecting root authentication.</p></div></div>${isAdmin() ? `<article class="reference-card" style="margin-bottom:18px"><h3>Add sport</h3><form id="sportForm" class="reference-form"><label>Name<input name="name" required></label><label>Activity type<input name="activity_type" placeholder="Team sport"></label><label>Venue<input name="venue" placeholder="Main ground"></label><div class="full"><button class="reference-button">Save sport</button></div></form></article>` : ""}<article class="reference-card"><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>Sport</th><th>Activity</th><th>Venue</th><th>Status</th></tr></thead><tbody>${sports.map((sport) => `<tr><td><strong>${esc(sport.name)}</strong></td><td>${esc(sport.activity_type)}</td><td>${esc(sport.venue || "—")}</td><td><span class="reference-pill">Active</span></td></tr>`).join("") || `<tr><td colspan="4" class="reference-empty">No sports have been added.</td></tr>`}</tbody></table></div></article>`);
    bindForm("#sportForm", (form) => request("POST", "/api/fit-track/sports", formData(form, ["name", "activity_type", "venue"])));
  }

  async function renderCoaching() {
    const [programmes, sports, students, assessments] = await Promise.all([request("GET", "/api/fit-track/programmes"), request("GET", "/api/fit-track/sports"), isStaff() ? request("GET", "/api/fit-track/students") : Promise.resolve([]), request("GET", "/api/fit-track/assessments/daily")]);
    layout("Programmes & athlete development", "Programmes, enrollments and daily assessment records from the reference workflow.", `${isStaff() ? `<article class="reference-card" style="margin-bottom:18px"><h3>Create programme</h3><form id="programmeForm" class="reference-form"><label>Name<input name="name" required></label><label>Sport<select name="sport_id" required>${sports.map((sport) => `<option value="${sport.id}">${esc(sport.name)}</option>`).join("")}</select></label><label>Coach ID<input name="coach_id" placeholder="Optional for admin"></label><label>Schedule<input name="schedule" placeholder="Mon/Wed 5:00 PM"></label><label>Venue<input name="venue"></label><div class="full"><button class="reference-button">Create programme</button></div></form></article>` : ""}<div class="reference-grid two"><article class="reference-card"><h2>Programmes</h2><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>Name</th><th>Sport</th><th>Coach</th><th>Athletes</th></tr></thead><tbody>${programmes.map((item) => `<tr><td><strong>${esc(item.name)}</strong><br><small>${esc(item.schedule || "Schedule not set")}</small></td><td>${esc(item.sport)}</td><td>${esc(item.coach || "TBA")}</td><td>${esc(item.enrolment_count)}</td></tr>`).join("") || `<tr><td colspan="4" class="reference-empty">No programmes yet.</td></tr>`}</tbody></table></div></article><article class="reference-card"><h2>Daily assessments</h2><p>${assessments.length} assessment record(s) are available to your account.</p><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>Athlete</th><th>Date</th><th>Overall</th><th>Remarks</th></tr></thead><tbody>${assessments.slice(0, 12).map((item) => `<tr><td>${esc(item.student_name)}</td><td>${esc(item.session_date)}</td><td>${esc(item.overall_performance || "—")}</td><td>${esc(item.remarks || "—")}</td></tr>`).join("") || `<tr><td colspan="4" class="reference-empty">No assessment records yet.</td></tr>`}</tbody></table></div></article></div>`);
    bindForm("#programmeForm", (form) => request("POST", "/api/fit-track/programmes", formData(form, ["name", "sport_id", "coach_id", "schedule", "venue"])));
  }

  async function renderSchedule() {
    const [sessions, programmes] = await Promise.all([request("GET", "/api/fit-track/schedule"), request("GET", "/api/fit-track/programmes")]);
    layout("Coaching schedule", "Publish and maintain dated coaching sessions for athletes and coaches.", `${isStaff() ? `<article class="reference-card" style="margin-bottom:18px"><h3>Add coaching session</h3><form id="scheduleForm" class="reference-form"><label>Programme<select name="programme_id" required>${programmes.map((item) => `<option value="${item.id}">${esc(item.name)} · ${esc(item.sport)}</option>`).join("")}</select></label><label>Date<input name="session_date" type="date" required></label><label>Start<input name="start_time" type="time" required></label><label>End<input name="end_time" type="time" required></label><label>Venue<input name="venue"></label><label>Status<select name="status"><option>Scheduled</option><option>Rescheduled</option><option>Cancelled</option><option>Completed</option></select></label><label class="full">Notes<textarea name="notes"></textarea></label><div class="full"><button class="reference-button">Publish session</button></div></form></article>` : ""}<article class="reference-card"><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>Date</th><th>Programme</th><th>Time</th><th>Venue</th><th>Status</th></tr></thead><tbody>${sessions.map((item) => `<tr><td><strong>${esc(item.session_date)}</strong></td><td>${esc(item.programme)}<br><small>${esc(item.sport)} · ${esc(item.coach || "Coach TBA")}</small></td><td>${esc(item.start_time)} – ${esc(item.end_time)}</td><td>${esc(item.venue || "TBA")}</td><td><span class="reference-pill ${item.status === "Cancelled" ? "live" : ""}">${esc(item.status)}</span></td></tr>`).join("") || `<tr><td colspan="5" class="reference-empty">No sessions have been scheduled.</td></tr>`}</tbody></table></div></article>`);
    bindForm("#scheduleForm", (form) => request("POST", "/api/fit-track/schedule", formData(form, ["programme_id", "session_date", "start_time", "end_time", "venue", "status", "notes"])));
  }

  async function renderEvents() {
    const [events, sports] = await Promise.all([request("GET", "/api/fit-track/tournaments"), request("GET", "/api/fit-track/sports")]);
    layout("Events & calendar", "Tournament registration, event details and the reference event calendar.", `${isAdmin() ? `<article class="reference-card" style="margin-bottom:18px"><h3>Create event</h3><form id="eventForm" class="reference-form"><label>Name<input name="name" required></label><label>Sport<select name="sport_id" required>${sports.map((sport) => `<option value="${sport.id}">${esc(sport.name)}</option>`).join("")}</select></label><label>Start date<input name="start_date" type="date" required></label><label>End date<input name="end_date" type="date"></label><label>Venue<input name="venue"></label><label>Status<select name="status"><option>Upcoming</option><option>Live</option><option>Completed</option><option>Postponed</option></select></label><label class="full">Description<textarea name="description"></textarea></label><div class="full"><button class="reference-button">Create event</button></div></form></article>` : ""}<div class="reference-grid">${events.map((item) => `<article class="reference-card"><span class="reference-pill">${esc(item.status)}</span><h3 style="margin-top:12px">${esc(item.name)}</h3><p>${esc(item.sport)} · ${esc(item.start_date)}${item.end_date ? ` to ${esc(item.end_date)}` : ""}<br>${esc(item.venue || "Venue TBA")}</p><p>${esc(item.description || "No description provided.")}</p><div class="reference-actions"><button class="reference-button secondary" data-register="${item.id}">Register me</button><a class="reference-button" href="fit-track-matches.html">Fixtures</a></div></article>`).join("") || `<article class="reference-card reference-empty">No events have been created.</article>`}</div>`);
    bindForm("#eventForm", (form) => request("POST", "/api/fit-track/tournaments", formData(form, ["name", "sport_id", "start_date", "end_date", "venue", "status", "description"])));
    document.querySelectorAll("[data-register]").forEach((button) => button.addEventListener("click", async () => { try { await request("POST", `/api/fit-track/tournaments/${button.dataset.register}/register`, {}); button.textContent = "Registered"; button.disabled = true; } catch (error) { alertMessage(error.message); } }));
  }

  async function renderMatches() {
    const [matches, events] = await Promise.all([request("GET", "/api/fit-track/matches"), request("GET", "/api/fit-track/tournaments")]);
    layout("Live scores", "Fixtures, scores and sport-aware match updates.", `${isAdmin() ? `<article class="reference-card" style="margin-bottom:18px"><h3>Create fixture</h3><form id="matchForm" class="reference-form"><label>Tournament<select name="tournament_id" required>${events.map((event) => `<option value="${event.id}">${esc(event.name)}</option>`).join("")}</select></label><label>Round<input name="round_name" placeholder="Semi-final"></label><label>Team A<input name="team_a" required></label><label>Team B<input name="team_b" required></label><label>Date/time<input name="match_date" type="datetime-local"></label><label>Venue<input name="venue"></label><div class="full"><button class="reference-button">Create fixture</button></div></form></article>` : ""}<div class="reference-grid two">${matches.map((item) => `<article class="reference-card"><div style="display:flex;justify-content:space-between;gap:12px"><div><span class="reference-pill">${esc(item.tournament)}</span><h3 style="margin-top:10px">${esc(item.sport)}</h3></div><span class="reference-pill ${item.status === "Live" ? "live" : ""}">${esc(item.status)}</span></div><p>${esc(item.round_name || "Match")} · ${esc(item.match_date || "Date TBA")} · ${esc(item.venue || "Venue TBA")}</p><div class="reference-score"><div><strong>${esc(item.score_a)}</strong><span>${esc(item.team_a)}</span></div><b>VS</b><div><strong>${esc(item.score_b)}</strong><span>${esc(item.team_b)}</span></div></div>${item.live_note ? `<p>${esc(item.live_note)}</p>` : ""}</article>`).join("") || `<article class="reference-card reference-empty">No fixtures have been created.</article>`}</div>`);
    bindForm("#matchForm", (form) => request("POST", "/api/fit-track/matches", formData(form, ["tournament_id", "round_name", "team_a", "team_b", "match_date", "venue"])));
  }

  async function renderGallery() {
    const media = await request("GET", "/api/fit-track/gallery");
    layout("Event gallery", "Media published from tournaments, matches and campus facilities.", `${isAdmin() ? `<article class="reference-card" style="margin-bottom:18px"><h3>Add media</h3><form id="mediaForm" class="reference-form"><label>File or image URL<input name="file_path" required placeholder="/uploads/events/image.jpg"></label><label>Media type<select name="media_type"><option>photo</option><option>video</option><option>document</option></select></label><label class="full">Caption<input name="caption"></label><div class="full"><button class="reference-button">Publish media</button></div></form></article>` : ""}<div class="reference-media-grid">${media.map((item) => `<article class="reference-media">${item.media_type === "photo" ? `<img src="${esc(item.file_path)}" alt="${esc(item.caption || "Event media")}" onerror="this.style.display='none'">` : ""}<div><strong>${esc(item.caption || "Event media")}</strong><br><span>${esc(item.tournament || "Campus media")} · ${esc(item.media_type)}</span></div></article>`).join("") || `<article class="reference-card reference-empty">No media has been published.</article>`}</div>`);
    bindForm("#mediaForm", (form) => request("POST", "/api/fit-track/gallery", formData(form, ["file_path", "media_type", "caption"])));
  }

  async function renderAnnouncements() {
    const announcements = await request("GET", "/api/fit-track/announcements");
    layout("Announcements", "Keep students, coaches and administrators aligned with the latest updates.", `${isAdmin() ? `<article class="reference-card" style="margin-bottom:18px"><h3>Publish announcement</h3><form id="announcementForm" class="reference-form"><label>Title<input name="title" required></label><label>Image URL<input name="image_path"></label><label class="full">Message<textarea name="message" required></textarea></label><div class="full"><button class="reference-button">Publish announcement</button></div></form></article>` : ""}<div class="reference-grid">${announcements.map((item) => `<article class="reference-card"><span class="reference-pill">${esc(item.created_at)}</span><h3 style="margin-top:12px">${esc(item.title)}</h3><p>${esc(item.message)}</p>${isAdmin() ? `<button class="reference-button danger" data-delete-announcement="${item.id}">Archive</button>` : ""}</article>`).join("") || `<article class="reference-card reference-empty">No announcements yet.</article>`}</div>`);
    bindForm("#announcementForm", (form) => request("POST", "/api/fit-track/announcements", formData(form, ["title", "message", "image_path"])));
    document.querySelectorAll("[data-delete-announcement]").forEach((button) => button.addEventListener("click", async () => { try { await request("DELETE", `/api/fit-track/announcements/${button.dataset.deleteAnnouncement}`); location.reload(); } catch (error) { alertMessage(error.message); } }));
  }

  async function renderChat() {
    const messages = await request("GET", "/api/fit-track/messages");
    layout("Chat", "A simple, authenticated conversation stream for student and coach coordination.", `<article class="reference-card" style="margin-bottom:18px"><h3>Send a message</h3><form id="messageForm" class="reference-form"><label>Recipient user ID<input name="receiver_user_id" type="number" required></label><label class="full">Message<textarea name="message" required></textarea></label><div class="full"><button class="reference-button">Send message</button></div></form></article><article class="reference-card"><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>From</th><th>To</th><th>Message</th><th>Sent</th></tr></thead><tbody>${messages.map((item) => `<tr><td>${esc(item.sender_name)}</td><td>${esc(item.receiver_name)}</td><td>${esc(item.message)}</td><td>${esc(item.created_at)}</td></tr>`).join("") || `<tr><td colspan="4" class="reference-empty">No messages yet.</td></tr>`}</tbody></table></div></article>`);
    bindForm("#messageForm", (form) => request("POST", "/api/fit-track/messages", formData(form, ["receiver_user_id", "message"])));
  }

  async function renderReports() {
    const report = await request("GET", "/api/fit-track/reports");
    layout("Reports & analytics", "Operational summaries for athletes, programmes, attendance and development.", `<div class="reference-grid">${card("Students", report.summary.students, "Active students")}${card("Programmes", report.summary.programmes, "Active programmes")}${card("Enrollments", report.summary.enrollments, "Active enrollments")}${card("Assessments", report.summary.assessments, "Daily assessments")}</div><article class="reference-card" style="margin-top:18px"><h2>Programme performance</h2><div class="reference-table-wrap"><table class="reference-table"><thead><tr><th>Programme</th><th>Sport</th><th>Athletes</th><th>Present sessions</th><th>Total sessions</th></tr></thead><tbody>${report.by_programme.map((item) => `<tr><td>${esc(item.programme)}</td><td>${esc(item.sport)}</td><td>${esc(item.athletes)}</td><td>${esc(item.present_sessions)}</td><td>${esc(item.total_sessions)}</td></tr>`).join("") || `<tr><td colspan="5" class="reference-empty">No programme data yet.</td></tr>`}</tbody></table></div></article>`);
  }

  async function renderProfile() {
    if (role() !== "student") {
      layout("My Fit-Track account", "Your existing root login and account identity remain unchanged.", `<article class="reference-card"><h2>${esc(currentUser?.full_name || "Account")}</h2><p>${esc(currentUser?.email || "")} · ${esc(role().toUpperCase())}</p><p>This account can manage the reference sports operations through the pages in the left navigation.</p></article>`);
      return;
    }
    const profileResponse = await request("GET", "/api/profile");
    const data = profileResponse.profile || profileResponse;
    const [achievements, certificates] = await Promise.all([
      request("GET", `/api/fit-track/students/${currentUser.id}/achievements`),
      request("GET", `/api/fit-track/students/${currentUser.id}/certificates`)
    ]);
    layout("My Fit-Track passport", "Your existing root account remains the source of truth; reference fields are editable here.", `<article class="reference-card"><h2>${esc(currentUser?.full_name || "Student")}</h2><p>${esc(currentUser?.email || "")} · ${esc(data.department || "Department not set")}</p><form id="profileForm" class="reference-form"><label>Full name<input name="full_name" value="${esc(currentUser?.full_name || "")}"></label><label>Phone<input name="contact_number" value="${esc(currentUser?.contact_number || "")}"></label><label>Date of birth<input name="date_of_birth" type="date" value="${esc(data.date_of_birth || "")}"></label><label>Emergency contact<input name="emergency_contact" value="${esc(data.emergency_contact || "")}"></label><label>Student number<input name="student_number" value="${esc(data.student_number || "")}"></label><label>Semester<input name="semester" value="${esc(data.semester || "")}"></label><label>Department<input name="department" value="${esc(data.department || "")}"></label><label>Blood group<input name="blood_group" value="${esc(data.blood_group || "")}"></label><label class="full">Bio<textarea name="bio">${esc(data.bio || "")}</textarea></label><div class="full"><button class="reference-button">Save passport</button></div></form></article><div class="reference-grid two" style="margin-top:18px"><article class="reference-card"><h2>Achievements</h2>${achievements.map((item) => `<p><strong>${esc(item.title)}</strong><br>${esc(item.sport || "")}${item.level ? ` · ${esc(item.level)}` : ""}${item.achievement_year ? ` · ${esc(item.achievement_year)}` : ""}</p>`).join("") || `<div class="reference-empty">No achievements recorded yet.</div>`}</article><article class="reference-card"><h2>Certificates</h2>${certificates.map((item) => `<p><strong>${esc(item.title)}</strong><br>${esc(item.issuer || "Issuer not set")}${item.issue_date ? ` · ${esc(item.issue_date)}` : ""}${item.certificate_no ? ` · ${esc(item.certificate_no)}` : ""}</p>`).join("") || `<div class="reference-empty">No certificates recorded yet.</div>`}</article></div>`);
    bindForm("#profileForm", (form) => request("PATCH", `/api/fit-track/students/${currentUser.id}`, formData(form, ["full_name", "contact_number", "date_of_birth", "emergency_contact", "student_number", "semester", "department", "blood_group", "bio"])));
  }

  async function mount() {
    try {
      const sessionData = await request("GET", "/api/session");
      currentUser = sessionData.user || sessionData;
      if (page === "hub") return renderHub();
      if (page === "sports") return renderSports();
      if (page === "coaching") return renderCoaching();
      if (page === "schedule") return renderSchedule();
      if (page === "events") return renderEvents();
      if (page === "matches") return renderMatches();
      if (page === "gallery") return renderGallery();
      if (page === "announcements") return renderAnnouncements();
      if (page === "chat") return renderChat();
      if (page === "reports") return renderReports();
      return renderProfile();
    } catch (error) {
      root.innerHTML = `<div class="reference-card" style="margin:30px"><h2>Unable to load this page</h2><p>${esc(error.message)}</p><a href="fit-track-features.html">Return to Fit-Track overview</a></div>`;
    }
  }
  mount();
})();
