/* ================================================================
   ATHLETE TRACKER — API CONFIGURATION
   ================================================================ */

(function () {
    "use strict";

    const isLocalHost =
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1";
    const localApiBase =
        isLocalHost
            ? `${window.location.protocol}//${window.location.hostname}:5000`
            : "";
    const configuredApiBase =
        window.FITNESS_API_BASE ||
        window.APP_CONFIG?.API_BASE ||
        localApiBase;
    const apiBase = configuredApiBase.replace(/\/+$/, "");

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
        DEBUG: false
    };

    // Local static servers use Flask on port 5000. Deployed pages remain
    // same-origin unless a public API origin is explicitly injected.
    window.FITNESS_API_BASE = apiBase;
})();
