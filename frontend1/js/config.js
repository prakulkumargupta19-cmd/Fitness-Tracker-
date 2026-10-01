/* ================================================================
   ATHLETE TRACKER — API CONFIGURATION
   ================================================================ */

(function () {
    "use strict";

    const isLocal =
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1";
    const apiBase = isLocal ? "http://localhost:5000" : "";

    window.APP_CONFIG = {
        API_BASE: apiBase,
        ROLE_MAP: {
            student: "student",
            coach: "coach",
            admin: "admin"
        },
        DISPLAY_ROLE: {
            player: "Student",
            coach: "Coach",
            admin: "Admin"
        },
        DASHBOARD_PAGES: {
            player: "student/student-dashboard.html",
            coach: "coach/coach-dashboard.html",
            admin: "admin/admin-dashboard.html"
        },
        LOGIN_PAGES: {
            player: "student/student-login.html",
            coach: "coach/coach-login.html",
            admin: "admin/admin-login.html"
        },
        DEBUG: isLocal
    };

    // Several standalone pages use this override directly.
    window.FITNESS_API_BASE = apiBase;
})();
