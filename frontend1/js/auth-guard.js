/* ================================================================
   ATHLETE TRACKER — AUTH GUARD

   Place this at the TOP of every protected page:
     <script src="../js/config.js"></script>
     <script src="../js/api-client.js"></script>
     <script src="../js/auth-guard.js"></script>

   It will automatically redirect unauthenticated users to login.
   ================================================================ */

(function () {
    "use strict";

    const cfg = window.APP_CONFIG || {};

    // Pages that are PUBLIC (no redirect if not logged in)
    const PUBLIC_PAGES = [
        "index.html",
        "student-login.html",
        "student-loginotp.html",
        "student-signup.html",
        "coach-login.html",
        "admin-login.html",
        "forgot-password.html",
        "verify.html",
        "reset-password.html"
    ];

    const currentPage = window.location.pathname.split("/").pop() || "index.html";
    const isPublic = PUBLIC_PAGES.some(p => currentPage.includes(p));

    if (isPublic) {
        if (cfg.DEBUG) console.log("[AUTH GUARD] Public page — no check needed.");
        return;
    }

    // Check session on load
    API.getSession().then(function (res) {
        if (!res.ok || !res.data.authenticated) {
            if (cfg.DEBUG) console.log("[AUTH GUARD] No session — redirecting to login.");
            // Try to guess role from URL path
            const path = window.location.pathname;
            let role = "player";
            if (path.includes("/coach/")) role = "coach";
            if (path.includes("/admin/")) role = "admin";
            API.redirectToLogin(role);
        } else {
            if (cfg.DEBUG) console.log("[AUTH GUARD] Session valid:", res.data.user);
            // Store minimal user info for UI use (NOT sensitive data)
            window.__USER = res.data.user;
        }
    });
})();