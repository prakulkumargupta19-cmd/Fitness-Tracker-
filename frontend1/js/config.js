/* ================================================================
   ATHLETE TRACKER — API CONFIGURATION

   RULE FOR FRONTEND DEVS:
   • You may change colors, fonts, spacing, layout — anything visual.
   • NEVER change variable names, function names, or fetch URLs here.
   • If you need a new API endpoint, ask the backend team to add it
     to api-client.js first. Then use the helper function.
   ================================================================ */

(function () {
    "use strict";

    // Auto-detect environment: relative paths work everywhere
    const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

    window.APP_CONFIG = {
        // Base URL for API calls. Always use relative paths.
        // If frontend is served from a different origin, override via env.
        API_BASE: "",

        // Role mapping (backend uses 'player', UI uses 'student')
        ROLE_MAP: {
            student: "player",
            coach: "coach",
            admin: "admin"
        },

        // Inverse mapping for display
        DISPLAY_ROLE: {
            player: "Student",
            coach: "Coach",
            admin: "Admin"
        },

        // Page routing by role
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

        // Debug logging (enabled on localhost only)
        DEBUG: isLocal
    };

})();
