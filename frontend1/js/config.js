
/* ATHLETE TRACKER — API CONFIGURATION */
(function () {
    "use strict";

    const isLocalHost =
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1";

    // Port 8080 uses the dev server proxy.
    // Port 8081 uses the Flask backend directly.
    const usesLocalApiProxy =
        isLocalHost && window.location.port === "8080";

    const localApiBase =
        isLocalHost && !usesLocalApiProxy
            ? `${window.location.protocol}//${window.location.hostname}:5000`
            : "";

    const configuredApiBase =
        usesLocalApiProxy
            ? ""
            : window.FITNESS_API_BASE ||
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

    window.FITNESS_API_BASE = apiBase;
})();
