
      "use strict";

      const API_BASE_URL = `${window.FITNESS_API_BASE || ""}/api`;

      /* =========================================================
   STUDENT INFORMATION
========================================================= */

      let studentName = "Student";
      let studentEmail = "";
      let studentProfileData = {};

      /* =========================================================
   PROFILE
========================================================= */

      function updateStudentProfile(data = {}) {
        const profile = data.student || data.user || data.profile || data || {};

        studentProfileData = {
          ...studentProfileData,
          ...profile,
        };

        const setValue = (id, value, fallback = "Not provided") => {
          const element = document.getElementById(id);

          if (!element) return;

          element.textContent =
            value !== undefined && value !== null && String(value).trim() !== ""
              ? String(value)
              : fallback;
        };

        setValue(
          "profileName",
          profile.name || profile.full_name || studentName,
        );
        setValue(
          "profileNameDisplay",
          profile.name || profile.full_name || studentName,
        );

        setValue("profileEmail", profile.email || studentEmail);

        setValue("profileGender", profile.gender);
        setValue("profileGenderDisplay", profile.gender);

        setValue("profileDob", profile.date_of_birth || profile.dob);
        setValue("profileDobDisplay", profile.date_of_birth || profile.dob);

        setValue(
          "profilePhone",
          profile.contact_number || profile.phone || profile.phone_number,
        );
        setValue(
          "profilePhoneDisplay",
          profile.contact_number || profile.phone || profile.phone_number,
        );

        setValue(
          "profileEmergency",
          profile.emergency_contact || profile.emergency_number,
        );
        setValue(
          "profileEmergencyDisplay",
          profile.emergency_contact || profile.emergency_number,
        );

        setValue("profileYear", profile.year ? `Year ${profile.year}` : null);
        setValue(
          "profileYearDisplay",
          profile.year ? `Year ${profile.year}` : null,
        );

        setValue(
          "profileSemester",
          profile.semester ? `Semester ${profile.semester}` : null,
        );
        setValue(
          "profileSemesterDisplay",
          profile.semester ? `Semester ${profile.semester}` : null,
        );

        setValue("profileDepartment", profile.department);
        setValue("profileDepartmentDisplay", profile.department);

        setValue(
          "profileHeight",
          profile.height
            ? `${profile.height} cm`
            : profile.height_cm
              ? `${profile.height_cm} cm`
              : null,
        );
        setValue(
          "profileHeightDisplay",
          profile.height
            ? `${profile.height} cm`
            : profile.height_cm
              ? `${profile.height_cm} cm`
              : null,
        );

        setValue(
          "profileWeight",
          profile.weight
            ? `${profile.weight} kg`
            : profile.weight_kg
              ? `${profile.weight_kg} kg`
              : null,
        );
        setValue(
          "profileWeightDisplay",
          profile.weight
            ? `${profile.weight} kg`
            : profile.weight_kg
              ? `${profile.weight_kg} kg`
              : null,
        );

        setValue(
          "profileSport",
          profile.sport || profile.activity || profile.sport_activity,
        );
        setValue(
          "profileSportDisplay",
          profile.sport || profile.activity || profile.sport_activity,
        );

        setValue("profileGoal", profile.goal);
        setValue("profileGoalDisplay", profile.goal);

        const sports = Array.isArray(profile.sports)
          ? profile.sports
              .map((sport) =>
                typeof sport === "string"
                  ? sport
                  : sport.name || sport.sport_name,
              )
              .filter(Boolean)
              .join(", ")
          : profile.sport_activity || profile.sport || profile.activity;
        setValue("profileSport", sports);
        setValue("profileSportDisplay", sports);
        const studentSportLabel = document.getElementById(
          "topStudentSportLabel",
        );
        if (studentSportLabel) {
          studentSportLabel.textContent = sports || "Student Athlete";
          studentSportLabel.title = sports || "Student Athlete";
        }
        setValue(
          "profileStudentNumberDisplay",
          profile.student_number || profile.student_id,
        );
        setValue("profileBloodGroupDisplay", profile.blood_group);
        setValue("profileMedicalHistoryDisplay", profile.medical_history);
        setValue("profileAddressDisplay", profile.address);
        setValue("profileParentNameDisplay", profile.parent_name);
        setValue("profileParentPhoneDisplay", profile.parent_phone);
        setValue("profileParentAddressDisplay", profile.parent_address);

        const initials = (
          profile.name ||
          profile.full_name ||
          studentName ||
          "Student"
        )
          .charAt(0)
          .toUpperCase();

        const avatarIds = ["topbarAvatar", "sidebarAvatar", "profileTabAvatar"];

        avatarIds.forEach((id) => {
          const element = document.getElementById(id);

          if (element) {
            element.textContent = initials;
          }
        });

        const profileName = document.getElementById("profileTabName");

        if (profileName) {
          profileName.textContent =
            profile.name || profile.full_name || studentName;
        }
      }

      /* =========================================================
   HEADER UI
========================================================= */

      function updateProfileHeaderUI() {
        const elements = {
          studentBrandName: studentName,
          topStudentName: studentName,
          sidebarStudentName: studentName,
          welcomeName: studentName,
        };

        Object.entries(elements).forEach(([id, value]) => {
          const element = document.getElementById(id);

          if (element) {
            element.textContent = value;
          }
        });

        const initials = studentName.charAt(0).toUpperCase();

        ["topbarAvatar", "sidebarAvatar", "profileTabAvatar"].forEach((id) => {
          const element = document.getElementById(id);

          if (element) {
            element.textContent = initials;
          }
        });
      }

      updateProfileHeaderUI();

      /* =========================================================
   SESSION CHECK
========================================================= */

      async function checkStudentSession() {
        const cfg = window.APP_CONFIG || {};
        if (cfg.AUTH_BYPASS === true) return true;

        try {
          const response = await fetch(`${API_BASE_URL}/session`, {
            method: "GET",
            credentials: "include",
          });

          if (response.ok) {
            const data = await response.json();
            if (
              data.authenticated &&
              data.user &&
              data.user.role === "student"
            ) {
              studentName = data.user.name || studentName;
              studentEmail = data.user.email || studentEmail;
              updateProfileHeaderUI();
              updateStudentProfile(data.user);
              return true;
            }
          }
        } catch (error) {
          console.warn("Session check offline:", error);
        }

        return false;
      }

      /* =========================================================
   CHARTS
========================================================= */

      let barChart = null;
      let radarChart = null;
      let lineChart = null;

      function initCharts() {
        const isDark = document.body.classList.contains("dark-mode");

        const textColor = isDark ? "#94a3b8" : "#64748b";

        const gridColor = isDark ? "#263653" : "#e7edf5";

        Chart.defaults.color = textColor;

        /* BAR */

        const barCanvas = document.getElementById("categoryBarChart");

        if (barCanvas) {
          if (barChart) {
            barChart.destroy();
          }

          barChart = new Chart(barCanvas, {
            type: "bar",

            data: {
              labels: [
                "Speed",
                "Endurance",
                "Strength",
                "Agility",
                "Flexibility",
                "Reaction time",
              ],

              datasets: [
                {
                  label: "Current",

                  data: [],

                  backgroundColor: "#2563eb",

                  borderRadius: 8,
                },
              ],
            },

            options: {
              responsive: true,

              maintainAspectRatio: false,

              plugins: {
                legend: {
                  position: "bottom",
                },
              },

              scales: {
                x: {
                  grid: {
                    display: false,
                  },
                },

                y: {
                  beginAtZero: true,

                  max: 100,

                  grid: {
                    color: gridColor,
                  },
                },
              },
            },
          });
        }

        /* RADAR */

        const radarCanvas = document.getElementById("attributeRadarChart");

        if (radarCanvas) {
          if (radarChart) {
            radarChart.destroy();
          }

          radarChart = new Chart(radarCanvas, {
            type: "radar",

            data: {
              labels: [
                "Speed",
                "Endurance",
                "Strength",
                "Agility",
                "Flexibility",
                "Reaction time",
              ],

              datasets: [
                {
                  label: "Performance",

                  data: [],

                  backgroundColor: "rgba(37,99,235,.15)",

                  borderColor: "#2563eb",

                  borderWidth: 2,
                },
              ],
            },

            options: {
              responsive: true,

              maintainAspectRatio: false,

              scales: {
                r: {
                  suggestedMin: 40,

                  suggestedMax: 100,

                  grid: {
                    color: gridColor,
                  },

                  angleLines: {
                    color: gridColor,
                  },

                  ticks: {
                    display: false,
                  },
                },
              },

              plugins: {
                legend: {
                  display: false,
                },
              },
            },
          });
        }

        /* LINE */

        const lineCanvas = document.getElementById("progressionLineChart");

        if (lineCanvas) {
          if (lineChart) {
            lineChart.destroy();
          }

          lineChart = new Chart(lineCanvas, {
            type: "line",

            data: {
              labels: [],

              datasets: [
                {
                  label: "Performance Index",

                  data: [],

                  borderColor: "#2563eb",

                  backgroundColor: "rgba(37,99,235,.08)",

                  fill: true,

                  tension: 0.4,

                  borderWidth: 3,
                },
              ],
            },

            options: {
              responsive: true,

              maintainAspectRatio: false,

              plugins: {
                legend: {
                  display: false,
                },
              },

              scales: {
                x: {
                  grid: {
                    display: false,
                  },
                },

                y: {
                  min: 50,

                  max: 100,

                  grid: {
                    color: gridColor,
                  },
                },
              },
            },
          });
        }
      }

      /* =========================================================
   DASHBOARD DATA
========================================================= */

      async function fetchDashboardData() {
        let data = null;
        let assessmentRows = [];
        let trainingRows = [];
        let goalRows = [];
        let feedbackRows = [];
        let feedbackLoadError = "";

        try {
          const response = await fetch(`${API_BASE_URL}/student/dashboard`, {
            method: "GET",
            credentials: "include",
          });

          if (response.ok) {
            data = await response.json();
            const [assessments, training, goals, feedback] = await Promise.all([
              fetch(`${API_BASE_URL}/assessments`, { credentials: "include" })
                .then((r) => (r.ok ? r.json() : {}))
                .catch(() => ({})),
              fetch(`${API_BASE_URL}/training-sessions`, {
                credentials: "include",
              })
                .then((r) => (r.ok ? r.json() : {}))
                .catch(() => ({})),
              fetch(`${API_BASE_URL}/goals`, { credentials: "include" })
                .then((r) => (r.ok ? r.json() : {}))
                .catch(() => ({})),
              fetch(`${API_BASE_URL}/feedback`, { credentials: "include" })
                .then(async (response) => {
                  if (!response.ok) {
                    let message = "Your coach feedback could not be loaded.";
                    try {
                      message = (await response.json()).message || message;
                    } catch (_) {}
                    throw new Error(message);
                  }
                  return response.json();
                })
                .catch((error) => ({
                  __error:
                    error.message ||
                    "Your coach feedback could not be loaded. Please try again.",
                })),
            ]);
            assessmentRows = assessments.data || [];
            trainingRows = training.data || [];
            goalRows = goals.data || [];
            if (feedback.__error) feedbackLoadError = feedback.__error;
            else feedbackRows = feedback.data || [];
          }
          const [dashboardResponse, assessments, training, goals, feedback] =
            await Promise.all([
              fetch(`${API_BASE_URL}/student/dashboard`, {
                method: "GET",
                credentials: "include",
              }).catch(() => null),
              fetch(`${API_BASE_URL}/assessments`, { credentials: "include" })
                .then((r) => (r.ok ? r.json() : {}))
                .catch(() => ({})),
              fetch(`${API_BASE_URL}/training-sessions`, {
                credentials: "include",
              })
                .then((r) => (r.ok ? r.json() : {}))
                .catch(() => ({})),
              fetch(`${API_BASE_URL}/goals`, { credentials: "include" })
                .then((r) => (r.ok ? r.json() : {}))
                .catch(() => ({})),
              fetch(`${API_BASE_URL}/feedback`, { credentials: "include" })
                .then(async (response) => {
                  if (!response.ok) {
                    let message = "Your coach feedback could not be loaded.";
                    try {
                      message = (await response.json()).message || message;
                    } catch (_) {}
                    throw new Error(message);
                  }
                  return response.json();
                })
                .catch((error) => ({
                  __error:
                    error.message ||
                    "Your coach feedback could not be loaded. Please try again.",
                })),
            ]);

          if (dashboardResponse?.ok) data = await dashboardResponse.json();
          assessmentRows = assessments.data || [];
          trainingRows = training.data || [];
          goalRows = goals.data || [];
          if (feedback.__error) feedbackLoadError = feedback.__error;
          else feedbackRows = feedback.data || [];
        } catch (err) {
          console.warn("Dashboard data could not be loaded:", err);
          feedbackLoadError =
            "We couldn’t connect to your account to load feedback. Check your connection and try again.";
        }

        if (!data) return;

        updateStudentProfile(data);
        updateAttendanceView(data.attendance || {});
        const assignedCoach = data.assigned_coach;
        document.getElementById("assignedCoachDisplay").textContent =
          assignedCoach
            ? `${assignedCoach.full_name}${assignedCoach.contact_number ? ` · ${assignedCoach.contact_number}` : ""}`
            : "No coach assigned yet.";
        renderLiveRecords(
          "analytics",
          "assessmentRecords",
          "Physical Assessments",
          assessmentRows,
          [
            "assessment_date",
            "overall_score",
            "speed",
            "strength",
            "endurance",
            "agility",
            "flexibility",
            "reaction_time",
            "notes",
          ],
        );
        renderLiveRecords(
          "improvement",
          "trainingRecords",
          "Training History",
          trainingRows,
          [
            "session_date",
            "training_type",
            "duration_minutes",
            "description",
            "performance_notes",
          ],
        );
        renderLiveRecords("goals", "goalRecords", "My Goals", goalRows, [
          "title",
          "description",
          "target_value",
          "current_value",
          "target_date",
          "status",
        ]);
        renderFeedbackView(feedbackRows, assignedCoach, feedbackLoadError);
        const scores = assessmentRows
          .map((row) => Number(row.overall_score))
          .filter(Number.isFinite);
        const overallScore = scores.length
          ? Math.round(
              scores.reduce((sum, score) => sum + score, 0) / scores.length,
            )
          : "-";
        document.getElementById("overallScore").textContent = overallScore;
        document.getElementById("dashboardPerformance").textContent =
          overallScore;
        document.getElementById("dashboardGoalProgress").textContent =
          goalRows.length
            ? `${Math.round((goalRows.filter((goal) => goal.status === "completed").length / goalRows.length) * 100)}%`
            : "-";
        document.getElementById("dashboardCoachRating").textContent =
          feedbackRows.find(
            (row) => row.rating !== null && row.rating !== undefined,
          )?.rating ?? "-";
        document.getElementById("goalCalendarDays")?.replaceChildren();
        updateAssessmentCharts(assessmentRows);
      }

      function updateAssessmentCharts(records) {
        const metrics = [
          ["Speed", "speed"],
          ["Endurance", "endurance"],
          ["Strength", "strength"],
          ["Agility", "agility"],
          ["Flexibility", "flexibility"],
          ["Reaction time", "reaction_time"],
        ];
        const latest =
          [...records].sort((left, right) =>
            String(right.assessment_date).localeCompare(
              String(left.assessment_date),
            ),
          )[0] || {};
        const labels = metrics
          .filter(
            ([, field]) =>
              latest[field] !== null && latest[field] !== undefined,
          )
          .map(([label]) => label);
        const values = metrics
          .filter(
            ([, field]) =>
              latest[field] !== null && latest[field] !== undefined,
          )
          .map(([, field]) => Number(latest[field]));
        if (barChart) {
          barChart.data.labels = labels;
          barChart.data.datasets[0].data = values;
          barChart.update();
        }
        if (radarChart) {
          radarChart.data.labels = labels;
          radarChart.data.datasets[0].data = values;
          radarChart.update();
        }
        const progression = [...records]
          .filter(
            (record) =>
              record.overall_score !== null &&
              record.overall_score !== undefined,
          )
          .sort((left, right) =>
            String(left.assessment_date).localeCompare(
              String(right.assessment_date),
            ),
          );
        if (lineChart) {
          lineChart.data.labels = progression.map(
            (record) => record.assessment_date,
          );
          lineChart.data.datasets[0].data = progression.map((record) =>
            Number(record.overall_score),
          );
          lineChart.update();
        }
      }

      function renderLiveRecords(
        sectionId,
        containerId,
        title,
        records,
        fields,
      ) {
        const section = document.getElementById(sectionId);
        if (!section) return;
        let container = document.getElementById(containerId);
        if (!container) {
          container = document.createElement("div");
          container.id = containerId;
          container.className = "dashboard-card";
          section.appendChild(container);
        }
        container.replaceChildren();
        const heading = document.createElement("h3");
        heading.textContent = title;
        container.appendChild(heading);
        if (!records.length) {
          const empty = document.createElement("p");
          empty.textContent = "No records yet.";
          container.appendChild(empty);
          return;
        }
        records.forEach((record) => {
          const article = document.createElement("article");
          article.className = "live-record";
          fields.forEach((field) => {
            const value = record[field];
            if (value === null || value === undefined || value === "") return;
            const line = document.createElement("p");
            line.textContent = `${field.replaceAll("_", " ")}: ${value}`;
            article.appendChild(line);
          });
          container.appendChild(article);
        });
      }

      function updateAttendanceView(attendance) {
        const summary = attendance || {};
        const percentage = Number(summary.percentage || 0);
        document.getElementById("attendancePercentage").textContent =
          `${percentage}%`;
        document.getElementById("dashboardAttendance").textContent =
          summary.total ? `${percentage}%` : "-";
        document.getElementById("dashboardAttendanceLate").textContent =
          summary.late || 0;
        document.getElementById("dashboardAttendanceExcused").textContent =
          summary.excused || 0;
        document
          .getElementById("attendanceProgressFill")
          .style.setProperty("--attendance-progress-width", `${percentage}%`);
        document.getElementById("attendancePresent").textContent =
          summary.present || 0;
        document.getElementById("attendanceAbsent").textContent =
          summary.absent || 0;
        document.getElementById("attendanceLate").textContent =
          summary.late || 0;
        document.getElementById("attendanceExcused").textContent =
          summary.excused || 0;
        document.getElementById("attendanceTotal").textContent =
          summary.total || 0;
        document.getElementById("attendanceLabel").textContent =
          summary.label || "No sessions yet";
        document.getElementById("attendanceStatusText").textContent =
          summary.statusText || "Not started";
        document.getElementById("attendanceStatusDesc").textContent =
          summary.statusDesc ||
          "Attendance will appear here after a coach records a session.";
        const week = document.getElementById("attendanceWeekContainer");
        week.replaceChildren();
        (summary.weekly || []).forEach((day) => {
          const item = document.createElement("div");
          item.className = "attendance-day";
          const name = document.createElement("span");
          name.textContent = day.day;
          const status = document.createElement("strong");
          const statusLabels = {
            present: "Present",
            late: "Late",
            absent: "Absent",
            excused: "Excused",
            mixed: "Mixed",
            none: "—",
          };
          const dayStatus = day.status || (day.present ? "present" : "absent");
          status.className = dayStatus;
          status.textContent = statusLabels[dayStatus] || "—";
          if (day.statuses?.length)
            item.title = day.statuses
              .map((value) => statusLabels[value] || value)
              .join(", ");
          item.append(name, status);
          week.appendChild(item);
        });
        const history = document.getElementById("attendanceHistoryContainer");
        history.replaceChildren();
        (summary.records || []).forEach((record) => {
          const line = document.createElement("p");
          line.className = "attendance-history-item";
          const details = document.createElement("span");
          details.textContent = `${record.session_date} · ${record.sport_name || "Training"}`;
          const status = document.createElement("strong");
          const statusLabels = {
            present: "Present",
            absent: "Absent",
            late: "Late",
            excused: "Excused",
          };
          status.className = `attendance-history-status status-${record.status}`;
          status.textContent = statusLabels[record.status] || "Recorded";
          line.append(details, status);
          history.appendChild(line);
        });
        if (!history.childElementCount)
          history.textContent = "No attendance recorded yet.";
      }

      function renderFeedbackView(records, assignedCoach, loadError = "") {
        const rows = Array.isArray(records) ? records : [];
        window.studentFeedbackRows = rows;
        const latest = rows[0];
        const rated = rows
          .map((row) => Number(row.rating))
          .filter(
            (rating) => Number.isInteger(rating) && rating >= 1 && rating <= 5,
          );
        const average = rated.length
          ? (
              rated.reduce((sum, rating) => sum + rating, 0) / rated.length
            ).toFixed(1)
          : "—";
        const coachName =
          latest?.coach_name || assignedCoach?.full_name || "No coach assigned";
        const coachNameNode = document.getElementById("feedbackCoachName");
        coachNameNode.textContent = coachName;
        document.getElementById("feedbackCoachAvatar").textContent =
          coachName !== "No coach assigned"
            ? coachName.trim().charAt(0).toUpperCase()
            : "C";
        document.getElementById("feedbackCoachMeta").textContent = "";
        document.getElementById("feedbackCount").textContent = String(
          rows.length,
        );
        document.getElementById("feedbackLatestDate").textContent = latest
          ? formatFeedbackDate(latest.created_at)
          : "—";
        document.getElementById("feedbackAverageRating").textContent =
          average === "—" ? "—" : `${average} / 5`;
        document.getElementById("coachFeedbackText").textContent =
          latest?.feedback ||
          (loadError
            ? "Feedback is temporarily unavailable."
            : "Your coach’s notes will appear here when they leave feedback.");
        const rating = Number(latest?.rating);
        document.getElementById("coachRatingNumber").textContent =
          Number.isInteger(rating) && rating >= 1 && rating <= 5
            ? `${rating}/5`
            : "—";
        const stars =
          Number.isInteger(rating) && rating >= 1 && rating <= 5
            ? "★".repeat(rating) + "☆".repeat(5 - rating)
            : "☆☆☆☆☆";
        document.getElementById("coachRatingStars").textContent = stars;
        document
          .getElementById("coachRatingStars")
          .setAttribute(
            "aria-label",
            Number.isInteger(rating) && rating >= 1 && rating <= 5
              ? `${rating} out of 5 stars`
              : "No rating yet",
          );
        document.getElementById("feedbackLatestBadge").textContent = latest
          ? formatFeedbackDate(latest.created_at)
          : "Waiting for feedback";
        document.getElementById("feedbackHistoryCount").textContent =
          `${rows.length} ${rows.length === 1 ? "note" : "notes"} · newest first`;
        const errorBox = document.getElementById("feedbackLoadError");
        errorBox.hidden = !loadError;
        if (loadError)
          document.getElementById("feedbackLoadErrorText").textContent =
            loadError;
        renderFeedbackHistory(
          rows,
          document.getElementById("feedbackSearch").value,
        );
      }

      function formatFeedbackDate(value) {
        if (!value) return "Date unavailable";
        const date = new Date(value);
        return Number.isNaN(date.getTime())
          ? String(value)
          : new Intl.DateTimeFormat(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            }).format(date);
      }

      function renderFeedbackHistory(records, query = "") {
        const list = document.getElementById("feedbackHistory");
        const normalizedQuery = query.trim().toLocaleLowerCase();
        const matches = records.filter(
          (row) =>
            !normalizedQuery ||
            `${row.feedback || ""} ${row.coach_name || ""}`
              .toLocaleLowerCase()
              .includes(normalizedQuery),
        );
        list.replaceChildren();
        if (!matches.length) {
          const empty = document.createElement("div");
          empty.className = "feedback-empty";
          empty.textContent = records.length
            ? "No feedback matches your search."
            : "There’s no feedback yet. Your coach’s notes will show up here after they’re shared.";
          list.appendChild(empty);
          return;
        }
        matches.forEach((row) => {
          const article = document.createElement("article");
          article.className = "feedback-history-item";
          const icon = document.createElement("div");
          icon.className = "feedback-history-icon";
          icon.innerHTML = '<i class="bi bi-chat-left-text"></i>';
          const content = document.createElement("div");
          const meta = document.createElement("div");
          meta.className = "feedback-history-meta";
          const date = document.createElement("span");
          date.textContent = formatFeedbackDate(row.created_at);
          const coach = document.createElement("span");
          coach.textContent = row.coach_name || "Coach";
          meta.append(date, coach);
          const note = document.createElement("p");
          note.className = "feedback-history-copy";
          note.textContent = row.feedback || "No written feedback provided.";
          content.append(meta, note);
          const rating = document.createElement("span");
          rating.className = "feedback-history-rating";
          const score = Number(row.rating);
          rating.textContent =
            Number.isInteger(score) && score >= 1 && score <= 5
              ? `★ ${score}/5`
              : "No rating";
          article.append(icon, content, rating);
          list.appendChild(article);
        });
      }

      document
        .getElementById("feedbackSearch")
        ?.addEventListener("input", (event) =>
          renderFeedbackHistory(
            window.studentFeedbackRows || [],
            event.currentTarget.value,
          ),
        );
      document
        .getElementById("feedbackRetryButton")
        ?.addEventListener("click", () => fetchDashboardData());

      /* =========================================================
   SECTION SWITCHER
========================================================= */

      const sectionTitles = {
        dashboard: "Dashboard",

        analytics: "Performance Analytics",

        improvement: "Scope of Improvement",

        goals: "Goal Progress",

        attendance: "Attendance",

        feedback: "Coach Feedback",

        events: "Events & Calendar",

        schedule: "Schedule",

        "profile-view": "My Profile",

        "settings-view": "Settings",
      };

      function mountStudentAnnouncements() {
        const root = document.querySelector("#announcementsPanel");
        if (!root) return;
        if (!window.AnnouncementsPanel) {
          root.innerHTML =
            '<div class="announcement-empty error">Announcements could not load. Refresh the page and try again.</div>';
          return;
        }
        window.AnnouncementsPanel.mount({
          root,
          canManage: false,
        });
      }

      function switchSection(sectionId) {
        document.querySelectorAll(".content-section").forEach((section) => {
          section.classList.remove("active");
        });

        const target = document.getElementById(sectionId);

        if (!target) {
          return;
        }

        target.classList.add("active");

        document.querySelectorAll(".sidebar-link").forEach((button) => {
          button.classList.toggle(
            "active",
            button.dataset.section === sectionId,
          );
        });

        const title = document.getElementById("currentPageTitle");

        if (title) {
          title.textContent = sectionTitles[sectionId] || "Dashboard";
        }

        window.scrollTo({
          top: 0,
          behavior: "smooth",
        });

        closeMobileSidebar();

        if (sectionId === "analytics") {
          setTimeout(initCharts, 100);
        }

        if (sectionId === "announcements") {
          mountStudentAnnouncements();
        }
        if (sectionId === "events") {
          window.DashboardEvents?.mount({
            root: "#dashboardEventsPanel",
            role: "student",
          });
        }
      }

      document.querySelectorAll(".sidebar-link").forEach((button) => {
        button.addEventListener("click", () => {
          switchSection(button.dataset.section);
        });
      });

      /* =========================================================
   MOBILE SIDEBAR
========================================================= */

      const sidebar = document.getElementById("sidebar");

      const sidebarOverlay = document.getElementById("sidebarOverlay");

      const mobileMenuBtn = document.getElementById("mobileMenuBtn");

      function openMobileSidebar() {
        sidebar.classList.add("mobile-open");

        sidebarOverlay.classList.add("show");
      }

      function closeMobileSidebar() {
        sidebar.classList.remove("mobile-open");

        sidebarOverlay.classList.remove("show");
      }

      mobileMenuBtn?.addEventListener("click", openMobileSidebar);

      sidebarOverlay?.addEventListener("click", closeMobileSidebar);

      /* =========================================================
   TOAST
========================================================= */

      let toastTimer = null;

      function showToast(message) {
        const toast = document.getElementById("toast");

        const text = document.getElementById("toastMessage");

        text.textContent = message;

        clearTimeout(toastTimer);

        toast.classList.add("show");

        toastTimer = setTimeout(() => {
          toast.classList.remove("show");
        }, 2500);
      }

      /* =========================================================
   DARK MODE
========================================================= */

      const darkModeToggle = document.getElementById("darkModeToggle");

      const themeButton = document.getElementById("themeButton");

      function applyTheme(isDark) {
        document.body.classList.toggle("dark-mode", isDark);

        if (darkModeToggle) {
          darkModeToggle.checked = isDark;
        }

        if (themeButton) {
          themeButton.innerHTML = isDark
            ? '<i class="bi bi-sun-fill"></i>'
            : '<i class="bi bi-moon-fill"></i>';
        }

        localStorage.setItem("studentTheme", isDark ? "dark" : "light");

        localStorage.setItem("fit-track-theme", isDark ? "dark" : "light");

        initCharts();
      }

      if (localStorage.getItem("studentTheme") === "dark") {
        applyTheme(true);
      }

      darkModeToggle?.addEventListener("change", function () {
        applyTheme(this.checked);

        showToast(this.checked ? "Dark mode enabled" : "Light mode enabled");
      });

      themeButton?.addEventListener("click", () => {
        applyTheme(!document.body.classList.contains("dark-mode"));
      });

      /* =========================================================
   LOGOUT
========================================================= */

      async function handleLogout() {
        if (!confirm("Are you sure you want to log out?")) {
          return;
        }

        sessionStorage.clear();

        await fetch(`${API_BASE_URL}/logout`, {
          method: "POST",
          credentials: "include",
        }).catch(() => {});

        window.location.replace("student-login.html");
      }

      document
        .getElementById("logoutBtnMain")
        ?.addEventListener("click", handleLogout);

      document
        .getElementById("dropdownLogoutBtn")
        ?.addEventListener("click", handleLogout);

      document
        .getElementById("sidebarLogoutBtn")
        ?.addEventListener("click", handleLogout);

      /* =========================================================
   EDIT PROFILE LOGIC (Without Photo Upload)
========================================================= */

      let isEditingProfile = false;

      function toggleEditProfile() {
        isEditingProfile = !isEditingProfile;
        const editBtn = document.getElementById("editProfileBtn");

        if (isEditingProfile) {
          document.getElementById("profileNameInput").value =
            document.getElementById("profileNameDisplay")?.textContent.trim() ||
            studentName ||
            "";
          document.getElementById("profileGenderInput").value = document
            .getElementById("profileGenderDisplay")
            .textContent.trim();
          document.getElementById("profileDobInput").value = document
            .getElementById("profileDobDisplay")
            .textContent.trim();
          document.getElementById("profilePhoneInput").value =
            document
              .getElementById("profilePhoneDisplay")
              ?.textContent.trim() ||
            studentProfileData.contact_number ||
            "";
          document.getElementById("profileEmergencyInput").value = document
            .getElementById("profileEmergencyDisplay")
            .textContent.trim();
          document.getElementById("profileYearInput").value = "";
          document.getElementById("profileSemesterInput").value = document
            .getElementById("profileSemesterDisplay")
            .textContent.replace("Semester ", "")
            .trim();
          document.getElementById("profileDepartmentInput").value = document
            .getElementById("profileDepartmentDisplay")
            .textContent.trim();
          document.getElementById("profileHeightInput").value = document
            .getElementById("profileHeightDisplay")
            .textContent.replace(" cm", "")
            .trim();
          document.getElementById("profileWeightInput").value = document
            .getElementById("profileWeightDisplay")
            .textContent.replace(" kg", "")
            .trim();
          document.getElementById("profileSportInput").value = document
            .getElementById("profileSportDisplay")
            .textContent.trim();
          document.getElementById("profileGoalInput").value = document
            .getElementById("profileGoalDisplay")
            .textContent.trim();
          document.getElementById("profileBloodGroupInput").value =
            profileValue("profileBloodGroupDisplay");
          document.getElementById("profileMedicalHistoryInput").value =
            profileValue("profileMedicalHistoryDisplay");
          document.getElementById("profileAddressInput").value = profileValue(
            "profileAddressDisplay",
          );
          document.getElementById("profileParentNameInput").value =
            profileValue("profileParentNameDisplay");
          document.getElementById("profileParentPhoneInput").value =
            profileValue("profileParentPhoneDisplay");
          document.getElementById("profileParentAddressInput").value =
            profileValue("profileParentAddressDisplay");
        }

        document
          .querySelectorAll(".view-mode")
          .forEach((el) => el.classList.toggle("d-none", isEditingProfile));
        document
          .querySelectorAll(".edit-mode")
          .forEach((el) => el.classList.toggle("d-none", !isEditingProfile));

        if (editBtn) {
          editBtn.innerHTML = isEditingProfile
            ? '<i class="bi bi-x-lg me-1"></i> Cancel'
            : '<i class="bi bi-pencil-square me-1"></i> Edit Profile';
        }
      }

      function profileValue(id) {
        const value = document.getElementById(id)?.textContent.trim();
        return value === "—" || value === "Not provided" ? "" : value;
      }

      async function saveStudentProfile(event) {
        event.preventDefault();

        const updatedData = {
          full_name: document.getElementById("profileNameInput").value.trim(),
          gender: document.getElementById("profileGenderInput").value,
          date_of_birth: document.getElementById("profileDobInput").value,
          contact_number: document.getElementById("profilePhoneInput").value,
          emergency_contact: document.getElementById("profileEmergencyInput")
            .value,
          semester: document.getElementById("profileSemesterInput").value,
          department: document.getElementById("profileDepartmentInput").value,
          height_cm: document.getElementById("profileHeightInput").value,
          weight_kg: document.getElementById("profileWeightInput").value,
          sport_activity: document.getElementById("profileSportInput").value,
          goal: document.getElementById("profileGoalInput").value,
          blood_group: document.getElementById("profileBloodGroupInput").value,
          medical_history: document.getElementById("profileMedicalHistoryInput")
            .value,
          address: document.getElementById("profileAddressInput").value,
          parent_name: document.getElementById("profileParentNameInput").value,
          parent_phone: document.getElementById("profileParentPhoneInput")
            .value,
          parent_address: document.getElementById("profileParentAddressInput")
            .value,
        };

        try {
          const response = await fetch(`${API_BASE_URL}/profile`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify(updatedData),
          });

          const result = await response.json();
          if (response.ok) {
            showToast("Profile updated successfully");
            studentName = updatedData.full_name;
            updateProfileHeaderUI();
            updateStudentProfile({ ...(result.profile || {}), ...updatedData });
            toggleEditProfile();
          } else {
            showToast(result.message || "Failed to update profile");
          }
        } catch (err) {
          showToast("Could not save profile. Please try again.");
        }
      }

      async function loadStudentProfile() {
        try {
          const response = await fetch(`${API_BASE_URL}/profile`, {
            credentials: "include",
          });
          if (!response.ok)
            throw new Error("Unable to load your saved profile.");
          const result = await response.json();
          if (result.success)
            updateStudentProfile({
              ...(result.user || {}),
              ...(result.profile || {}),
            });
        } catch (error) {
          console.error("STUDENT PROFILE LOAD ERROR:", error);
          showToast("Unable to load saved profile details");
        }
      }

      /* =========================================================
   INITIALIZATION
========================================================= */

      document.addEventListener("DOMContentLoaded", async () => {
        const authenticated = await checkStudentSession();
        if (!authenticated) {
          if (window.APP_CONFIG?.AUTH_BYPASS === false) {
            window.location.replace("student-login.html");
          }
          return;
        }

        updateProfileHeaderUI();

        await loadStudentProfile();

        initCharts();

        await fetchDashboardData();
      });

      document
        .querySelector('[data-section="schedule"]')
        ?.addEventListener("click", () => {
          window.DashboardSchedule?.mount({
            root: "#schedule",
            role: "student",
          });
        });
    
      window.DashboardSchedule?.mount({ root: "#schedule", role: "student" });
    
      window.DashboardEvents?.mount({
        root: "#dashboardEventsPanel",
        role: "student",
      });
    