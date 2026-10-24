/* ================================================================
   ATHLETE TRACKER — AUTH GUARD
   Protects pages, with preview / bypass support for offline inspection.
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
        "student-signup-verify.html",
        "student-basicinfo.html",
        "student-personalinfo.html",
        "coach-login.html",
        "coach-loginotp.html",
        "coach-signup.html",
        "coach-signup-verify.html",
        "coach-waiting.html",
        "admin-login.html",
        "admin-loginotp.html",
        "forgot-password.html",
        "verify.html",
        "verify-otp.html",
        "login-otp.html",
        "set-password.html",
        "reset-password.html"
    ];

    const currentPath = window.location.pathname.toLowerCase();
    const currentPage = currentPath.split("/").pop() || "index.html";
    const isPublic = PUBLIC_PAGES.some(p => currentPage.includes(p));

    if (isPublic) {
        if (cfg.DEBUG) console.log("[AUTH GUARD] Public page — no check needed.");
        return;
    }

    // Role detection from path
    let role = "player";
    if (currentPath.includes("/coach/")) role = "coach";
    if (currentPath.includes("/admin/")) role = "admin";

    const mockUsers = {
        player: {
            id: 1,
            name: "Alex Morgan",
            full_name: "Alex Morgan",
            email: "alex.morgan@fittrack.com",
            role: "student",
            sport: "Track & Field / Football",
            department: "Sports Science",
            semester: "4"
        },
        coach: {
            id: 2,
            name: "Coach Sarah Jenkins",
            full_name: "Sarah Jenkins",
            email: "coach@fittrack.com",
            role: "coach",
            specialization: "Athletics & Fitness",
            contact_number: "+1 555-0192"
        },
        admin: {
            id: 3,
            name: "Admin Manager",
            full_name: "System Administrator",
            email: "admin@fittrack.com",
            role: "admin"
        }
    };

    // If AUTH_BYPASS is active, seed demo user and allow immediate page access
    if (cfg.AUTH_BYPASS !== false) {
        window.__USER = mockUsers[role] || mockUsers.player;
        if (cfg.DEBUG) console.log("[AUTH GUARD] Auth bypass enabled. Current user:", window.__USER);
        return;
    }

    // Otherwise, check session against API
    if (typeof API !== "undefined" && typeof API.getSession === "function") {
        API.getSession().then(function (res) {
            if (!res.ok || !res.data || !res.data.authenticated) {
                if (cfg.DEBUG) console.log("[AUTH GUARD] No session — redirecting to login.");
                API.redirectToLogin(role);
            } else {
                if (cfg.DEBUG) console.log("[AUTH GUARD] Session valid:", res.data.user);
                window.__USER = res.data.user;
            }
        }).catch(function (err) {
            console.warn("[AUTH GUARD] Backend connection failed:", err);
            // Fallback gracefully to demo user if offline
            window.__USER = mockUsers[role] || mockUsers.player;
        });
    }
})();