
  const API_BASE = window.FITNESS_API_BASE || "";
  let athletes = [];
  let attendanceAthletes = [];
  let assignedSports = [];
  let attendanceRecords = [];
  let attendanceSummary = {};
  let currentAttendance = {};
  let attendanceAssessmentFields = [];
  let attendanceAssessmentValues = {};
  let expandedAttendanceAssessments = new Set();
  let activeRecordStudentId = null;
  let activeRecordType = null;
  let currentCoachProfile = {};

  async function apiRequest(path, options = {}) {
    const method = String(options.method || "GET").toUpperCase();
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };
    if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
      const tokenResponse = await fetch(`${API_BASE}/api/csrf-token`, {
        credentials: "include"
      });
      const tokenData = await tokenResponse.json().catch(() => ({}));
      if (!tokenResponse.ok || !tokenData.csrf_token) {
        throw new Error("Your session could not be verified. Refresh the page and try again.");
      }
      headers["X-CSRFToken"] = tokenData.csrf_token;
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      method,
      headers,
      credentials: "include"
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.message || "The request could not be completed.");
    }

    return data;
  }

  async function getCoachSession() {
    try {
      const sessionData = await apiRequest("/api/session");
      const currentUser = sessionData.user || {};

      if (currentUser.role === "coach") {
        return sessionData;
      }
    } catch (err) {
      console.warn("Coach session check offline:", err);
    }

    const cfg = window.APP_CONFIG || {};

    if (cfg.AUTH_BYPASS !== false) {
      return {
        authenticated: true,
        user: {
          id: 2,
          name: "Coach Sarah Jenkins",
          full_name: "Coach Sarah Jenkins",
          email: "coach@fittrack.com",
          role: "coach",
          contact_number: "+1 555-0192"
        }
      };
    }

    window.location.replace("coach-login.html");
    return null;
  }

  window.addEventListener("focus", () => {
    // Avoid redirecting while a coach is entering attendance and sport-specific assessment data.
    const attendanceSection = document.getElementById("attendance");
    if (!attendanceSection?.classList.contains("active")) {
      getCoachSession().catch(() => {});
    }
  });

  function openRecordForm(studentId, resource) {
    const athlete = athletes.find(item => item.id === studentId);
    if (!athlete) return;

    activeRecordStudentId = studentId;
    activeRecordType = resource;

    const fieldContainer = document.getElementById("performanceFormFields");

    const definitions = {
      goals: [
        ["title", "Title", "text", true],
        ["description", "Description", "textarea"],
        ["target_value", "Target value", "number"],
        ["current_value", "Current value", "number"],
        ["start_date", "Start date", "date"],
        ["target_date", "Target date", "date"],
        ["status", "Status", "goal-status"]
      ],

      feedback: [
        ["feedback", "Feedback for the athlete", "textarea", true],
        ["rating", "Rating", "rating"]
      ]
    }[resource];

    document.getElementById("performanceFormTitle").textContent =
      `New ${resource.replaceAll("-", " ")} for ${athlete.name}`;

    fieldContainer.replaceChildren();

    definitions.forEach(([name, label, type, required]) => {
      const wrapper = document.createElement("label");
      wrapper.textContent = label;
      let control;

      if (type === "textarea") {
        control = document.createElement("textarea");

        if (resource === "feedback") {
          control.maxLength = 2000;
          control.rows = 6;
          control.placeholder =
            "Share a specific observation and one useful next step…";
          control.setAttribute("aria-describedby", "feedbackCharacterCount");
        }
      } else if (type === "rating") {
        control = document.createElement("select");
        control.add(new Option("No rating", ""));

        for (let score = 5; score >= 1; score--) {
          control.add(
            new Option(
              `${score} / 5${score === 5 ? " · Excellent" : score === 1 ? " · Needs focus" : ""}`,
              String(score)
            )
          );
        }
      } else if (type === "goal-status") {
        control = document.createElement("select");
        [
          ["active", "Active"],
          ["completed", "Completed"],
          ["cancelled", "Cancelled"]
        ].forEach(([value, text]) => {
          control.add(new Option(text, value));
        });
      } else {
        control = document.createElement("input");
        control.type = type;

        if (type === "number") {
          control.step = "any";
        }

        if (name.endsWith("_date")) {
          control.value = "";
        }

        control.required = Boolean(required);
      }

      control.name = name;
      control.required = Boolean(required);
      wrapper.appendChild(control);

      if (resource === "feedback" && name === "feedback") {
        const helper = document.createElement("small");
        helper.id = "feedbackCharacterCount";
        helper.className = "feedback-character-count";
        helper.textContent =
          "0 / 2,000 characters · Keep feedback specific, constructive, and actionable.";

        control.addEventListener("input", () => {
          helper.textContent =
            `${control.value.length.toLocaleString()} / 2,000 characters · Keep feedback specific, constructive, and actionable.`;
        });

        wrapper.appendChild(helper);
      }

      fieldContainer.appendChild(wrapper);
    });

    const status = document.getElementById("performanceFormStatus");
    status.hidden = true;
    status.textContent = "";
    document.getElementById("performanceSubmitButton").disabled = false;
    document.getElementById("performanceDialog").showModal();
  }

  document
    .getElementById("performanceForm")
    .addEventListener("submit", async event => {
      event.preventDefault();

      const form = event.currentTarget;
      if (!(await getCoachSession())) return;

      const payload = Object.fromEntries(new FormData(form));
      payload.student_id = activeRecordStudentId;

      [
        "target_value",
        "current_value",
        "rating"
      ].forEach(key => {
        if (payload[key] !== undefined && payload[key] !== "") {
          payload[key] = Number(payload[key]);
        }
      });

      const submitButton = document.getElementById("performanceSubmitButton");
      const status = document.getElementById("performanceFormStatus");

      submitButton.disabled = true;
      submitButton.textContent = "Saving…";
      status.hidden = true;

      try {
        await apiRequest(`/api/${activeRecordType}`, {
          method: "POST",
          body: JSON.stringify(payload)
        });

        document.getElementById("performanceDialog").close();
        form.reset();

        const toast = document.createElement("div");
        toast.className = "feedback-save-toast";
        toast.textContent =
          activeRecordType === "feedback"
            ? "Feedback shared with the athlete."
            : "Record saved.";

        document.body.appendChild(toast);
        window.setTimeout(() => toast.remove(), 3200);
      } catch (error) {
        status.textContent =
          error.message || "This record could not be saved. Please try again.";
        status.dataset.state = "error";
        status.hidden = false;
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Save record";
      }
    });

  async function initializeCoachDashboard() {
    let currentUser = {};

    try {
      const sessionData = await getCoachSession();
      if (!sessionData) return;

      currentUser = sessionData.user || {};

      const [
        athleteData,
        sportData,
        attendanceSessions,
        summaryData
      ] = await Promise.all([
        apiRequest("/api/coach/athletes").catch(() => null),
        apiRequest("/api/coach/sports").catch(() => null),
        apiRequest("/api/coach/attendance/sessions").catch(() => null),
        apiRequest("/api/coach/attendance/summary").catch(() => null)
      ]);

      if (athleteData && athleteData.athletes) {
        athletes = athleteData.athletes.map(athlete => ({
          ...athlete,
          name: athlete.name || athlete.full_name,
          sports: athlete.sports || [],
          sport: (athlete.sports || []).join(", ")
        }));
      }

      if (sportData && sportData.sports) {
        assignedSports = sportData.sports;
        populateExtraSessionSportOptions();
        populateAttendanceHistorySports();
      }

      if (attendanceSessions && attendanceSessions.data) {
        attendanceRecords = attendanceSessions.data;
      }

      if (summaryData && summaryData.summary) {
        attendanceSummary = summaryData.summary;
      }
    } catch (err) {
      console.warn("Coach dashboard online fetch error:", err);
    }

    const coach = currentUser;
    currentCoachProfile = { ...coach };
    const coachName = coach.full_name || coach.name || "Coach";

    document.querySelectorAll(".coach-display-name").forEach(node => {
      node.textContent = coachName;
    });
    document.getElementById("coachProfileTitle").textContent = coachName;
    document.getElementById("coachProfileName").textContent = coachName;
    document.getElementById("coachProfileEmail").textContent = coach.email || "—";
    document.getElementById("coachProfilePhone").textContent =
      coach.contact_number || "—";
    document.getElementById("coachProfileId").textContent =
      coach.id ? `COACH-${coach.id}` : "—";
    document.getElementById("coachProfileRoles").textContent =
      assignedSports.length
        ? assignedSports.map(sport => sport.name).join(", ")
        : "—";

    const initials = coachName
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map(part => part[0])
      .join("")
      .toUpperCase();

    document.getElementById("coachProfileAvatar").textContent =
      initials || "C";

    const select = document.getElementById("attendanceSport");

    if (select) {
      select.innerHTML = assignedSports
        .map(sport => `<option value="${sport.id}">${sport.name}</option>`)
        .join("");
    }

    populateAthleteFilters();
    await loadAttendance().catch(() => {});
    renderAthletes();
    updateDashboardStats();
  }


  function renderCoachProfile(coach) {
    const coachName = coach.full_name || coach.name || "Coach";
    const displayName = document.getElementById("coachProfileTitle");
    const profileName = document.getElementById("coachProfileName");
    const profileEmail = document.getElementById("coachProfileEmail");
    const profilePhone = document.getElementById("coachProfilePhone");
    const avatar = document.getElementById("coachProfileAvatar");

    document.querySelectorAll(".coach-display-name").forEach(node => {
      node.textContent = coachName;
    });
    if (displayName) displayName.textContent = coachName;
    if (profileName) profileName.textContent = coachName;
    if (profileEmail) profileEmail.textContent = coach.email || "—";
    if (profilePhone) profilePhone.textContent = coach.contact_number || "—";
    if (avatar) {
      avatar.textContent = coachName.trim().split(/\s+/).slice(0, 2)
        .map(part => part[0]).join("").toUpperCase() || "C";
    }
  }

  function openCoachProfileEditor() {
    const coach = currentCoachProfile || {};
    document.getElementById("editCoachName").value = coach.full_name || coach.name || "";
    document.getElementById("editCoachEmail").value = coach.email || "";
    document.getElementById("editCoachPhone").value = coach.contact_number || "";
    document.getElementById("coachProfileEditForm").hidden = false;
    document.getElementById("coachProfileActions").hidden = true;
  }

  function closeCoachProfileEditor() {
    document.getElementById("coachProfileEditForm").hidden = true;
    document.getElementById("coachProfileActions").hidden = false;
  }

  function saveCoachProfileLocally(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;

    const name = document.getElementById("editCoachName").value.trim();
    const email = document.getElementById("editCoachEmail").value.trim();
    const phone = document.getElementById("editCoachPhone").value.trim();
    if (!name || !email) return;

    currentCoachProfile = {
      ...currentCoachProfile,
      name,
      full_name: name,
      email,
      contact_number: phone
    };
    renderCoachProfile(currentCoachProfile);
    closeCoachProfileEditor();
  }

  let coachRosterRefreshInFlight = false;

  async function refreshCoachRoster() {
    if (coachRosterRefreshInFlight || document.visibilityState === "hidden") return;

    // Do NOT refresh if the coach is actively filling in the attendance/assessment form.
    // Resetting would wipe unsaved attendance statuses and assessment values mid-entry.
    const attendanceSection = document.getElementById("attendance");
    const attendanceIsActive = attendanceSection?.classList.contains("active");
    if (attendanceIsActive) return;

    coachRosterRefreshInFlight = true;
    try {
      const response = await apiRequest("/api/coach/athletes");
      if (!Array.isArray(response?.athletes)) return;
      athletes = response.athletes.map(athlete => ({
        ...athlete,
        name: athlete.name || athlete.full_name,
        sports: athlete.sports || [],
        sport: (athlete.sports || []).join(", ")
      }));
      populateAthleteFilters();
      renderAthletes();
      updateDashboardStats();
      if (document.getElementById("attendance")?.classList.contains("active")) {
        await loadAttendance().catch(() => {});
      }
    } catch (error) {
      console.warn("Coach roster refresh failed:", error);
    } finally {
      coachRosterRefreshInFlight = false;
    }

    const coach = currentUser;
    const coachName = coach.full_name || coach.name || "Coach";

    document.querySelectorAll(".coach-display-name").forEach(node => {
      node.textContent = coachName;
    });
    document.getElementById("coachProfileTitle").textContent = coachName;
    document.getElementById("coachProfileName").textContent = coachName;
    document.getElementById("coachProfileEmail").textContent = coach.email || "—";
    document.getElementById("coachProfilePhone").textContent =
      coach.contact_number || "—";
    document.getElementById("coachProfileId").textContent =
      coach.id ? `COACH-${coach.id}` : "—";
    document.getElementById("coachProfileRoles").textContent =
      assignedSports.length
        ? assignedSports.map(sport => sport.name).join(", ")
        : "—";

    const initials = coachName
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map(part => part[0])
      .join("")
      .toUpperCase();

    document.getElementById("coachProfileAvatar").textContent =
      initials || "C";

    const select = document.getElementById("attendanceSport");

    if (select) {
      select.innerHTML = assignedSports
        .map(sport => `<option value="${sport.id}">${sport.name}</option>`)
        .join("");
    }

    populateAthleteFilters();
    await loadAttendance().catch(() => {});
    renderAthletes();
    updateDashboardStats();
  }

  function getToday() {
    const date = new Date();

    const localDate = new Date(
      date.getTime() - date.getTimezoneOffset() * 60000
    );

    return localDate.toISOString().split("T")[0];
  }

  // Guard: skip roster refresh on focus if the attendance/assessment section
  // is active — refreshCoachRoster calls loadAttendance which resets the form.
  window.addEventListener("focus", () => {
    const attendanceSection = document.getElementById("attendance");
    if (!attendanceSection?.classList.contains("active")) refreshCoachRoster();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      const attendanceSection = document.getElementById("attendance");
      if (!attendanceSection?.classList.contains("active")) refreshCoachRoster();
    }
  });

  // Poll every 30 seconds — but skip if the attendance section is active so we
  // never wipe unsaved assessment values while the coach is filling in the form.
  window.setInterval(() => {
    const attendanceSection = document.getElementById("attendance");
    const attendanceIsActive = attendanceSection?.classList.contains("active");
    if (!attendanceIsActive) {
      refreshCoachRoster();
    }
  }, 30000);

  function getInitials(name) {
    return name
      .split(" ")
      .map(word => word[0])
      .join("")
      .substring(0, 2)
      .toUpperCase();
  }

  function formatDate(date) {
    return new Date(date + "T00:00:00").toLocaleDateString(
      undefined,
      {
        day: "numeric",
        month: "short",
        year: "numeric"
      }
    );
  }

  function updateTopDate() {
    document.getElementById("topDate").textContent =
      new Date().toLocaleDateString(
        undefined,
        {
          weekday: "short",
          day: "numeric",
          month: "short",
          year: "numeric"
        }
      );
  }

  function showSection(sectionName, button) {
    document.querySelectorAll(".section").forEach(section => {
      section.classList.remove("active");
    });

    document.getElementById(sectionName).classList.add("active");

    document.querySelectorAll(".nav-button").forEach(button => {
      button.classList.remove("active");
    });

    if (button) {
      button.classList.add("active");
    }

    const titles = {
      dashboard: "Coach Dashboard",
      attendance: "Attendance",
      athletes: "My Athletes",
      announcements: "Announcements",
      events: "Events & Calendar",
      liveScores: "Live Scores",
      schedule: "Schedule",
      profile: "My Profile",
      settings: "Settings"
    };

    document.getElementById("pageTitle").textContent =
      titles[sectionName] || "Coach Dashboard";

    if (sectionName === "attendance") {
      loadAttendance();
    }

    if (sectionName === "schedule") {
      window.DashboardSchedule?.mount({
        root: "#schedule",
        role: "coach"
      });
    }

    if (sectionName === "athletes") {
      renderAthletes();
    }

    if (sectionName === "announcements") {
      mountCoachAnnouncements();
    }

    if (sectionName === "events") {
      mountCoachEvents();
    }

    if (sectionName === "liveScores") {
      loadCoachLiveScores();
    }

    closeSidebar();
  }

  function showSectionByName(sectionName) {
    const button = [
      ...document.querySelectorAll(".nav-button")
    ].find(btn =>
      btn.getAttribute("onclick") &&
      btn.getAttribute("onclick").includes(`'${sectionName}'`)
    );

    showSection(sectionName, button);
  }

  function escapeLiveScoreText(value) {
    return String(value ?? "").replace(/[&<>\"']/g, character => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '\"': "&quot;",
      "'": "&#39;"
    }[character]));
  }

  function formatLiveMatchDate(value) {
    if (!value) return "Date not set";
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime())
      ? String(value)
      : parsed.toLocaleString(undefined, {
          weekday: "short",
          day: "numeric",
          month: "short",
          year: "numeric",
          hour: "numeric",
          minute: "2-digit"
        });
  }

  async function loadCoachLiveScores() {
    const list = document.getElementById("coachLiveScoresList");
    if (!list) return;
    list.innerHTML = '<div class="announcement-empty">Loading fixtures and scores…</div>';

    try {
      const result = await apiRequest("/api/matches");
      const matches = Array.isArray(result.data) ? result.data : [];
      list.replaceChildren();

      if (!matches.length) {
        const empty = document.createElement("div");
        empty.className = "announcement-empty";
        empty.textContent = "No fixtures or scores have been published yet.";
        list.appendChild(empty);
        return;
      }

      matches.forEach(match => {
        const card = document.createElement("article");
        card.className = "coach-live-score-item";

        const header = document.createElement("div");
        header.className = "coach-live-score-meta";
        const event = document.createElement("strong");
        event.textContent = match.tournament || "Match fixture";
        const sport = document.createElement("span");
        sport.textContent = match.sport || "Sport not specified";
        const state = document.createElement("span");
        state.className = `coach-live-score-status${String(match.status || "").toLowerCase() === "live" ? " is-live" : ""}`;
        state.textContent = match.status || "Scheduled";
        header.append(event, sport, state);

        const score = document.createElement("div");
        score.className = "coach-live-score-board";
        const teamA = document.createElement("strong");
        teamA.textContent = match.team_a || "Team A";
        const scoreA = document.createElement("span");
        scoreA.className = "coach-live-score-number";
        scoreA.textContent = match.score_a == null ? "—" : String(match.score_a);
        const divider = document.createElement("span");
        divider.className = "coach-live-score-divider";
        divider.textContent = "–";
        const scoreB = document.createElement("span");
        scoreB.className = "coach-live-score-number";
        scoreB.textContent = match.score_b == null ? "—" : String(match.score_b);
        const teamB = document.createElement("strong");
        teamB.textContent = match.team_b || "Team B";
        score.append(teamA, scoreA, divider, scoreB, teamB);

        const details = document.createElement("div");
        details.className = "coach-live-score-details";
        const date = document.createElement("span");
        date.textContent = formatLiveMatchDate(match.match_date);
        const venue = document.createElement("span");
        venue.textContent = match.venue || "Venue not set";
        const category = document.createElement("span");
        category.textContent = [match.category, match.round_name].filter(Boolean).join(" · ");
        details.append(date, venue);
        if (category.textContent) details.appendChild(category);

        card.append(header, score, details);
        list.appendChild(card);
      });
    } catch (error) {
      list.replaceChildren();
      const message = document.createElement("div");
      message.className = "announcement-empty";
      message.textContent = error.message || "Live scores could not be loaded.";
      list.appendChild(message);
    }
  }

  async function loadAttendance() {
    try {
      if (!(await getCoachSession())) return;
    } catch (error) {
      if (/unauthorized|session|coach account|approved|disabled/i.test(error.message)) {
        if (window.APP_CONFIG?.AUTH_BYPASS !== false) return;
        window.location.replace("coach-login.html");
        return;
      }

      alert(error.message || "Could not verify coach access.");
      return;
    }

    const dateInput = document.getElementById("attendanceDate");

    if (!dateInput.value) {
      dateInput.value = getToday();
    }

    const sportId = document.getElementById("attendanceSport").value;
    if (!sportId) return;

    const selectedDate = dateInput.value;

    try {
      const query = new URLSearchParams({ sport_id: sportId });

      const [studentsData, recordsData] = await Promise.all([
        apiRequest(`/api/coach/attendance/students?${query}`),
        apiRequest(
          `/api/coach/attendance/records?${new URLSearchParams({
            sport_id: sportId,
            session_date: selectedDate
          })}`
        )
      ]);

      attendanceAthletes = studentsData.students.map(student => ({
        ...student,
        sport:
          assignedSports.find(sport => sport.id === Number(sportId))?.name || ""
      }));

      currentAttendance = Object.fromEntries(
        recordsData.records.map(record => [
          record.student_id,
          String(record.status || "").trim().toLowerCase()
        ])
      );

      attendanceAssessmentFields = [];
      attendanceAssessmentValues = {};
      expandedAttendanceAssessments = new Set();
      const assessmentStatus = document.getElementById("attendanceAssessmentStatus");
      assessmentStatus.hidden = true;
      assessmentStatus.textContent = "";
      try {
        const fieldsData = await apiRequest(
          `/api/coach/sports/${encodeURIComponent(sportId)}/assessment-fields`
        );
        attendanceAssessmentFields = fieldsData.fields || [];
        if (attendanceAssessmentFields.length) {
          const savedData = await apiRequest(
            `/api/coach/sport-assessments?${new URLSearchParams({
              sport_id: sportId,
              session_date: selectedDate
            })}`
          );
          attendanceAssessmentValues = Object.fromEntries(
            (savedData.assessments || []).map(assessment => [
              assessment.student_id,
              {
                values: assessment.values || {},
                remarks: assessment.remarks || ""
              }
            ])
          );
        }
      } catch (error) {
        attendanceAssessmentFields = [];
        attendanceAssessmentValues = {};
        assessmentStatus.textContent =
          `Assessment forms could not be loaded: ${error.message} Attendance can still be saved.`;
        assessmentStatus.hidden = false;
      }
    } catch (error) {
      alert(error.message);
      return;
    }

    renderAttendance();
    updateAttendanceSummary();
  }

  async function viewAttendanceHistory() {
    const dialog = document.getElementById("attendanceHistoryDialog");
    const sportSelect = document.getElementById("attendanceHistorySport");
    if (!dialog.open) dialog.showModal();
    const previousSport = sportSelect.value;
    populateAttendanceHistorySports();
    sportSelect.value = previousSport;
    await loadCoachAttendanceHistory();
  }

  function populateExtraSessionSportOptions() {
    const select = document.getElementById("extraSessionSport");
    if (!select) return;
    select.replaceChildren(new Option("Choose a sport", ""));
    assignedSports.forEach(sport => {
      select.appendChild(new Option(sport.name, sport.id));
    });
    const dateInput = document.getElementById("extraSessionDate");
    if (dateInput) {
      dateInput.min = getToday();
      if (!dateInput.value) dateInput.value = getToday();
    }
  }

  function populateAttendanceHistorySports() {
    const select = document.getElementById("attendanceHistorySport");
    if (!select) return;
    select.replaceChildren(new Option("All assigned sports", ""));
    assignedSports.forEach(sport => {
      select.appendChild(new Option(sport.name, sport.id));
    });
  }

  async function loadCoachAttendanceHistory() {
    const results = document.getElementById("coachAttendanceHistoryResults");
    const sportId = document.getElementById("attendanceHistorySport").value;
    const sessionDate = document.getElementById("attendanceHistoryDate").value;
    const query = new URLSearchParams();
    if (sportId) query.set("sport_id", sportId);
    if (sessionDate) query.set("session_date", sessionDate);
    results.textContent = "Loading attendance history…";

    try {
      const recordsData = await apiRequest(
        `/api/coach/attendance${query.toString() ? `?${query}` : ""}`
      );
      const records = recordsData.records || [];
      if (!records.length) {
        results.textContent = "No attendance history found for the selected filters.";
        return;
      }

      const sessions = new Map();
      records.forEach(record => {
        const key = `${record.session_date}|${record.sport_id}`;
        if (!sessions.has(key)) sessions.set(key, []);
        sessions.get(key).push(record);
      });

      results.replaceChildren();
      sessions.forEach(sessionRecords => {
        const first = sessionRecords[0];
        const article = document.createElement("article");
        article.className = "attendance-history-session";
        const heading = document.createElement("h3");
        heading.textContent = `${first.sport_name} · ${formatDate(first.session_date)}`;
        article.appendChild(heading);

        const table = document.createElement("table");
        table.className = "attendance-history-table";
        const head = table.createTHead().insertRow();
        ["Athlete", "Status"].forEach(label => {
          const cell = document.createElement("th");
          cell.textContent = label;
          head.appendChild(cell);
        });
        const body = table.createTBody();
        sessionRecords.forEach(record => {
          const row = body.insertRow();
          const athlete = row.insertCell();
          athlete.textContent = record.student_name || "Unknown athlete";
          const status = row.insertCell();
          const value = String(record.status || "unknown").toLowerCase();
          status.textContent = value.charAt(0).toUpperCase() + value.slice(1);
          status.className = `history-status status-${value}`;
        });
        article.appendChild(table);
        results.appendChild(article);
      });
    } catch (error) {
      results.textContent = `Attendance history could not be loaded: ${error.message}`;
    }
  }


  function renderAttendance() {
    const tableBody = document.getElementById("attendanceBody");
    tableBody.innerHTML = "";

    attendanceAthletes.forEach(athlete => {
      const status = String(currentAttendance[athlete.id] || "absent").trim().toLowerCase();
      const row = document.createElement("tr");
      const assessment = attendanceAssessmentValues[athlete.id] || { values: {}, remarks: "" };
      const canAssess = status === "present" || status === "late";
      const assessmentId = `attendance-assessment-${athlete.id}`;

      row.innerHTML = `
        <td>
          <div class="student">
            <div class="student-avatar">
              ${escapeAttendanceText(getInitials(athlete.name))}
            </div>
            <strong>${escapeAttendanceText(athlete.name)}</strong>
          </div>
        </td>
        <td>${escapeAttendanceText(athlete.sport)}</td>
        <td>
          <div class="status-buttons">
            <button
              class="present ${status === "present" ? "active" : ""}"
              aria-pressed="${status === "present"}"
              onclick="setAttendance(${athlete.id}, 'present')"
            >
              Present
            </button>
            <button
              class="absent ${status === "absent" ? "active" : ""}"
              aria-pressed="${status === "absent"}"
              onclick="setAttendance(${athlete.id}, 'absent')"
            >
              Absent
            </button>
            <button
              class="late ${status === "late" ? "active" : ""}"
              aria-pressed="${status === "late"}"
              onclick="setAttendance(${athlete.id}, 'late')"
            >
              Late
            </button>
            <button
              class="excused ${status === "excused" ? "active" : ""}"
              aria-pressed="${status === "excused"}"
              onclick="setAttendance(${athlete.id}, 'excused')"
            >
              Excused
            </button>
            ${attendanceAssessmentFields.length ? `
              <button
                type="button"
                class="assessment-toggle"
                aria-expanded="${expandedAttendanceAssessments.has(athlete.id)}"
                aria-controls="${assessmentId}"
                onclick="toggleAttendanceAssessment(${athlete.id})"
              >
                <i class="bi bi-chevron-down" aria-hidden="true"></i>
                Assessment
              </button>
            ` : ""}
          </div>
        </td>
      `;

      tableBody.appendChild(row);
      if (attendanceAssessmentFields.length) {
        const detailsRow = document.createElement("tr");
        detailsRow.className = "attendance-assessment-row";
        detailsRow.innerHTML = `
          <td colspan="3">
            <div id="${assessmentId}" class="attendance-assessment-form"
              ${expandedAttendanceAssessments.has(athlete.id) ? "" : "hidden"}
              aria-disabled="${!canAssess}">
              ${canAssess ? `
                <div class="attendance-assessment-fields">
                  ${attendanceAssessmentFields.map(field => `
                    <label class="attendance-assessment-field">
                      <span>${escapeAttendanceText(field.field_label)} (0-${escapeAttendanceText(field.max_score || 10)})</span>
                      <input
                        type="number"
                        min="0"
                        max="${escapeAttendanceText(field.max_score || 10)}"
                        step="0.1"
                        required
                        data-field-key="${escapeAttendanceText(field.field_key)}"
                        value="${escapeAttendanceText(assessment.values[field.field_key] ?? "")}"
                        aria-label="${escapeAttendanceText(field.field_label)} score for ${escapeAttendanceText(athlete.name)}"
                        oninput="updateAttendanceAssessmentValue(${athlete.id}, this.dataset.fieldKey, this.value)"
                      >
                    </label>
                  `).join("")}
                </div>
                <label class="attendance-assessment-field attendance-assessment-remarks">
                  <span>Coach feedback (optional)</span>
                  <textarea
                    rows="2"
                    aria-label="Coach feedback for ${escapeAttendanceText(athlete.name)}"
                    oninput="updateAttendanceAssessmentRemarks(${athlete.id}, this.value)"
                  >${escapeAttendanceText(assessment.remarks)}</textarea>
                </label>
              ` : `<p>Assessment is available only for students marked Present or Late.</p>`}
            </div>
          </td>
        `;
        tableBody.appendChild(detailsRow);
      }
    });
  }

  function escapeAttendanceText(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    }[character]));
  }

  function toggleAttendanceAssessment(athleteId) {
    if (expandedAttendanceAssessments.has(athleteId)) {
      expandedAttendanceAssessments.delete(athleteId);
    } else {
      expandedAttendanceAssessments.add(athleteId);
    }
    renderAttendance();
  }

  function updateAttendanceAssessmentValue(athleteId, fieldKey, value) {
    const assessment = attendanceAssessmentValues[athleteId] || { values: {}, remarks: "" };
    assessment.values[fieldKey] = value;
    attendanceAssessmentValues[athleteId] = assessment;
  }

  function updateAttendanceAssessmentRemarks(athleteId, remarks) {
    const assessment = attendanceAssessmentValues[athleteId] || { values: {}, remarks: "" };
    assessment.remarks = remarks;
    attendanceAssessmentValues[athleteId] = assessment;
  }

  function setAttendance(athleteId, status) {
    currentAttendance[athleteId] = status;
    if (status !== "present" && status !== "late") {
      delete attendanceAssessmentValues[athleteId];
      expandedAttendanceAssessments.delete(athleteId);
    }
    renderAttendance();
    updateAttendanceSummary();
  }

  function markAll(status) {
    attendanceAthletes.forEach(athlete => {
      currentAttendance[athlete.id] = status;
      if (status !== "present" && status !== "late") {
        delete attendanceAssessmentValues[athlete.id];
        expandedAttendanceAssessments.delete(athlete.id);
      }
    });

    renderAttendance();
    updateAttendanceSummary();
  }

  function updateAttendanceSummary() {
    const values = Object.values(currentAttendance);
    const present = values.filter(value => value === "present").length;
    const absent = values.filter(value => value === "absent").length;
    const late = values.filter(value => value === "late").length;
    const excused = values.filter(value => value === "excused").length;

    document.getElementById("presentCount").textContent = present;
    document.getElementById("absentCount").textContent = absent;
    document.getElementById("lateCount").textContent = late;
    document.getElementById("excusedCount").textContent = excused;
  }

  async function saveAttendance() {
    try {
      if (!(await getCoachSession())) return;
    } catch (error) {
      if (/unauthorized|session|coach account|approved|disabled/i.test(error.message)) {
        if (window.APP_CONFIG?.AUTH_BYPASS !== false) return;
        window.location.replace("coach-login.html");
        return;
      }

      alert(error.message || "Could not verify coach access.");
      return;
    }

    const date = document.getElementById("attendanceDate").value;

    if (!date) {
      alert("Please select an attendance date.");
      return;
    }

    const sportId = document.getElementById("attendanceSport").value;

    try {
      const records = attendanceAthletes.map(athlete => ({
        student_id: athlete.id,
        status: currentAttendance[athlete.id] || "absent"
      }));
      const body = {
        sport_id: Number(sportId),
        session_date: date,
        records
      };
      if (attendanceAssessmentFields.length) {
        const assessments = attendanceAthletes.map(athlete => {
          const status = currentAttendance[athlete.id] || "absent";
          const assessment = attendanceAssessmentValues[athlete.id] || { values: {}, remarks: "" };
          if (status === "present" || status === "late") {
            const missingField = attendanceAssessmentFields.find(field => {
              const value = assessment.values[field.field_key];
              return value === undefined || value === "" || !Number.isFinite(Number(value));
            });
            if (missingField) {
              expandedAttendanceAssessments.add(athlete.id);
              renderAttendance();
              throw new Error(
                `Complete ${missingField.field_label} for ${athlete.name} before saving attendance.`
              );
            }
          }
          return {
            student_id: athlete.id,
            attendance_status: status,
            values:
              status === "present" || status === "late"
                ? Object.fromEntries(
                    attendanceAssessmentFields.map(field => [
                      field.field_key,
                      Number(assessment.values[field.field_key])
                    ])
                  )
                : {},
            remarks: status === "present" || status === "late" ? assessment.remarks : ""
          };
        });
        body.assessments = assessments;
      }
      await apiRequest("/api/coach/attendance/records", {
        method: "POST",
        body: JSON.stringify(body)
      });

      await loadAttendance();
      alert(`Attendance saved for ${formatDate(date)}.`);
    } catch (error) {
      alert(error.message);
    }
  }

  function renderAthletes() {
    const grid = document.getElementById("athletesGrid");
    if (!grid) return;

    const selectedSport =
      document.getElementById("athleteSportFilter")?.value.trim().toLowerCase() || "";
    const selectedDepartment =
      document.getElementById("athleteDepartmentFilter")?.value.trim().toLowerCase() || "";
    const selectedSemester =
      document.getElementById("athleteSemesterFilter")?.value.trim().toLowerCase() || "";

    const normalizeSemester = value =>
      String(value ?? "").trim().replace(/^semester\s*/i, "").toLowerCase();

    const filteredAthletes = athletes.filter(athlete => {
      const sports = Array.isArray(athlete.sports)
        ? athlete.sports
        : String(athlete.sport || "").split(",");

      const matchesSport =
        !selectedSport ||
        sports.some(sport => String(sport).trim().toLowerCase() === selectedSport);

      const department = String(
        athlete.department || athlete.department_name || ""
      ).trim().toLowerCase();

      const semester = normalizeSemester(athlete.semester);

      return matchesSport &&
        (!selectedDepartment || department === selectedDepartment) &&
        (!selectedSemester || semester === selectedSemester);
    });

    grid.innerHTML = "";

    if (!filteredAthletes.length) {
      const emptyMessage = document.createElement("p");
      emptyMessage.className = "announcement-empty";
      emptyMessage.textContent = athletes.length
        ? "No athletes match the selected filters."
        : "No athletes are currently assigned to you.";
      grid.appendChild(emptyMessage);
      return;
    }

    filteredAthletes.forEach(athlete => {
      const card = document.createElement("div");
      card.className = "athlete-card";

      card.innerHTML = `
        <div class="athlete-header">
          <div class="athlete-avatar">
            ${getInitials(athlete.name)}
          </div>
          <div>
            <strong>${athlete.name}</strong>
            <span>${athlete.sport}</span>
          </div>
        </div>
        <div class="athlete-details">
          <div class="athlete-detail">
            <span>Email</span>
            <strong>${athlete.email || "Not provided"}</strong>
          </div>
        </div>
        <div class="athlete-record-actions">
          <button
            type="button"
            onclick="openRecordForm(${athlete.id}, 'goals')"
          >
            Goal
          </button>
          <button
            type="button"
            onclick="openRecordForm(${athlete.id}, 'feedback')"
          >
            Feedback
          </button>
        </div>
        <button
          class="view-athlete"
          onclick="viewAthlete(${athlete.id})"
        >
          View Athlete
        </button>
      `;

      grid.appendChild(card);
    });
  }

  function populateAthleteFilters() {
    const sportSelect = document.getElementById("athleteSportFilter");
    const departmentSelect = document.getElementById("athleteDepartmentFilter");
    const semesterSelect = document.getElementById("athleteSemesterFilter");

    if (!sportSelect || !departmentSelect || !semesterSelect) return;

    const uniqueValues = values =>
      [...new Map(
        values
          .map(value => String(value ?? "").trim())
          .filter(Boolean)
          .map(value => [value.toLowerCase(), value])
      ).values()].sort((a, b) => a.localeCompare(b));

    const fillSelect = (select, values, format = value => value) => {
      const previousValue = select.value;
      const allOption = select.options[0].cloneNode(true);
      select.replaceChildren(allOption);

      values.forEach(value => {
        select.appendChild(new Option(format(value), value));
      });

      if (values.includes(previousValue)) {
        select.value = previousValue;
      }
    };

    const sports = uniqueValues(
      athletes.flatMap(athlete =>
        Array.isArray(athlete.sports)
          ? athlete.sports
          : String(athlete.sport || "").split(",")
      )
    );

    const departments = uniqueValues(
      athletes.map(athlete => athlete.department || athlete.department_name)
    );

    const semesters = uniqueValues(
      athletes.map(athlete =>
        String(athlete.semester ?? "")
          .trim()
          .replace(/^semester\s*/i, "")
      )
    );

    fillSelect(sportSelect, sports);
    fillSelect(departmentSelect, departments);
    fillSelect(semesterSelect, semesters, value => `Semester ${value}`);
  }

  function resetAthleteFilters() {
    [
      "athleteSportFilter",
      "athleteDepartmentFilter",
      "athleteSemesterFilter"
    ].forEach(id => {
      const select = document.getElementById(id);
      if (select) select.value = "";
    });

    renderAthletes();
  }

  function setAthleteView(view) {
    const grid = document.getElementById("athletesGrid");
    const boxButton = document.getElementById("boxViewButton");
    const listButton = document.getElementById("listViewButton");

    if (view === "list") {
      grid.classList.add("list-view");
      listButton.classList.add("active");
      boxButton.classList.remove("active");
    } else {
      grid.classList.remove("list-view");
      boxButton.classList.add("active");
      listButton.classList.remove("active");
    }
  }

  function getAthleteAttendance(athleteId) {
    let total = 0;
    let present = 0;

    Object.values(attendanceRecords).forEach(record => {
      if (record[athleteId]) {
        total++;

        if (record[athleteId] === "present") {
          present++;
        }
      }
    });

    if (!total) {
      return 0;
    }

    return Math.round((present / total) * 100);
  }

  async function viewAthlete(athleteId) {
    const modal = document.getElementById("athleteDetailModal");
    const content = document.getElementById("athleteDetailContent");
    if (!modal || !content) return;

    modal.hidden = false;
    content.textContent = "Loading athlete profile…";

    const escapeHtml = value =>
      String(value ?? "Not provided").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[character]));
    const displayDate = value => {
      if (!value) return "Not recorded";
      const parsed = new Date(value);
      return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleDateString();
    };
    const valueLine = (label, value, suffix = "") =>
      `<span>${escapeHtml(label)}: ${escapeHtml(value)}${suffix}</span>`;
    try {
      const [profileResult, feedbackResult] =
        await Promise.allSettled([
          apiRequest(`/api/coach/athletes/${encodeURIComponent(athleteId)}`),
          apiRequest("/api/feedback")
        ]);

      if (profileResult.status !== "fulfilled") throw profileResult.reason;
      const athlete = profileResult.value.athlete;
      if (!athlete) throw new Error("Athlete profile was not returned.");

      const feedback = feedbackResult.status === "fulfilled" && Array.isArray(feedbackResult.value.data)
        ? feedbackResult.value.data
            .filter(record => String(record.student_id) === String(athlete.id))
            .sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")))
        : [];
      const attendanceRate = getAthleteAttendance(athlete.id);
      const sports = Array.isArray(athlete.sports) && athlete.sports.length
        ? athlete.sports.map(escapeHtml).join(", ")
        : escapeHtml(athlete.sport);
      const initials = String(athlete.name || "A")
        .trim().split(/\s+/).slice(0, 2).map(part => part[0] || "").join("").toUpperCase();

      const feedbackRows = feedback.slice(0, 3);

      content.innerHTML = `
        <div class="athlete-detail-eyebrow">ATHLETE PROFILE</div>
        <div class="athlete-profile-overview">
          <div class="athlete-profile-avatar" aria-hidden="true">${escapeHtml(initials || "A")}</div>
          <div>
            <h2 id="athleteDetailName">${escapeHtml(athlete.name)}</h2>
            <span>${sports} · ${escapeHtml(athlete.department)} · Semester ${escapeHtml(athlete.semester)}</span>
          </div>
        </div>

        <div class="athlete-detail-fields">
          <section class="athlete-detail-section">
            <span>Personal Information</span>
            <strong>
              ${valueLine("Full name", athlete.name)}
              ${valueLine("Gender", athlete.gender)}
              ${valueLine("Date of birth", displayDate(athlete.date_of_birth))}
              ${valueLine("Student number", athlete.student_number)}
            </strong>
          </section>
          <section class="athlete-detail-section">
            <span>Contact Information</span>
            <strong>
              ${valueLine("Email", athlete.email)}
              ${valueLine("Phone", athlete.contact_number)}
              ${valueLine("Emergency number", athlete.emergency_contact)}
            </strong>
          </section>
          <section class="athlete-detail-section">
            <span>Education</span>
            <strong>
              ${valueLine("Department", athlete.department)}
              ${valueLine("Semester", athlete.semester)}
            </strong>
          </section>
          <section class="athlete-detail-section">
            <span>Sports &amp; Fitness</span>
            <strong>
              ${valueLine("Sports", Array.isArray(athlete.sports) ? athlete.sports.join(", ") : athlete.sport)}
              ${valueLine("Height", athlete.height_cm, " cm")}
              ${valueLine("Weight", athlete.weight_kg, " kg")}
              ${valueLine("Fitness goal", athlete.goal)}
            </strong>
          </section>
          <section class="athlete-detail-section">
            <span>Bio</span>
            <strong>${escapeHtml(athlete.bio)}</strong>
          </section>

          <section class="athlete-detail-section athlete-attendance-panel">
            <span>Attendance Summary</span>
            <div class="athlete-attendance-summary">
              <div class="athlete-attendance-stat"><span>Attendance</span><strong>${escapeHtml(attendanceRate)}%</strong></div>
            </div>
          </section>
          <section class="athlete-detail-section">
            <span>Coach Feedback</span>
            ${feedbackRows.length
              ? `<div class="athlete-profile-records">${feedbackRows.map(record => `<article class="athlete-profile-record">
                  <strong>Coach feedback${record.rating == null ? "" : ` · ${escapeHtml(record.rating)} / 5`}</strong>
                  <span>${escapeHtml(displayDate(record.created_at))}</span>
                  <p>${escapeHtml(record.feedback)}</p>
                </article>`).join("")}</div>`
              : `<div class="athlete-detail-empty">No coach feedback has been recorded yet.</div>`}
          </section>
        </div>

        <div class="athlete-detail-actions">
          <button type="button" onclick="closeAthleteDetails(); openRecordForm(${Number(athlete.id)}, 'feedback')">Add feedback</button>
        </div>
      `;

      modal.querySelector(".athlete-detail-close")?.focus();
    } catch (error) {
      content.textContent = error.message || "Unable to load this athlete's profile.";
    }
  }
  function closeAthleteDetails() {
    const modal = document.getElementById("athleteDetailModal");
    if (modal) modal.hidden = true;
  }

  function updateDashboardStats() {
    document.getElementById("totalAthletes").textContent = athletes.length;

    document.getElementById("attendanceRate").textContent =
      `${attendanceSummary.percentage || 0}%`;

    document.getElementById("presentToday").textContent =
      attendanceSummary.present_today || 0;
  }

  function mountCoachAnnouncements() {
    const root = document.querySelector("#announcementsPanel");
    if (!root) return;

    if (!window.AnnouncementsPanel) {
      const list = root.querySelector("[data-announcement-list]");

      if (list) {
        list.innerHTML =
          '<div class="announcement-empty error">Announcements could not load. Refresh the page and try again.</div>';
      }

      return;
    }

    window.AnnouncementsPanel.mount({
      root,
      canManage: true
    });
  }

  let coachEventsMounted = false;

  function mountCoachEvents() {
    if (coachEventsMounted || !window.DashboardEvents) return;

    window.DashboardEvents.mount({
      root: "#dashboardEventsPanel",
      role: "coach"
    });

    coachEventsMounted = true;
  }

  async function logout() {
    await apiRequest("/api/logout", { method: "POST" }).catch(() => {});
    window.location.href = "coach-login.html";
  }

  function toggleSidebar() {
    document
      .getElementById("sidebar")
      .classList.toggle("open");
  }

  function closeSidebar() {
    document
      .getElementById("sidebar")
      .classList.remove("open");
  }

  document.getElementById("editCoachProfileButton")?.addEventListener("click", openCoachProfileEditor);
  document.getElementById("cancelCoachProfileEdit")?.addEventListener("click", closeCoachProfileEditor);
  document.getElementById("coachProfileEditForm")?.addEventListener("submit", saveCoachProfileLocally);

  document.getElementById("attendanceDate").value = getToday();
  document.getElementById("loadCoachAttendanceHistory").addEventListener(
    "click",
    loadCoachAttendanceHistory
  );
  document.getElementById("attendanceHistoryClose").addEventListener(
    "click",
    () => document.getElementById("attendanceHistoryDialog").close()
  );
  updateTopDate();
  initializeCoachDashboard();

  window.DashboardEvents?.mount({
    root: "#dashboardEventsPanel",
    role: "coach"
  });
