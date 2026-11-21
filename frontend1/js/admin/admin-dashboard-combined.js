
    // Mount the calendar before the dashboard's larger inline script runs, so
    // an unrelated dashboard error cannot leave the event form using GET.
    window.DashboardEvents?.mount({ root: "#dashboardEventsPanel", role: "admin" });
    const eventQuery = new URL(window.location.href);
    const eventFormKeys = ["title", "sport_id", "event_date", "venue", "description"];
    if (eventFormKeys.some((key) => eventQuery.searchParams.has(key))) {
      eventFormKeys.forEach((key) => eventQuery.searchParams.delete(key));
      window.history.replaceState({}, "", `${eventQuery.pathname}${eventQuery.search}${eventQuery.hash}`);
    }
  window.DashboardSchedule?.mount({ root: "#schedule", role: "admin" });

    /* =====================================================
       SPORTS / ROLES
    ===================================================== */

    const sports = [
      "Football",
      "Volleyball",
      "Basketball",
      "Badminton",
      "Cricket",
      "Kickboxing",
      "Athletics"
    ];


    /* =====================================================
       DATA STATE
    ===================================================== */

    let athletes = [];
    let deactivatedStudents = [];
    let deactivatedView = "box";
    let coachRequests = [];
    let approvedCoaches = [];
    let attendanceRecords = [];
    let dashboardStats = {};
    let sportOptions = [];


    /* =====================================================
       API HELPERS
    ===================================================== */

    function getAdminMock(url, options = {}) {
      if (url.includes("/api/admin/deactivated-students")) return { success: true, students: [] };
      if (url.includes("/session")) {
        return { authenticated: true, user: { id: 3, name: "Admin Manager", email: "admin@fittrack.com", role: "admin" } };
      }
      if (url.includes("/coaches")) {
        return {
          pending: [
            { id: 101, name: "David Miller", email: "david.m@fittrack.com", phone: "+1 555-0182", status: "pending", submitted_at: "2026-10-21" },
            { id: 102, name: "Elena Rostova", email: "elena.r@fittrack.com", phone: "+1 555-0199", status: "pending", submitted_at: "2026-10-20" }
          ],
          approved: [
            { id: 2, name: "Sarah Jenkins", email: "coach@fittrack.com", phone: "+1 555-0192", status: "approved" },
            { id: 4, name: "Marcus Vance", email: "marcus.v@fittrack.com", phone: "+1 555-0144", status: "approved" }
          ]
        };
      }
      if (url.includes("/students")) {
        return {
          students: [
            { id: 1, name: "Alex Morgan", email: "alex.morgan@fittrack.com", department: "Sports Science", semester: "4", sports: ["Athletics"], attendance_rate: 88, status: "Active" },
            { id: 2, name: "Jordan Lee", email: "jordan.lee@fittrack.com", department: "Physical Ed", semester: "6", sports: ["Football"], attendance_rate: 85, status: "Active" },
            { id: 3, name: "Sam Rivera", email: "sam.rivera@fittrack.com", department: "Kinesiology", semester: "2", sports: ["Badminton"], attendance_rate: 95, status: "Active" },
            { id: 4, name: "Taylor Swift", email: "taylor.s@fittrack.com", department: "Athletic Training", semester: "4", sports: ["Athletics"], attendance_rate: 78, status: "Active" }
          ]
        };
      }
      if (url.includes("/sports")) {
        return { sports: [{ id: 1, name: "Football" }, { id: 2, name: "Athletics" }, { id: 3, name: "Basketball" }, { id: 4, name: "Badminton" }] };
      }
      if (url.includes("/diagnostics")) {
        return { success: true, database: "Connected", status: "Healthy", api_version: "2.4.0", timestamp: new Date().toISOString() };
      }
      if (url.includes("/attendance")) {
        return { data: [], summary: { total_classes: 32, average_attendance: 87.4 } };
      }
      return { success: true, message: "Action recorded (preview mode)." };
    }

    async function requestJson(url, options = {}) {
      try {
        const response = await fetch(`${window.FITNESS_API_BASE || ""}${url}`, {
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          ...options
        });

        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
          const data = await response.json();
          if (response.ok) return data;
          if (response.status === 401 && window.APP_CONFIG?.AUTH_BYPASS !== false) {
            return getAdminMock(url, options);
          }
          if (response.status === 401) {
            window.location.replace("admin-login.html");
            return;
          }
          throw new Error(data.message || "Request failed.");
        }
      } catch (err) {
        if (window.APP_CONFIG?.AUTH_BYPASS !== false) {
          console.warn("API offline or bypass mode, returning mock admin data:", url);
          return getAdminMock(url, options);
        }
        throw err;
      }

      if (window.APP_CONFIG?.AUTH_BYPASS !== false) {
        return getAdminMock(url, options);
      }
      throw new Error("Unable to complete request.");
    }

    async function strictAdminJson(url, options = {}) {
      const response = await fetch(`${window.FITNESS_API_BASE || ""}${url}`, {
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        ...options
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.message || "Request failed.");
      return data;
    }

    function setAdminFeatureStatus(id, text, isError = false) {
      const element = document.getElementById(id);
      if (!element) return;
      element.textContent = text;
      element.hidden = !text;
      element.classList.toggle("error", isError);
    }

    async function loadAdminSports() {
      const grid = document.getElementById("adminSportsGrid");
      const count = document.getElementById("adminSportsCount");
      if (!grid) return;
      grid.innerHTML = `<div class="sports-loading-state"><i class="bi bi-arrow-repeat" style="font-size: 24px; animation: spin 1s linear infinite; display: inline-block;"></i><p style="margin-top: 8px;">Loading sports catalogue…</p></div>`;
      try {
        const [catRes, detRes, facRes] = await Promise.all([
          requestJson("/api/sports"),
          requestJson("/api/fit-track/sports"),
          requestJson("/api/fit-track/facilities")
        ]);
        const items = catRes?.sports ?? catRes?.data ?? [];
        const detailsById = new Map((detRes?.data ?? detRes?.sports ?? []).map((i) => [Number(i.id), i]));
        const mediaBySport = new Map();
        (facRes?.data ?? facRes?.facilities ?? []).forEach((m) => {
          const k = Number(m.sport_id);
          if (!mediaBySport.has(k)) mediaBySport.set(k, []);
          mediaBySport.get(k).push(m);
        });
        count.textContent = `${items.length} sport${items.length === 1 ? "" : "s"}`;
        
        if (!items.length) {
          grid.innerHTML = `<div class="sports-empty-card"><div class="sports-empty-icon"><i class="bi bi-trophy"></i></div><h3>No sports in catalogue</h3><p>Add your first campus sport using the "+ Add Sport" button above.</p></div>`;
          return;
        }

        grid.innerHTML = items.map((sport) => {
          const sid = Number(sport.id);
          const detail = detailsById.get(sid) || {};
          const media = mediaBySport.get(sid) || [];
          const venue = sport.venue || detail.venue || "Venue not set";
          const thumbs = media.map((item) => `<div class="sport-facility-thumb"><img src="${window.FITNESS_API_BASE || ""}/api/fit-track/facility-media/${encodeURIComponent(item.id)}/download" alt="${escapeHtml(item.caption || sport.name)}" onerror="this.parentElement.remove()"></div>`).join("");
          const initials = (sport.name || "S").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();

          return `<article class="sport-card" data-sport-id="${sid}">
            <div class="sport-card-top">
              <div class="sport-card-brand">
                <div class="sport-card-avatar">${initials}</div>
                <div class="sport-card-title-group">
                  <h3 class="sport-card-title" title="${escapeHtml(sport.name)}">${escapeHtml(sport.name)}</h3>
                  <span class="sport-card-venue" title="${escapeHtml(venue)}"><i class="bi bi-geo-alt-fill"></i> ${escapeHtml(venue)}</span>
                </div>
              </div>
              <div class="sport-card-actions" style="display: flex; gap: 6px; align-items: center;">
                <button class="sport-edit-btn" type="button"><i class="bi bi-pencil"></i> Edit</button>
                <button class="sport-delete-btn" type="button"><i class="bi bi-trash3"></i> Remove</button>
              </div>
            </div>
            <div class="sport-card-media-block">
              <div class="sport-media-header">
                <span class="sport-media-title"><i class="bi bi-images"></i> Facility Media</span>
                <span class="sport-media-count">${media.length} image${media.length === 1 ? "" : "s"}</span>
              </div>
              <div class="sport-facility-gallery">
                ${thumbs || `<span class="sport-media-empty"><i class="bi bi-camera"></i> No photos uploaded</span>`}
              </div>
            </div>
            <div class="sport-card-footer">
              <details class="sport-upload-accordion">
                <summary class="sport-upload-summary"><i class="bi bi-upload"></i> Upload Facility Photo</summary>
                <form class="sport-upload-form" data-sport-id="${sid}" enctype="multipart/form-data">
                  <div class="upload-input-wrap">
                    <input name="file" type="file" accept="image/png,image/jpeg,image/webp" required>
                  </div>
                  <div class="upload-input-wrap">
                    <input name="caption" maxlength="180" placeholder="Caption (optional)">
                  </div>
                  <button class="btn btn-secondary" type="submit" style="width: 100%; margin-top: 4px; padding: 6px; font-size: 11px;">Upload Photo</button>
                </form>
              </details>
            </div>
          </article>`;
        }).join("");

        grid.querySelectorAll(".sport-upload-form").forEach((form) => {
          form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = form.querySelector('button[type="submit"]');
            const fd = new FormData(form);
            btn.disabled = true;
            try {
              const res = await fetch(`${window.FITNESS_API_BASE || ""}/api/fit-track/facilities/${encodeURIComponent(form.dataset.sportId)}/media`, {
                method: "POST", credentials: "include", body: fd
              });
              const json = await res.json().catch(() => ({}));
              if (!res.ok || json.success === false) throw new Error(json.message || "Upload failed.");
              setAdminFeatureStatus("adminSportsStatus", "Facility photo uploaded.");
              await loadAdminSports();
            } catch (err) {
              setAdminFeatureStatus("adminSportsStatus", err.message || "Upload failed.", true);
            } finally {
              btn.disabled = false;
            }
          });
        });

        grid.querySelectorAll(".sport-edit-btn").forEach((btn) => {
          btn.addEventListener("click", (e) => {
            const card = e.currentTarget.closest(".sport-card");
            if (!card) return;
            const sid = Number(card.dataset.sportId);
            const name = card.querySelector(".sport-card-title")?.textContent || "";
            const venueEl = card.querySelector(".sport-card-venue");
            const venue = venueEl ? venueEl.textContent.replace(/[\r\n]/g, "").replace(/^\s*📍\s*/, "").trim() : "";
            openEditSportModal(sid, name, venue);
          });
        });

        grid.querySelectorAll(".sport-delete-btn").forEach((btn) => {
          btn.addEventListener("click", (e) => {
            const card = e.currentTarget.closest(".sport-card");
            if (!card) return;
            const sid = Number(card.dataset.sportId);
            const name = card.querySelector(".sport-card-title")?.textContent || "Sport";
            deleteAdminSport(sid, name);
          });
        });
      } catch (err) {
        count.textContent = "Error";
        grid.innerHTML = `<div class="sports-empty-card"><div class="sports-empty-icon" style="color:#dc2626;background:#fee2e2;"><i class="bi bi-exclamation-triangle"></i></div><h3>Error loading sports</h3><p>${escapeHtml(err.message || "Please refresh.")}</p></div>`;
        setAdminFeatureStatus("adminSportsStatus", err.message || "Could not load sports.", true);
      }
    }

    async function loadAdminMatches() {
      const body = document.getElementById("adminMatchesBody");
      const count = document.getElementById("adminMatchesCount");
      const tournamentSelect = document.getElementById("adminMatchTournament");
      const createButton = document.getElementById("adminCreateMatchButton");
      if (!body) return;
      const refreshButton = document.getElementById("adminMatchesRefresh");
      if (!body) return;
      if (refreshButton) {
        refreshButton.disabled = true;
        refreshButton.setAttribute("aria-busy", "true");
      }
      body.innerHTML = '<tr><td colspan="6">Loading fixtures…</td></tr>';
      try {
        const [matchesResponse, eventsResponse] = await Promise.all([
          requestJson("/api/matches"),
          requestJson("/api/tournaments")
        ]);
        const matches = matchesResponse?.data ?? matchesResponse?.matches ?? [];
        const events = eventsResponse?.data ?? eventsResponse?.tournaments ?? [];
        tournamentSelect.innerHTML = events.length
          ? '<option value="">Choose an event</option>' + events.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join("")
          : '<option value="">Create an event first</option>';
        createButton.disabled = events.length === 0;
        count.textContent = `${matches.length} fixture${matches.length === 1 ? "" : "s"}`;
        body.innerHTML = matches.length ? matches.map((match) => {
          const status = /live/i.test(match.status || "") ? "Live" : /complete/i.test(match.status || "") ? "Completed" : "Scheduled";
          return `<tr>
            <td><strong>${escapeHtml(match.tournament || "Event")}</strong><br><small>${escapeHtml(match.sport || "Sport")}</small></td>
            <td>${escapeHtml(match.team_a || "Team A")}<br><span>vs</span><br>${escapeHtml(match.team_b || "Team B")}</td>
            <td>${escapeHtml(match.match_date || "Date not set")}<br><small>${escapeHtml(match.venue || "Venue not set")}</small></td>
            <td><form class="admin-score-form" id="score-form-${escapeHtml(match.id)}" data-match-id="${escapeHtml(match.id)}"></form><div class="admin-feature-score-pair"><label class="visually-hidden" for="score-a-${escapeHtml(match.id)}">${escapeHtml(match.team_a)} score</label><input form="score-form-${escapeHtml(match.id)}" class="admin-match-score-input" id="score-a-${escapeHtml(match.id)}" name="score_a" type="number" min="0" step="1" value="${escapeHtml(match.score_a ?? 0)}" required><span>–</span><label class="visually-hidden" for="score-b-${escapeHtml(match.id)}">${escapeHtml(match.team_b)} score</label><input form="score-form-${escapeHtml(match.id)}" class="admin-match-score-input" id="score-b-${escapeHtml(match.id)}" name="score_b" type="number" min="0" step="1" value="${escapeHtml(match.score_b ?? 0)}" required></div></td>
            <td><select class="admin-match-status" name="status" form="score-form-${escapeHtml(match.id)}"><option ${status === "Scheduled" ? "selected" : ""}>Scheduled</option><option ${status === "Live" ? "selected" : ""}>Live</option><option ${status === "Completed" ? "selected" : ""}>Completed</option></select></td>
            <td><button class="btn btn-primary" form="score-form-${escapeHtml(match.id)}" type="submit">Save score</button></td>
          </tr>`;
        }).join("") : '<tr><td colspan="6">No fixtures yet. Create one above.</td></tr>';
        // Keep each row's score/status fields in one PATCH form without changing the API contract.
        body.querySelectorAll("tr").forEach((row) => {
          const scoreForm = row.querySelector(".admin-score-form");
          if (!scoreForm) return;
          row.querySelectorAll('[name="status"]').forEach((field) => field.setAttribute("form", scoreForm.id));
          row.querySelectorAll('button[form]').forEach((button) => button.setAttribute("form", scoreForm.id));
          row.querySelectorAll('input[name="score_a"], input[name="score_b"]').forEach((field) => field.setAttribute("form", scoreForm.id));
          scoreForm.addEventListener("submit", saveAdminMatchScore);
        });
        if (!events.length) setAdminFeatureStatus("adminMatchesStatus", "No events are available yet. Add an event in the Event section before creating a fixture.", true);
        else setAdminFeatureStatus("adminMatchesStatus", "");
      } catch (error) {
        count.textContent = "Could not load fixtures";
        body.innerHTML = '<tr><td colspan="6">Fixtures could not be loaded. Check the connection and refresh.</td></tr>';
        setAdminFeatureStatus("adminMatchesStatus", error.message || "Could not load fixtures.", true);
      } finally {
        if (refreshButton) {
          refreshButton.disabled = false;
          refreshButton.removeAttribute("aria-busy");
        }
      }
    }

    async function saveAdminMatchScore(event) {
      event.preventDefault();
      const form = event.currentTarget;
      const payload = Object.fromEntries(new FormData(form));
      const scoreInputs = Array.from(form.elements).filter((input) => input.name === "score_a" || input.name === "score_b");
      for (const input of scoreInputs) {
        if (!Number.isInteger(Number(input.value)) || Number(input.value) < 0) {
          setAdminFeatureStatus("adminMatchesStatus", "Scores must be whole numbers greater than or equal to zero.", true);
          input.focus();
          return;
        }
        payload[input.name] = Number(input.value);
      }
      try {
        await requestJson(`/api/matches/${encodeURIComponent(form.dataset.matchId)}`, {
          method: "PATCH",
          body: JSON.stringify(payload)
        });
        setAdminFeatureStatus("adminMatchesStatus", "Score updated.");
        await loadAdminMatches();
      } catch (error) {
        setAdminFeatureStatus("adminMatchesStatus", error.message || "Score could not be updated.", true);
      }
    }

    function defaultAssessmentLabels() {
      return ["", "", "", ""];
    }

    function renderAssessmentFields(labels) {
      const container = document.getElementById("dynamicAssessmentFields");
      if (!container) return;
      const values = Array.isArray(labels) && labels.length ? labels.slice(0, 8) : defaultAssessmentLabels();
      while (values.length < 4) values.push("");
      container.innerHTML = values.map((label, index) => {
        const removeButton = index >= 4
          ? `<button type="button" class="btn btn-secondary btn-sm" onclick="removeAssessmentField(this)" aria-label="Remove field" title="Remove field">−</button>`
          : "";
        return `<div class="assessment-field-row" style="display:flex; gap:6px; align-items:center;">
          <input type="text" placeholder="Field ${index + 1} Label" class="assessment-field-input" value="${escapeHtml(label || "")}" required style="flex:1;">
          ${removeButton}
        </div>`;
      }).join("");
    }

    function openAddSportModal() {
      const modal = document.getElementById("addSportModal");
      if (modal) {
        modal.classList.add("show");
        document.body.classList.add("popup-open");
        const form = document.getElementById("adminSportModalForm");
        if (form) {
          form.reset();
          delete form.dataset.sportId;
        }
        renderAssessmentFields(defaultAssessmentLabels());
        const title = document.getElementById("addSportModalTitle");
        if (title) title.textContent = "Add New Sport";
        const submitBtn = document.getElementById("modalSportSubmitBtn");
        if (submitBtn) submitBtn.innerHTML = '<i class="bi bi-plus-circle-fill"></i> Add Sport';
        setAdminFeatureStatus("modalSportStatus", "");
        document.getElementById("modalSportName")?.focus();
      }
    }

    async function loadSportAssessmentLabels(sportId) {
      const endpoints = [
        `/api/admin/sports/${encodeURIComponent(sportId)}/assessment-fields`,
        `/api/sports/${encodeURIComponent(sportId)}/assessment-fields`
      ];
      for (const endpoint of endpoints) {
        try {
          const result = await requestJson(endpoint);
          const fields = result.fields || result.data?.fields || result.assessment_fields || [];
          if (Array.isArray(fields) && fields.length) {
            return fields.map((field) => field.field_label || field.label || field.name || "").filter(Boolean);
          }
        } catch (error) {
          // Try the next endpoint; an empty form is the last fallback.
        }
      }
      return defaultAssessmentLabels();
    }

    async function openEditSportModal(sportId, sportName, venue) {
      const modal = document.getElementById("addSportModal");
      if (modal) {
        modal.classList.add("show");
        document.body.classList.add("popup-open");
        const form = document.getElementById("adminSportModalForm");
        if (form) {
          form.reset();
          form.dataset.sportId = sportId;
          const nameInput = document.getElementById("modalSportName");
          const venueInput = document.getElementById("modalSportVenue");
          if (nameInput) nameInput.value = sportName || "";
          if (venueInput) venueInput.value = venue === "Venue not set" ? "" : (venue || "");
        }
        renderAssessmentFields(defaultAssessmentLabels());
        const title = document.getElementById("addSportModalTitle");
        if (title) title.textContent = "Edit Sport";
        const submitBtn = document.getElementById("modalSportSubmitBtn");
        if (submitBtn) submitBtn.innerHTML = '<i class="bi bi-check-circle-fill"></i> Save Changes';
        setAdminFeatureStatus("modalSportStatus", "Loading saved assessment fields…");
        try {
          renderAssessmentFields(await loadSportAssessmentLabels(sportId));
          setAdminFeatureStatus("modalSportStatus", "");
        } catch (error) {
          setAdminFeatureStatus("modalSportStatus", "Saved assessment fields could not be loaded.", true);
        }
        document.getElementById("modalSportName")?.focus();
      }
    }

    function closeAddSportModal() {
      const modal = document.getElementById("addSportModal");
      if (modal) {
        modal.classList.remove("show");
        document.body.classList.remove("popup-open");
        const form = document.getElementById("adminSportModalForm");
        if (form) {
          form.reset();
          delete form.dataset.sportId;
        }
        setAdminFeatureStatus("modalSportStatus", "");
        renderAssessmentFields(defaultAssessmentLabels());
      }
    }

    function currentAssessmentLabels() {
      return Array.from(document.querySelectorAll("#dynamicAssessmentFields .assessment-field-input"))
        .map((input) => input.value);
    }

    function addAssessmentField() {
      const labels = currentAssessmentLabels();
      if (labels.length < 8) {
        labels.push("");
        renderAssessmentFields(labels);
      }
    }

    function removeAssessmentField(button) {
      const labels = currentAssessmentLabels();
      const row = button.closest(".assessment-field-row");
      const index = row ? Array.from(row.parentElement.children).indexOf(row) : -1;
      if (index < 4 || labels.length <= 4) return;
      labels.splice(index, 1);
      renderAssessmentFields(labels);
    }

    async function deleteAdminSport(sportId, sportName) {
      if (!confirm(`Are you sure you want to remove "${sportName}"? This will also remove associated facility media and session data.`)) {
        return;
      }
      try {
        let success = false;
        try {
          await requestJson(`/api/admin/sports/${encodeURIComponent(sportId)}`, { method: "DELETE" });
          success = true;
        } catch (e1) {
          try {
            await requestJson(`/api/fit-track/sports/${encodeURIComponent(sportId)}`, { method: "DELETE" });
            success = true;
          } catch (e2) {
            throw e1;
          }
        }
        setAdminFeatureStatus("adminSportsStatus", `Sport "${sportName}" removed successfully.`);
        await loadAdminSports();
      } catch (error) {
        setAdminFeatureStatus("adminSportsStatus", error.message || "Sport could not be removed.", true);
      }
    }

    async function saveAdminSport(event) {
      event.preventDefault();
      const form = event.currentTarget;
      const sportId = form.dataset.sportId;
      const submitBtn = document.getElementById("modalSportSubmitBtn");
      const payload = Object.fromEntries(new FormData(form));
      const fieldLabels = Array.from(document.querySelectorAll('.assessment-field-input')).map(input => input.value.trim()).filter(Boolean);
      if (fieldLabels.length > 0) {
        if (fieldLabels.length < 4 || fieldLabels.length > 8) {
          setAdminFeatureStatus("modalSportStatus", "Please provide between 4 and 8 assessment fields.", true);
          if (submitBtn) submitBtn.disabled = false;
          return;
        }
        payload.assessment_fields = fieldLabels.map((label, index) => ({
          field_key: label.toLowerCase().replace(/ /g, '_'),
          field_label: label,
          field_type: 'rating',
          max_score: 10,
          sort_order: index
        }));
      }

      ["name", "venue"].forEach((key) => {
        payload[key] = payload[key]?.trim() || null;
      });
      if (!payload.name) {
        setAdminFeatureStatus("modalSportStatus", "Sport name is required.", true);
        return;
      }
      if (submitBtn) submitBtn.disabled = true;
      try {
        if (sportId) {
          try {
            await requestJson(`/api/fit-track/sports/${encodeURIComponent(sportId)}`, {
              method: "PUT",
              body: JSON.stringify(payload)
            });
          } catch (e1) {
            await requestJson(`/api/admin/sports/${encodeURIComponent(sportId)}`, {
              method: "PUT",
              body: JSON.stringify(payload)
            });
          }
          setAdminFeatureStatus("modalSportStatus", "Sport updated successfully.");
        } else {
          try {
            await requestJson("/api/admin/sports", {
              method: "POST",
              body: JSON.stringify(payload)
            });
          } catch (e1) {
            await requestJson("/api/fit-track/sports", {
              method: "POST",
              body: JSON.stringify(payload)
            });
          }
          setAdminFeatureStatus("modalSportStatus", "Sport added successfully.");
        }
        form.reset();
        delete form.dataset.sportId;
        await loadAdminSports();
        setTimeout(() => {
          closeAddSportModal();
        }, 600);
      } catch (error) {
        setAdminFeatureStatus("modalSportStatus", error.message || "Sport could not be saved.", true);
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    }

    function bindAdminFeatureForms() {
      document.getElementById("adminSportModalForm")?.addEventListener("submit", saveAdminSport);

      document.getElementById("adminMatchForm")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const submit = document.getElementById("adminCreateMatchButton");
        const payload = Object.fromEntries(new FormData(form));
        ["round_name", "match_date", "venue"].forEach((key) => {
          payload[key] = payload[key]?.trim() || null;
        });
        submit.disabled = true;
        try {
          await requestJson("/api/matches", { method: "POST", body: JSON.stringify(payload) });
          form.reset();
          setAdminFeatureStatus("adminMatchesStatus", "Fixture created.");
          await loadAdminMatches();
        } catch (error) {
          setAdminFeatureStatus("adminMatchesStatus", error.message || "Fixture could not be created.", true);
        } finally {
          submit.disabled = !document.querySelector("#adminMatchTournament option[value]:not([value=''])");
        }
      });
    }

    bindAdminFeatureForms();


    function normalizeStudent(student) {

      return {
        id: student.id,
        name: student.full_name || "Unknown Student",
        phone: student.contact_number || "",
        emergency: "",
        email: student.email || "",
        isActive: student.is_active !== false && student.account_status !== "deactivated",
        sports: Array.isArray(student.sports)
          ? student.sports
          : String(student.sports || "").split(", ").filter(Boolean),
        isVerified: student.is_verified !== false,
        sport: Array.isArray(student.sports) && student.sports.length ? student.sports[0] : "",
        position: "",
        performance: 0
      };

    }


    function normalizeCoachRequest(coach) {

      return {
        id: coach.registration_id || coach.user_id || coach.id,
        registrationId: coach.registration_id,
        userId: coach.user_id,
        name: coach.full_name || coach.name || "Unnamed Coach",
        email: coach.email || "",
        phone: coach.contact_number || "",
        decisionAt: coach.decision_at || "",
        decisionReason: coach.decision_reason || "",
        requested: coach.created_at ? coach.created_at.split("T")[0] : "",
        status: (coach.coach_status || coach.status || "pending") === "pending_approval"
          ? "pending"
          : coach.coach_status || coach.status || "pending",
        roles: []
      };

    }


    function normalizeCoach(coach) {

      return {
        id: coach.id,
        name: coach.full_name || coach.name || "Unnamed Coach",
        email: coach.email || "",
        phone: coach.contact_number || "",
        decisionAt: coach.decision_at || "",
        decisionReason: coach.decision_reason || "",
        athleteCount: Number(coach.athlete_count || 0),
        active: coach.is_active !== false,
        coachStatus: coach.coach_status === "rejected" ? "declined" : (coach.coach_status || "approved"),
        roles: [],
        status: coach.coach_status || "approved"
      };

    }


    function normalizeAttendanceRecord(record) {

      return {
        athleteId: Number(record.student_id),
        studentName: record.student_name || "",
        studentEmail: record.email || "",
        coachId: record.coach_id ? Number(record.coach_id) : null,
        sportId: record.sport_id ? Number(record.sport_id) : null,
        sportName: record.sport_name || "",
        coach: record.coach_name || "Unknown Coach",
        date: record.session_date || record.date,
        status: (record.status || "").toLowerCase()
      };

    }

    function renderManualAttendanceEntryOptions() {
      const athleteSelect = document.getElementById("markAthlete");
      const coachSelect = document.getElementById("markCoach");
      const sportSelect = document.getElementById("markSport");
      if (!athleteSelect || !coachSelect || !sportSelect) return;
      athleteSelect.innerHTML = athletes.map(item => `<option value="${item.id}">${item.name} — ${item.email}</option>`).join("");
      coachSelect.innerHTML = approvedCoaches.filter(item => item.coachStatus === "approved").map(item => `<option value="${item.id}">${item.name}</option>`).join("");
      sportSelect.innerHTML = sportOptions.map(item => `<option value="${item.id}">${item.name}</option>`).join("");
    }

    async function loadAdminData() {

      try {

        const [studentsResponse, pendingResponse, coachesResponse, attendanceResponse, statsResponse, sportsResponse, assignmentsResponse, deactivatedResponse] =
          await Promise.all([
            requestJson("/api/admin/students").catch(() => ({ students: [] })),
            requestJson("/api/admin/coaches/pending").catch(() => ({ coaches: [] })),
            requestJson("/api/admin/coaches").catch(() => ({ coaches: [] })),
            requestJson("/api/admin/attendance").catch(() => ({ records: [] })),
            requestJson("/api/admin/dashboard-stats").catch(() => ({ stats: {} })),
            requestJson("/api/sports").catch(() => ({ sports: [] })),
            requestJson("/api/admin/coach-sports").catch(() => ({ assignments: [] })),
            requestJson("/api/admin/deactivated-students").catch(() => ({ students: [] }))
          ]);

        athletes = (studentsResponse.students || []).map(normalizeStudent);
        deactivatedStudents = (deactivatedResponse.students || []).map(student => ({
          id: Number(student.id), name: student.full_name || "Unknown Student",
          phone: student.contact_number || "", email: student.email || "",
          sport: (student.sports || []).join(", ") || student.sport_activity || "—",
          position: "—", isActive: false,
          studentId: student.passport_id || student.student_number || "—",
          deactivatedAt: student.deactivated_at || "—"
        }));

        coachRequests = (pendingResponse.coaches || []).map(normalizeCoachRequest);

        approvedCoaches = (coachesResponse.coaches || []).map(normalizeCoach);
        dashboardStats = statsResponse.stats || {};
        sportOptions = sportsResponse.sports || [];

        const assignmentsByCoach = new Map();
        (assignmentsResponse.assignments || []).forEach((assignment) => {
          const coachId = Number(assignment.coach_id);
          if (!assignmentsByCoach.has(coachId)) assignmentsByCoach.set(coachId, []);
          if (assignment.sport_name) assignmentsByCoach.get(coachId).push(assignment.sport_name);
        });
        approvedCoaches = approvedCoaches.map((coach) => ({
          ...coach,
          roles: assignmentsByCoach.get(Number(coach.id)) || coach.roles || []
        }));

        attendanceRecords = (attendanceResponse.records || []).map(normalizeAttendanceRecord);

        renderManualAttendanceEntryOptions();
        renderAdminAttendanceEntryOptions();

        updateDashboardStats();
        renderAthletes();
        renderDeactivatedStudents();
        renderCoachRequests();
        renderCoaches();
        renderAttendance();

      }
      catch (error) {

        console.warn("Admin dashboard data load failed:", error);

        athletes = [];
        deactivatedStudents = [];
        coachRequests = [];
        approvedCoaches = [];
        dashboardStats = {};
        attendanceRecords = [];

        updateDashboardStats();
        renderAthletes();
        renderDeactivatedStudents();
        renderCoachRequests();
        renderCoaches();
        renderAttendance();

      }

    }


    function setDiagnosticValue(id, value, state) {

      const element =
        document.getElementById(id);

      if (!element) return;

      element.textContent =
        value || "Unknown";

      element.classList.remove(
        "diagnostic-healthy",
        "diagnostic-warning",
        "diagnostic-error"
      );

      if (state) {
        element.classList.add(
          `diagnostic-${state}`
        );
      }

    }


    async function loadAdminDiagnostics() {

      const refreshButton =
        document.getElementById("diagnosticsRefresh");

      const errorMessage =
        document.getElementById("diagnosticsError");

      const requestId =
        document.getElementById("diagnosticRequestId");

      if (refreshButton) {
        refreshButton.disabled = true;
      }

      if (errorMessage) {
        errorMessage.hidden = true;
        errorMessage.textContent = "";
      }

      if (requestId) {
        requestId.textContent = "Unavailable";
      }

      try {

        const response =
          await fetch(
            `${window.FITNESS_API_BASE || ""}/api/admin/diagnostics`,
            {
              method: "GET",
              credentials: "include",
              headers: {
                "Accept": "application/json"
              }
            }
          );

        const payload =
          await response.json().catch(() => ({}));

        const correlationId =
          payload.request_id ||
          response.headers.get("X-Request-ID") ||
          "Unavailable";

        if (requestId) {
          requestId.textContent = correlationId;
        }

        if (!response.ok) {
          throw new Error(
            payload.message ||
            payload.error ||
            "Diagnostics could not be loaded."
          );
        }

        const checks =
          payload.checks || {};

        const renderStatus = (id, value) => {
          const normalized =
            String(value || "error").toLowerCase();
          const state =
            normalized === "ok" || normalized === "configured"
              ? "healthy"
              : normalized === "warning" || normalized === "not_configured"
                ? "warning"
                : "error";
          setDiagnosticValue(id, normalized.replaceAll("_", " "), state);
        };

        renderStatus("diagnosticBackend", checks.backend);
        renderStatus("diagnosticApi", checks.api);
        renderStatus("diagnosticDatabase", checks.database);
        renderStatus("diagnosticSupabase", checks.supabase_connectivity);
        renderStatus("diagnosticEmail", checks.email_service);
        renderStatus("diagnosticAuth", checks.authentication);
        renderStatus(
          "diagnosticEnvironment",
          checks.environment_configuration
        );

        const latency =
          document.getElementById("diagnosticLatency");

        if (latency) {
          latency.textContent =
            Number.isFinite(checks.database_latency_ms)
              ? `${checks.database_latency_ms} ms`
              : "Unavailable";

          latency.classList.remove(
            "diagnostic-healthy",
            "diagnostic-warning",
            "diagnostic-error"
          );

          latency.classList.add(
            Number.isFinite(checks.database_latency_ms) &&
              checks.database === "ok"
                ? "diagnostic-healthy"
                : "diagnostic-error"
          );
        }

        document.getElementById("diagnosticVersion").textContent =
          payload.version || "Unknown";

        document.getElementById("diagnosticDeployment").textContent =
          payload.deployment_environment || "Unknown";

        const checkedAt =
          payload.last_checked_at
            ? new Date(payload.last_checked_at)
            : null;

        document.getElementById("diagnosticLastChecked").textContent =
          checkedAt && !Number.isNaN(checkedAt.getTime())
            ? checkedAt.toLocaleString()
            : "Unknown";

      }
      catch (error) {

        setDiagnosticValue(
          "diagnosticBackend",
          "unavailable",
          "error"
        );

        [
          "diagnosticApi",
          "diagnosticDatabase",
          "diagnosticSupabase",
          "diagnosticEmail",
          "diagnosticAuth",
          "diagnosticEnvironment",
          "diagnosticLatency"
        ].forEach(id =>
          setDiagnosticValue(id, "unavailable", "error")
        );

        if (errorMessage) {
          errorMessage.textContent =
            error.message || "Diagnostics could not be loaded.";
          errorMessage.hidden = false;
        }

      }
      finally {

        if (refreshButton) {
          refreshButton.disabled = false;
        }

      }

    }


    /* =====================================================
       SAVE DATA
    ===================================================== */

    function saveAllData() {

      localStorage.setItem(
        "coachRequests",
        JSON.stringify(coachRequests)
      );

      localStorage.setItem(
        "approvedCoaches",
        JSON.stringify(approvedCoaches)
      );

      localStorage.setItem(
        "adminAttendance",
        JSON.stringify(attendanceRecords)
      );

    }


    /* =====================================================
       INITIALS
    ===================================================== */

    function getInitials(name) {

      return name
        .split(" ")
        .map(word => word[0])
        .join("")
        .substring(0, 2)
        .toUpperCase();

    }


    /* =====================================================
       DATE
    ===================================================== */

    function getToday() {

      const date = new Date();

      const localDate =
        new Date(
          date.getTime() -
          date.getTimezoneOffset() * 60000
        );

      return localDate
        .toISOString()
        .split("T")[0];

    }


    function formatDateDisplay(value) {

      if (!value) return "";

      const parts =
        value.split("-");

      if (parts.length !== 3) {
        return value;
      }

      return `${parts[2]}/${parts[1]}/${parts[0]}`;

    }


    function openDatePicker(id) {

      const picker =
        document.getElementById(id);

      if (!picker) return;

      if (
        typeof picker.showPicker ===
        "function"
      ) {

        picker.showPicker();

      } else {

        picker.click();

      }

    }


    function changeGlobalDate(value) {

      if (!value) return;

      const attendanceDate =
        document.getElementById(
          "adminAttendanceDate"
        );

      const display =
        document.getElementById(
          "globalDateDisplay"
        );

      const picker =
        document.getElementById(
          "globalDatePicker"
        );

      if (picker) {
        picker.value = value;
      }

      if (display) {

        display.value =
          formatDateDisplay(value);

      }

      if (attendanceDate) {

        attendanceDate.value =
          value;

        updateAttendanceDateDisplay();

        renderAttendance();

      }

    }


    function updateAttendanceDateDisplay() {

      const picker =
        document.getElementById(
          "adminAttendanceDate"
        );

      const display =
        document.getElementById(
          "adminAttendanceDateDisplay"
        );

      if (picker && display) {

        display.value =
          formatDateDisplay(
            picker.value
          );

      }

    }


    /* =====================================================
       NAVIGATION
    ===================================================== */

    function showSection(
      sectionName,
      button
    ) {

      const targetSection = document.getElementById(sectionName);
      if (!targetSection) {
        console.error(`Admin dashboard section not found: ${sectionName}`);
        return;
      }

      document
        .querySelectorAll(".section")
        .forEach(section =>
          section.classList.remove("active")
        );


      targetSection.classList.add("active");


      document
        .querySelectorAll(".nav-button")
        .forEach(btn =>
          btn.classList.remove("active")
        );


      if (button) {
        button.classList.add("active");
      }


      const titles = {

        dashboard: "Admin Dashboard",
        athletes: "Athletes",
        deactivatedStudents: "Deactivated Accounts",
        coaches: "Coaches",
        attendance: "Attendance",
        diagnostics: "System Diagnostics",
        announcements: "Announcements",
        events: "Event",
        schedule: "Schedule",
        sports: "Sports & Facilities",
        liveScores: "Live Scores",
        profile: "My Profile",
        settings: "Settings"

      };


      document.getElementById("pageTitle").textContent =
        titles[sectionName] || "Admin Dashboard";


      if (
        sectionName ===
        "athletes"
      ) {

        renderAthletes();

      }

      if (sectionName === "deactivatedStudents") renderDeactivatedStudents();


      if (
        sectionName ===
        "coaches"
      ) {

        loadAdminData();

        renderCoachRequests();

        renderCoaches();

      }


      if (
        sectionName ===
        "attendance"
      ) {

        renderAttendance();

      }

      if (sectionName === "schedule") {
      window.DashboardSchedule?.mount({ root: "#schedule", role: "admin" });
      }


      if (
        sectionName ===
        "diagnostics"
      ) {

        loadAdminDiagnostics();

      }


      if (
        sectionName ===
        "announcements"
      ) {

        mountAdminAnnouncements();

      }

      if (sectionName === "events") mountAdminEvents();
      if (sectionName === "sports") loadAdminSports();
      if (sectionName === "liveScores") loadAdminMatches();
      updateDashboardStats();

      closeSidebar();

    }


    function showSectionByName(
      sectionName
    ) {

      const button =
        [
          ...document.querySelectorAll(
            ".nav-button"
          )
        ].find(btn =>
          btn
            .getAttribute("onclick")
            ?.includes(
              `'${sectionName}'`
            )
        );


      showSection(
        sectionName,
        button
      );

    }


    /* =====================================================
       ATHLETE VIEW
    ===================================================== */

    let athleteView = "box";


    function setAthleteView(view) {

      athleteView =
        view;

      const grid =
        document.getElementById(
          "athletesGrid"
        );

      const boxButton =
        document.getElementById(
          "boxViewButton"
        );

      const listButton =
        document.getElementById(
          "listViewButton"
        );


      if (view === "list") {

        grid.classList.add(
          "list-view"
        );

        listButton.classList.add(
          "active"
        );

        boxButton.classList.remove(
          "active"
        );

      } else {

        grid.classList.remove(
          "list-view"
        );

        boxButton.classList.add(
          "active"
        );

        listButton.classList.remove(
          "active"
        );

      }

    }


    function renderAthletes() {

      const grid =
        document.getElementById(
          "athletesGrid"
        );


      const search =
        document
          .getElementById(
            "athleteSearch"
          )
          ?.value
          .toLowerCase()
          .trim() || "";


      const listedAthletes = [
        ...athletes,
        ...deactivatedStudents
      ];
      const filtered = listedAthletes.filter(athlete =>
        [athlete.name, athlete.sport, athlete.email, athlete.phone]
          .some(value => String(value || "").toLowerCase().includes(search))
      );


      grid.innerHTML = "";


      if (!filtered.length) {

        grid.innerHTML = `

          <div class="empty-athletes">

            <i class="bi bi-person-x"></i>

            <strong>
              No athletes found
            </strong>

            <span>
              There are no athletes matching your search.
            </span>

          </div>

        `;

        return;

      }


      filtered.forEach(
        athlete => {

          const card =
            document.createElement(
              "div"
            );


          card.className = `athlete-card${athlete.isActive === false ? " is-deactivated" : ""}`;

          const athleteId = Number(athlete.id);
          const profileButton = athlete.isActive === false
            ? `<button class="btn-neutral" onclick="viewDeactivatedStudent(${athleteId})"><i class="bi bi-eye"></i> View Profile</button>`
            : `<button class="btn-neutral" onclick="viewAthlete(${athleteId})"><i class="bi bi-eye"></i> View</button>`;
          const statusBadge = athlete.isActive === false
            ? '<span class="badge-custom badge-deactivated" role="status">Deactivated</span>'
            : "";
          const otherActions = athlete.isActive === false
            ? ""
            : `
              <button class="btn-neutral" type="button" disabled title="Edit action is not connected yet">
                <i class="bi bi-pencil-square"></i> Edit
              </button>
              <button class="btn-neutral" type="button" disabled title="Deactivate action is not connected yet">
                <i class="bi bi-person-slash"></i> Deactivate
              </button>
              <button class="remove-athlete-button" onclick="removeAthlete(${athleteId})">
                <i class="bi bi-trash3"></i> Remove
              </button>
            `;

          card.innerHTML = `

            <div class="athlete-header">

              <div class="athlete-avatar">

                ${escapeHtml(getInitials(athlete.name))}

              </div>


              <div>

                <strong>
                  ${escapeHtml(athlete.name)}
                </strong>

                <span>
                  ${escapeHtml(athlete.sport)}
                  •
                  ${escapeHtml(athlete.position)}
                </span>

              </div>

            </div>


            <div class="athlete-details">

              <div class="athlete-detail">

                <span>
                  Phone
                </span>

                <strong>
                  ${escapeHtml(athlete.phone || "Not available")}
                </strong>

              </div>


              <div class="athlete-detail">

                <span>
                  Email
                </span>

                <strong>
                  ${escapeHtml(athlete.email)}
                </strong>

              </div>

            </div>


            <div class="athlete-card-bottom">

              <span class="badge-custom badge-role">
                ${escapeHtml(athlete.sport)}
              </span>

              ${statusBadge}

              <div class="athlete-actions">

                ${profileButton}
                ${otherActions}

              </div>

            </div>

          `;


          grid.appendChild(card);

        }
      );


      setAthleteView(
        athleteView
      );

    }


    function setDeactivatedView(view) {
      deactivatedView = view;
      document.getElementById("deactivatedStudentsGrid")?.classList.toggle("list-view", view === "list");
      document.getElementById("deactivatedBoxButton")?.classList.toggle("active", view === "box");
      document.getElementById("deactivatedListButton")?.classList.toggle("active", view === "list");
    }

    function renderDeactivatedStudents() {
      const grid = document.getElementById("deactivatedStudentsGrid");
      if (!grid) return;
      const query = (document.getElementById("deactivatedSearch")?.value || "").trim().toLowerCase();
      const filtered = deactivatedStudents.filter(student =>
        [student.name, student.email, student.phone, student.sport, student.studentId].join(" ").toLowerCase().includes(query)
      );
      if (!filtered.length) {
        grid.innerHTML = '<div class="empty-athletes"><i class="bi bi-person-check"></i><strong>No deactivated accounts found</strong><span>Deactivated student accounts will appear here.</span></div>';
      } else {
        grid.innerHTML = filtered.map(student => `
          <article class="athlete-card"><div class="athlete-header"><div class="athlete-avatar">${escapeHtml(getInitials(student.name))}</div><div><strong>${escapeHtml(student.name)}</strong><span>${escapeHtml(student.sport)} · ${escapeHtml(student.studentId)}</span></div></div>
          <div class="athlete-details"><div class="athlete-detail"><span>Email</span><strong>${escapeHtml(student.email)}</strong></div><div class="athlete-detail"><span>Contact</span><strong>${escapeHtml(student.phone || "Not available")}</strong></div><div class="athlete-detail"><span>Status</span><strong>Deactivated</strong></div><div class="athlete-detail"><span>Deactivated on</span><strong>${escapeHtml(student.deactivatedAt)}</strong></div></div>
          <div class="athlete-card-bottom"><span class="badge-custom badge-role">Deactivated</span><div class="athlete-actions"><button class="btn-neutral" onclick="viewDeactivatedStudent(${student.id})"><i class="bi bi-eye"></i> View Profile</button><button class="btn-neutral" onclick="reactivateStudent(${student.id})"><i class="bi bi-person-check"></i> Reactivate</button></div></div></article>`).join("");
      }
      setDeactivatedView(deactivatedView);
    }

    async function deactivateStudent(id) {
      const athlete = athletes.find(item => Number(item.id) === Number(id));
      if (!athlete || !confirm(`Are you sure you want to deactivate ${athlete.name}'s account?`)) return;
      try {
        await strictAdminJson(`/api/admin/students/${id}/deactivate`, { method: "POST", body: "{}" });
        athletes = athletes.filter(item => Number(item.id) !== Number(id));
        alert(`${athlete.name}'s account was deactivated.`);
        await loadAdminData();
      } catch (error) {
        alert(error.message || "Student account could not be deactivated.");
      }
    }

    async function reactivateStudent(id) {
      const student = deactivatedStudents.find(item => Number(item.id) === Number(id));
      if (!student || !confirm("Are you sure you want to reactivate this student account?")) return;
      try {
        await strictAdminJson(`/api/admin/students/${id}/reactivate`, { method: "POST", body: "{}" });
        deactivatedStudents = deactivatedStudents.filter(item => Number(item.id) !== Number(id));
        alert(`${student.name}'s account was reactivated.`);
        await loadAdminData();
      } catch (error) {
        alert(error.message || "Student account could not be reactivated.");
      }
    }

    async function viewDeactivatedStudent(id) {
      const title = document.getElementById("deactivatedProfileTitle");
      const content = document.getElementById("deactivatedProfileContent");
      const dialog = document.getElementById("deactivatedProfileDialog");
      title.textContent = "Loading student history…";
      content.textContent = "";
      dialog.showModal();
      try {
        const result = await strictAdminJson(`/api/admin/deactivated-students/${id}`);
        title.textContent = result.student.full_name || "Student profile";
        content.innerHTML = `<h3>Profile details</h3><pre>${escapeHtml(JSON.stringify(result.student, null, 2))}</pre><h3>Historical records</h3>${Object.entries(result.history || {}).map(([group, rows]) => `<details open><summary>${escapeHtml(group.replaceAll("_", " "))} (${rows.length})</summary><pre>${escapeHtml(JSON.stringify(rows, null, 2))}</pre></details>`).join("")}`;
      } catch (error) {
        title.textContent = "Student history unavailable";
        content.textContent = error.message || "The profile could not be loaded.";
      }
    }

    function removeAthlete(id) {

      const athlete =
        athletes.find(
          athlete =>
            athlete.id === id
        );


      if (!athlete) return;


      const confirmed =
        confirm(
          `Are you sure you want to remove ${athlete.name} from the athletes list?`
        );


      if (!confirmed) return;


      athletes =
        athletes.filter(
          athlete =>
            athlete.id !== id
        );


      attendanceRecords =
        attendanceRecords.filter(
          record =>
            record.athleteId !== id
        );


      saveAllData();

      renderAthletes();

      renderAttendance();

      updateDashboardStats();

    }


    /* =====================================================
       ATHLETE INFORMATION POPUP
    ===================================================== */

    function viewAthlete(id) {

      const athlete =
        athletes.find(
          athlete =>
            athlete.id === id
        );


      if (!athlete) return;


      document.getElementById(
        "modalAthleteAvatar"
      ).textContent =
        getInitials(
          athlete.name
        );


      document.getElementById(
        "modalAthleteName"
      ).value =
        athlete.name;


      document.getElementById(
        "modalAthletePhone"
      ).value =
        athlete.phone ||
        "Not available";


      document.getElementById(
        "modalAthleteEmergency"
      ).value =
        athlete.emergency ||
        "Not available";


      document.getElementById(
        "modalAthleteEmail"
      ).value =
        athlete.email;


      document.getElementById(
        "modalAthleteSport"
      ).value =
        athlete.sport;


      document
        .getElementById(
          "athleteViewModal"
        )
        .classList.add("show");

    }


    function closeAthleteModal() {

      document
        .getElementById(
          "athleteViewModal"
        )
        .classList.remove("show");

    }


    /* =====================================================
       ROLE POPUP
    ===================================================== */

    let rolePopupType = "";

    let rolePopupId = null;


    function openRolePopup(
      type,
      id,
      selectedRoles
    ) {

      rolePopupType =
        type;

      rolePopupId =
        id;


      const overlay =
        document.getElementById(
          "rolePopupOverlay"
        );


      const options =
        document.getElementById(
          "rolePopupOptions"
        );


      const title =
        document.getElementById(
          "rolePopupTitle"
        );


      if (type === "request") {

        title.textContent =
          "Assign Coach Roles";

      } else {

        title.textContent =
          "Update Coach Roles";

      }


      options.innerHTML =
        "";


      const selected =
        Array.isArray(selectedRoles)
          ? [...selectedRoles]
          : [];


      /*
        Create all available roles.
      */

      sports.forEach(
        (sport, index) => {

          const label =
            document.createElement(
              "label"
            );


          label.className =
            "popup-role-option";


          label.setAttribute(
            "for",
            `role-${index}`
          );


          label.innerHTML = `

            <input
              type="checkbox"
              id="role-${index}"
              class="role-checkbox"
              value="${sport}"
              ${selected.includes(sport)
                ? "checked"
                : ""}
              onchange="updatePopupRoleCount()">


            <span class="popup-role-icon">

              <i class="bi bi-trophy-fill"></i>

            </span>


            <span class="popup-role-name">

              ${sport}

            </span>


            <span class="popup-role-check">

              <i class="bi bi-check-circle-fill"></i>

            </span>

          `;


          options.appendChild(
            label
          );

        }
      );


      updatePopupRoleCount();


      overlay.classList.add(
        "show"
      );

      document.body.classList.add(
        "popup-open"
      );

    }


    function updatePopupRoleCount() {

      const selected =
        document.querySelectorAll(
          "#rolePopupOptions input[type='checkbox']:checked"
        );


      const count =
        selected.length;


      document.getElementById(
        "rolePopupCount"
      ).textContent =
        `${count} role${count === 1 ? "" : "s"} selected`;

    }


    async function savePopupRoles() {

      const selected =
        [
          ...document.querySelectorAll(
            "#rolePopupOptions input[type='checkbox']:checked"
          )
        ].map(
          checkbox =>
            checkbox.value
        );


      if (selected.length === 0) {

        alert(
          "Please select at least one sport role."
        );

        return;

      }


      /* ================================================
         COACH SIGN-UP REQUEST
      ================================================= */

      if (
        rolePopupType ===
        "request"
      ) {

        const request =
          coachRequests.find(
            request =>
              request.id ===
              rolePopupId
          );


        if (request) {

          request.roles =
            [...selected];

        }

      }


      /* ================================================
         APPROVED COACH
      ================================================= */

      if (
        rolePopupType ===
        "coach"
      ) {

        const coach =
          approvedCoaches.find(
            coach =>
              coach.id ===
              rolePopupId
          );


        if (coach) {
          try {
            await requestJson(`/api/admin/coach-sports?coach_id=${coach.id}`, {
              method: "PUT",
              body: JSON.stringify({ coach_id: coach.id, sports: selected })
            });
            await loadAdminData();
          } catch (error) { alert(error.message || "Coach roles could not be saved."); return; }
        }

      }


      renderCoachRequests();


      closeRolePopup();


      renderCoaches();

      updateDashboardStats();

    }


    function closeRolePopup() {

      document
        .getElementById(
          "rolePopupOverlay"
        )
        .classList.remove(
          "show"
        );


      document.body.classList.remove(
        "popup-open"
      );


      rolePopupType =
        "";

      rolePopupId =
        null;

    }


    /* =====================================================
       APPROVE COACH
    ===================================================== */

    async function approveCoach(id) {

      const request =
        coachRequests.find(
          request =>
            request.id === id
        );


      if (!request) return;


      const roles =
        request.roles || [];


      if (roles.length === 0) {

        alert(
          "Please select at least one sport role before approving this coach."
        );

        return;

      }


      try {
        await requestJson(
          "/api/admin/coaches/approve",
          {
            method: "POST",
            body: JSON.stringify({
              registration_id: request.registrationId,
              user_id: request.userId,
              email: request.email,
              sports: roles
            })
          }
        );

        await loadAdminData();

        alert(
          `${request.name} has been approved with ${roles.length} role(s).`
        );
      } catch (error) {
        alert(error.message || "Coach approval failed.");
      }

    }


    /* =====================================================
       RENDER COACH REQUESTS
    ===================================================== */

    function renderCoachRequests() {

      const tbody =
        document.getElementById(
          "coachRequestsBody"
        );


      tbody.innerHTML =
        "";


      const pendingRequests =
        coachRequests.filter(
          request =>
            request.status ===
            "pending"
        );


      if (!pendingRequests.length) {

        tbody.innerHTML = `

          <tr>

            <td
              colspan="6"
              class="empty-table-message">

              <i class="bi bi-check-circle"></i>

              No pending coach requests.

            </td>

          </tr>

        `;

        return;

      }


      pendingRequests.forEach(
        request => {

          const row =
            document.createElement(
              "tr"
            );


          row.innerHTML = `

            <td>

              <div class="person">

                <div class="person-avatar">

                  ${getInitials(request.name)}

                </div>


                <div>

                  <strong>
                    ${request.name}
                  </strong>

                  <span>
                    ${request.phone || "Coach applicant"} · Requested ${request.requested || "recently"}
                  </span>

                </div>

              </div>

            </td>


            <td>
              ${request.email}
            </td>


            <td>
              ${formatDateDisplay(request.requested)}
            </td>


            <td>

              <button
                type="button"
                class="role-select-button"
                onclick='openRolePopup(
                  "request",
                  ${request.id},
                  ${JSON.stringify(request.roles || [])}
                )'>

                <span>

                  ${
                    request.roles &&
                    request.roles.length
                      ? request.roles.join(", ")
                      : "Select roles"
                  }

                </span>


                <i class="bi bi-chevron-down"></i>

              </button>

            </td>


            <td>

              <span
                class="badge-custom badge-pending">

                Pending

              </span>

            </td>


            <td>

              <div class="action-buttons">

                <button
                  class="btn-success-custom"
                  onclick="approveCoach(${request.id})">

                  <i class="bi bi-check-lg"></i>

                  Approve

                </button>

                <button class="btn-neutral" onclick="viewCoachRequest(${request.id})">View</button>


                <button
                  class="btn-danger-custom"
                  onclick="rejectCoach(${request.id})">

                  <i class="bi bi-x-lg"></i>

                  Decline

                </button>

              </div>

            </td>

          `;


          tbody.appendChild(
            row
          );

        }
      );

    }


    /* =====================================================
       REJECT COACH
    ===================================================== */

    async function rejectCoach(id) {

      const request =
        coachRequests.find(
          request =>
            request.id === id
        );


      if (!request) return;


      const reason = prompt("Reason for declining this application (optional):", "") || "";
      try {
        await requestJson(
          "/api/admin/coaches/reject",
          {
            method: "POST",
            body: JSON.stringify({
              registration_id: request.registrationId,
              user_id: request.userId,
              email: request.email,
              reason
            })
          }
        );

        await loadAdminData();
      } catch (error) {
        alert(error.message || "Coach rejection failed.");
      }

    }

    function viewCoachRequest(id) {
      const request = coachRequests.find(item => item.id === id);
      if (!request) return;
      alert(`${request.name}\n${request.email}\nPhone: ${request.phone || "—"}\nRequested: ${request.requested || "—"}`);
    }


    /* =====================================================
       RENDER APPROVED COACHES
    ===================================================== */

    function renderCoaches() {

      const tbody =
        document.getElementById(
          "coachesBody"
        );


      tbody.innerHTML =
        "";


      if (!approvedCoaches.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-table-message">No coaches registered.</td></tr>';
        return;
      }
      approvedCoaches.forEach(coach => {
        const row = document.createElement("tr");
        const roles = coach.roles || [];
        row.innerHTML = `<td><div class="person"><div class="person-avatar">${getInitials(coach.name)}</div><div><strong>${coach.name}</strong><span>${coach.phone || "Phone not provided"} · ${coach.athleteCount} athletes</span></div></div></td>
          <td>${coach.email}</td>
          <td><div class="coach-role-badges">${roles.map(role => `<span class="badge-custom badge-role">${role}</span>`).join("")}</div>${coach.decisionAt ? `<small>Decision ${coach.decisionAt.split("T")[0]}${coach.decisionReason ? ` · ${coach.decisionReason}` : ""}</small>` : ""}</td>
          <td><span class="badge-custom ${coach.coachStatus === "approved" && coach.active ? "badge-approved" : "badge-pending"}">${coach.coachStatus === "approved" ? (coach.active ? "Active" : "Inactive") : capitalize(coach.coachStatus)}</span></td>
          <td>${coach.coachStatus === "approved" ? `<button type="button" class="role-select-button" onclick='openRolePopup("coach", ${coach.id}, ${JSON.stringify(roles)})'>Update Roles</button>` : "—"}</td>
          <td>${coach.coachStatus === "approved" ? `<button class="remove-coach-button" onclick="setCoachActive(${coach.id}, ${!coach.active})">${coach.active ? "Deactivate" : "Activate"}</button>` : "—"}</td>`;
        tbody.appendChild(row);
      });

    }


    /* =====================================================
       REMOVE COACH
    ===================================================== */

    function removeCoach(id) {

      const coach =
        approvedCoaches.find(
          coach =>
            coach.id === id
        );


      if (!coach) return;


      const confirmed =
        confirm(
          `Are you sure you want to remove ${coach.name} from the approved coaches?`
        );


      if (!confirmed) return;


      approvedCoaches =
        approvedCoaches.filter(
          coach =>
            coach.id !== id
        );


      saveAllData();


      renderCoaches();

      updateDashboardStats();

    }

    async function setCoachActive(id, active) {
      try {
        await requestJson(`/api/admin/coaches/${id}/active`, { method: "PUT", body: JSON.stringify({ active }) });
        await loadAdminData();
      } catch (error) { alert(error.message || "Coach status could not be changed."); }
    }

    /* =====================================================
       ATTENDANCE
    ===================================================== */

    function renderAdminAttendanceEntryOptions() {

      const sportSelect = document.getElementById("attendanceSport");
      if (!sportSelect) return;

      const currentValue = sportSelect.value || "all";

      const apiSports = Array.isArray(sportOptions) ? sportOptions : [];

      const fallbackSports = [
        ...new Map(
          attendanceRecords
            .filter(record => record.sportId && record.sportName)
            .map(record => [
              String(record.sportId),
              { id: record.sportId, name: record.sportName }
            ])
        ).values()
      ];

      const sports = apiSports.length ? apiSports : fallbackSports;

      sportSelect.innerHTML = `
        <option value="all">All Sports</option>
        ${sports.map(sport => `
          <option value="${sport.id}">
            ${escapeHtml(sport.name || "Sport")}
          </option>
        `).join("")}
      `;

      if ([...sportSelect.options].some(option => option.value === currentValue)) {
        sportSelect.value = currentValue;
      } else {
        sportSelect.value = "all";
      }

    }


    function getSelectedAttendanceRecords() {

      const selectedDate =
        document.getElementById("adminAttendanceDate")?.value || getToday();

      const selectedSport =
        document.getElementById("attendanceSport")?.value || "all";

      return attendanceRecords.filter(record => {

        const dateMatches = record.date === selectedDate;
        const sportMatches =
          selectedSport === "all" ||
          String(record.sportId) === String(selectedSport);

        return dateMatches && sportMatches &&
          (record.status === "present" || record.status === "absent");

      });

    }


    function getStudentOverallAttendance(athleteId, sportId) {

      const studentRecords = attendanceRecords.filter(record => {

        if (Number(record.athleteId) !== Number(athleteId)) return false;

        if (sportId && String(sportId) !== "all") {
          if (Number(record.sportId) !== Number(sportId)) return false;
        }

        return ["present", "absent", "late", "excused"].includes(record.status);

      });

      if (!studentRecords.length) return 0;

      const excused = studentRecords.filter(record => record.status === "excused").length;
      const eligible = studentRecords.length - excused;
      const attended = studentRecords.filter(
        record => record.status === "present" || record.status === "late"
      ).length;

      return eligible ? Math.round((attended / eligible) * 100) : 0;

    }


    function getStudentNameForAttendance(record) {

      if (record.studentName) return record.studentName;

      const athlete = athletes.find(
        item => Number(item.id) === Number(record.athleteId)
      );

      return athlete?.name || "Student";

    }


    function getStudentEmailForAttendance(record) {

      if (record.studentEmail) return record.studentEmail;

      const athlete = athletes.find(
        item => Number(item.id) === Number(record.athleteId)
      );

      return athlete?.email || "";

    }


    function escapeHtml(value) {

      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

    }


    function updateAttendanceSummary(records) {

      const validRecords = records.filter(
        record => ["present", "absent", "late", "excused"].includes(record.status)
      );

      const present =
        validRecords.filter(record => record.status === "present").length;

      const absent =
        validRecords.filter(record => record.status === "absent").length;

      const late =
        validRecords.filter(record => record.status === "late").length;

      const excused =
        validRecords.filter(record => record.status === "excused").length;

      const total = present + absent + late + excused;
      const eligible = total - excused;
      const percentage =
        eligible ? Math.round(((present + late) / eligible) * 100) : 0;

      const percentElement =
        document.getElementById("attendanceOverallPercent");

      const presentElement =
        document.getElementById("attendancePresentCount");

      const absentElement =
        document.getElementById("attendanceAbsentCount");

      const lateElement =
        document.getElementById("attendanceLateCount");

      const excusedElement =
        document.getElementById("attendanceExcusedCount");

      const totalElement =
        document.getElementById("attendanceTotalCount");

      const donut =
        document.getElementById("attendanceDonut");

      if (percentElement) percentElement.textContent = `${percentage}%`;
      if (presentElement) presentElement.textContent = present;
      if (absentElement) absentElement.textContent = absent;
      if (lateElement) lateElement.textContent = late;
      if (excusedElement) excusedElement.textContent = excused;
      if (totalElement) totalElement.textContent = total;

      if (donut) {
        donut.style.setProperty("--attendance-percent", `${percentage}%`);
      }

    }


    function renderAttendanceProgress(records) {

      const container =
        document.getElementById("attendanceProgressList");

      if (!container) return;

      const sportId =
        document.getElementById("attendanceSport")?.value || "all";

      const students = [];
      const seen = new Set();

      records.forEach(record => {

        if (seen.has(record.athleteId)) return;

        seen.add(record.athleteId);

        students.push({
          id: record.athleteId,
          name: getStudentNameForAttendance(record),
          percentage: getStudentOverallAttendance(record.athleteId, sportId)
        });

      });

      students.sort((a, b) => a.name.localeCompare(b.name));

      if (!students.length) {
        container.innerHTML = `
          <div class="attendance-progress-empty">
            No student attendance records available.
          </div>
        `;
        return;
      }

      container.innerHTML = students.map(student => {

        const percentage = Math.max(0, Math.min(100, student.percentage));

        return `
          <div class="attendance-progress-row">
            <div class="attendance-progress-label">
              <span>${escapeHtml(student.name)}</span>
              <strong>${percentage}%</strong>
            </div>
            <div class="attendance-progress-track">
              <span style="width:${percentage}%"></span>
            </div>
          </div>
        `;

      }).join("");

    }


    function renderAttendance() {

      const dateInput =
        document.getElementById("adminAttendanceDate");

      if (!dateInput) return;

      if (!dateInput.value) {
        dateInput.value = getToday();
      }

      updateAttendanceDateDisplay();

      const selectedDate = dateInput.value;

      const sportFilter =
        document.getElementById("attendanceSport")?.value || "all";

      const selectedSport =
        sportOptions.find(
          sport => String(sport.id) === String(sportFilter)
        );

      const selectedSportName =
        sportFilter === "all"
          ? "All Sports"
          : (selectedSport?.name || "Selected Sport");

      const dateLabel =
        document.getElementById("attendanceSelectedDate");

      const sportLabel =
        document.getElementById("attendanceSelectedSport");

      if (dateLabel) {
        dateLabel.textContent = formatDateDisplay(selectedDate);
      }

      if (sportLabel) {
        sportLabel.textContent = selectedSportName;
      }

      const tbody =
        document.getElementById("attendanceBody");

      if (!tbody) return;

      const allSelectedDateRecords =
        attendanceRecords.filter(record => {

          if (record.date !== selectedDate) return false;

          return sportFilter === "all" ||
            String(record.sportId) === String(sportFilter);

        });

      // For a specific sport, include every verified student enrolled in
      // that sport, even when nobody has been marked for this date yet.
      let records = allSelectedDateRecords;
      if (sportFilter !== "all") {
        const rosterSport = selectedSport?.name;
        const existingByStudent = new Map(
          allSelectedDateRecords.map(record => [Number(record.athleteId), record])
        );
        records = athletes
          .filter(student => student.isVerified && (student.sports || []).includes(rosterSport))
          .map(student => {
            const existing = existingByStudent.get(Number(student.id));
            return {
              athleteId: Number(student.id),
              studentName: student.name,
              studentEmail: student.email,
              coachId: existing?.coachId || null,
              sportId: Number(sportFilter),
              sportName: rosterSport,
              date: selectedDate,
              status: existing?.status || "unmarked"
            };
          });
      }

      updateAttendanceSummary(allSelectedDateRecords);
      renderAttendanceProgress(allSelectedDateRecords);

      tbody.innerHTML = "";

      const selectAll =
        document.getElementById("attendanceSelectAll");

      if (selectAll) selectAll.checked = false;

      if (!records.length) {

        tbody.innerHTML = `
          <tr>
            <td colspan="6" class="attendance-empty-cell">
              <i class="bi bi-calendar-x"></i>
              <strong>${sportFilter === "all" ? "Choose a sport to mark attendance" : "No students are enrolled in this sport"}</strong>
              <span>${sportFilter === "all" ? "Select a specific sport above to load its student roster." : "Only verified students enrolled in the selected sport are listed."}</span>
            </td>
          </tr>
        `;

        return;

      }

      records
        .sort((a, b) =>
          getStudentNameForAttendance(a)
            .localeCompare(getStudentNameForAttendance(b))
        )
        .forEach((record, index) => {

          const studentName = getStudentNameForAttendance(record);
          const studentEmail = getStudentEmailForAttendance(record);

          const statusStyles = {
            present: ["attendance-present-pill", "bi-check-circle-fill", "Present"],
            absent: ["attendance-absent-pill", "bi-x-circle-fill", "Absent"],
            late: ["attendance-late-pill", "bi-clock-fill", "Late"],
            excused: ["attendance-excused-pill", "bi-info-circle-fill", "Excused"],
            unmarked: ["attendance-unmarked-pill", "bi-dash-circle", "Not marked"]
          };
          const [statusClass, statusIcon, statusLabel] = statusStyles[record.status] || statusStyles.unmarked;

          const overall =
            getStudentOverallAttendance(
              record.athleteId,
              record.sportId
            );

          const row = document.createElement("tr");

          row.dataset.studentId = record.athleteId;
          row.dataset.attendanceDate = record.date;
          row.dataset.sportId = record.sportId || "";

          row.innerHTML = `
            <td class="attendance-check-col">
              <input
                type="checkbox"
                class="attendance-row-check"
                data-student-id="${record.athleteId}"
                aria-label="Select ${escapeHtml(studentName)}">
            </td>

            <td class="attendance-no-col">${index + 1}</td>

            <td>
              <div class="attendance-student-name">
                <div class="attendance-student-avatar">
                  ${escapeHtml(getInitials(studentName))}
                </div>
                <div>
                  <strong>${escapeHtml(studentName)}</strong>
                  <span>${escapeHtml(studentEmail || "Student")}</span>
                </div>
              </div>
            </td>

            <td class="attendance-status-cell">
              <span class="${statusClass}">
                <i class="bi ${statusIcon}"></i>
                ${statusLabel}
              </span>
            </td>

            <td>
              <div class="attendance-row-overall">
                <div class="attendance-row-percent">${overall}%</div>
                <div class="attendance-row-track">
                  <span style="width:${overall}%"></span>
                </div>
              </div>
            </td>

            <td>
              <button
                type="button"
                class="attendance-edit-button"
                ${record.status !== "unmarked" ? `onclick="editAttendance(${record.athleteId}, '${record.date}', ${record.sportId || 0}, this)"` : "disabled"}>
                <i class="bi bi-pencil"></i>
                Edit
              </button>
            </td>
          `;

          tbody.appendChild(row);

        });

    }


    function toggleAllAttendanceRows(checked) {

      document
        .querySelectorAll(".attendance-row-check")
        .forEach(input => {
          input.checked = checked;
        });

    }


    async function saveAdminAttendance() {

      const selectedDate =
        document.getElementById("adminAttendanceDate")?.value || getToday();

      const sportFilter =
        document.getElementById("attendanceSport")?.value || "all";

      const status =
        document.getElementById("attendanceStatusFilter")?.value || "present";

      if (sportFilter === "all") {
        alert("Choose a specific sport before marking attendance.");
        return;
      }

      const selectedIds = [
        ...document.querySelectorAll(".attendance-row-check:checked")
      ].map(input => Number(input.dataset.studentId));

      const selectedSet = new Set(selectedIds);
      const rosterRows = [
        ...document.querySelectorAll("#attendanceBody tr[data-student-id]")
      ];
      const recordsToSave = rosterRows
        .filter(row => !selectedSet.size || selectedSet.has(Number(row.dataset.studentId)))
        .map(row => ({ student_id: Number(row.dataset.studentId), status }));

      if (!recordsToSave.length) {

        alert(
          "There are no enrolled students to mark for the selected sport."
        );

        return;

      }

      if (
        !confirm(
          `Mark ${recordsToSave.length} student${recordsToSave.length === 1 ? "" : "s"} as ${capitalize(status)} for ${formatDateDisplay(selectedDate)}?`
        )
      ) {
        return;
      }

      try {
        await requestJson("/api/admin/attendance", {
          method: "POST",
          body: JSON.stringify({
            sport_id: Number(sportFilter),
            session_date: selectedDate,
            records: recordsToSave
          })
        });

        await loadAdminData();
        alert(`Attendance saved for ${recordsToSave.length} student${recordsToSave.length === 1 ? "" : "s"}.`);

      } catch (error) {

        alert(
          error.message ||
          "Attendance could not be saved."
        );

      }

    }


    async function editAttendance(athleteId, date, sportId, button) {

      const record =
        attendanceRecords.find(item =>
          Number(item.athleteId) === Number(athleteId) &&
          item.date === date &&
          Number(item.sportId) === Number(sportId)
        );

      if (!record || !button) return;

      const row =
        button.closest("tr");

      const statusCell =
        row?.querySelector(".attendance-status-cell");

      const actionCell =
        button.parentElement;

      if (!statusCell || !actionCell) return;

      statusCell.innerHTML = `
        <select
          class="attendance-inline-select"
          aria-label="Attendance for ${escapeHtml(getStudentNameForAttendance(record))}">
          <option value="present" ${record.status === "present" ? "selected" : ""}>Present</option>
          <option value="absent" ${record.status === "absent" ? "selected" : ""}>Absent</option>
          <option value="late" ${record.status === "late" ? "selected" : ""}>Late</option>
          <option value="excused" ${record.status === "excused" ? "selected" : ""}>Excused</option>
        </select>
      `;

      actionCell.innerHTML = `
        <button type="button" class="attendance-save-button">
          <i class="bi bi-check2"></i>
          Save
        </button>
        <button type="button" class="attendance-cancel-button">
          Cancel
        </button>
      `;

      const select =
        statusCell.querySelector(".attendance-inline-select");

      const saveButton =
        actionCell.querySelector(".attendance-save-button");

      const cancelButton =
        actionCell.querySelector(".attendance-cancel-button");

      cancelButton.addEventListener(
        "click",
        () => renderAttendance()
      );

      saveButton.addEventListener(
        "click",
        async () => {

          const nextStatus = select.value;

          if (!["present", "absent", "late", "excused"].includes(nextStatus)) {
            alert("Choose Present, Absent, Late, or Excused.");
            return;
          }

          if (!record.coachId || !record.sportId) {
            alert(
              "This attendance record is missing its assigned coach or sport."
            );
            return;
          }

          try {

            saveButton.disabled = true;

            await requestJson(
              "/api/admin/attendance",
              {
                method: "POST",
                body: JSON.stringify({
                  coach_id: record.coachId,
                  sport_id: record.sportId,
                  session_date: record.date,
                  records: [{
                    student_id: record.athleteId,
                    status: nextStatus
                  }]
                })
              }
            );

            await loadAdminData();

          } catch (error) {

            saveButton.disabled = false;

            alert(
              error.message ||
              "Attendance update failed."
            );

          }

        }
      );

    }


    /* =====================================================
       DASHBOARD STATS
    ===================================================== */

    function updateDashboardStats() {

      document.getElementById(
        "totalAthletes"
      ).textContent =
        athletes.length;


      document.getElementById(
        "approvedCoaches"
      ).textContent =
        dashboardStats.active_coaches ?? approvedCoaches.filter(coach => coach.coachStatus === "approved" && coach.active).length;


      document.getElementById(
        "pendingRequests"
      ).textContent =
        dashboardStats.pending_coaches ?? coachRequests.filter(request => request.status === "pending").length;


      document.getElementById(
        "attendanceRecords"
      ).textContent =
        dashboardStats.present_today ?? 0;

      document.getElementById("totalCoaches").textContent = dashboardStats.total_coaches ?? approvedCoaches.length;
      document.getElementById("absentToday").textContent = dashboardStats.absent_today ?? 0;
      document.getElementById("overallAttendance").textContent = `${dashboardStats.overall_attendance_percent ?? 0}%`;

    }


    /* =====================================================
       CAPITALIZE
    ===================================================== */

    function capitalize(value) {

      return value
        .charAt(0)
        .toUpperCase()
        +
        value.slice(1);

    }


    /* =====================================================
       SIDEBAR
    ===================================================== */

    function toggleSidebar() {

      document
        .getElementById(
          "sidebar"
        )
        .classList.toggle(
          "open"
        );

    }


    function closeSidebar() {

      document
        .getElementById(
          "sidebar"
        )
        .classList.remove(
          "open"
        );

    }


    /* =====================================================
       LOGOUT
    ===================================================== */

    function logout() {
      fetch(`${window.FITNESS_API_BASE || ""}/api/logout`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" }
      }).catch(error => console.warn("Admin sign-out request failed:", error))
        .finally(() => window.location.replace("admin-login.html"));
    }


    /* =====================================================
       ESC KEY
    ===================================================== */

    document.addEventListener(
      "keydown",
      function(event) {

        if (
          event.key ===
          "Escape"
        ) {

          closeAthleteModal();

          closeRolePopup();

        }

      }
    );


    /* =====================================================
       ROLE POPUP OUTSIDE CLICK
    ===================================================== */

    document
      .getElementById(
        "rolePopupOverlay"
      )
      .addEventListener(
        "click",
        function(event) {

          if (
            event.target ===
            this
          ) {

            closeRolePopup();

          }

        }
      );


    /* =====================================================
       INITIALIZE
    ===================================================== */

    const today =
      getToday();


    const adminAttendanceDate = document.getElementById("adminAttendanceDate");
    if (adminAttendanceDate) adminAttendanceDate.value = today;

    const globalDatePicker = document.getElementById("globalDatePicker");
    if (globalDatePicker) globalDatePicker.value = today;

    const globalDateDisplay = document.getElementById("globalDateDisplay");
    if (globalDateDisplay) globalDateDisplay.value = formatDateDisplay(today);

    const adminAttendanceDateDisplay = document.getElementById("adminAttendanceDateDisplay");
    if (adminAttendanceDateDisplay) {
      adminAttendanceDateDisplay.value = formatDateDisplay(today);
    }


    function mountAdminAnnouncements() {
      if (!window.AnnouncementsPanel) {
        console.error("Announcements panel script did not load.");
        const empty = document.querySelector("#announcementsPanel .announcement-empty");
        if (empty) {
          empty.classList.add("error");
          empty.textContent = "Announcements could not load. Refresh the page and check the browser console.";
        }
        return;
      }
      window.AnnouncementsPanel.mount({
        root: "#announcementsPanel",
        canManage: true
      });
    }

    let adminEventsMounted = false;
    function mountAdminEvents() {
      if (adminEventsMounted) return;
      if (!window.DashboardEvents) {
        console.error("Dashboard events script did not load.");
        document.querySelector("#dashboardEventsPanel .announcement-empty").textContent = "Events could not load. Refresh the page and check the browser console.";
        return;
      }
      window.DashboardEvents.mount({ root: "#dashboardEventsPanel", role: "admin" });
      adminEventsMounted = true;
    }

    // Mount both panels during page initialization so their forms are ready
    // even if navigation or a cached page bypasses the section click handler.
    mountAdminAnnouncements();
    mountAdminEvents();

    loadAdminData();

    renderAthletes();

    renderCoachRequests();

    renderCoaches();

    renderAttendance();

    updateDashboardStats();

  