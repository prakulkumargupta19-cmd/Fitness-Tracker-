/* ================================================================
   ATHLETE TRACKER — API CLIENT

   THIS FILE IS OWNED BY THE BACKEND TEAM.
   Frontend developers: IMPORT this file and call the functions.
   Do NOT write raw fetch() calls in your HTML/JS.

   Usage:
     <script src="../js/config.js"></script>
     <script src="../js/api-client.js"></script>
     <script>
       API.login({email: "...", password: "...", role: "student"})
         .then(res => { ... })
         .catch(err => { ... });
     </script>
   ================================================================ */

(function () {
    "use strict";

    const cfg = window.APP_CONFIG || { API_BASE: "", DEBUG: false };

    // ── Low-level request helper ────────────────────────────────────────────
    async function apiRequest(method, endpoint, body) {
        const url = cfg.API_BASE + endpoint;
        const options = {
            method: method,
            headers: { "Content-Type": "application/json" },
            credentials: "include"  // Sends session cookie
        };
        if (body !== undefined) {
            options.body = JSON.stringify(body);
        }

        if (cfg.DEBUG) console.log(`[API] ${method} ${url}`, body);

        try {
            const response = await fetch(url, options);
            let data;
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                data = await response.json();
            } else {
                data = { success: false, message: "Unexpected server response." };
            }
            if (cfg.DEBUG) console.log(`[API] ${method} ${url} → ${response.status}`, data);
            return { ok: response.ok, status: response.status, data: data };
        } catch (networkError) {
            if (cfg.DEBUG) console.error(`[API] Network error: ${networkError}`);
            return {
                ok: false,
                status: 0,
                data: { success: false, message: "Network error. Please check your connection." }
            };
        }
    }

    // ── Public API ──────────────────────────────────────────────────────────
    window.API = {
        // ── Auth ────────────────────────────────────────────────────────────
        login: function (credentials) {
            // credentials: {email, password, role}
            // role in UI: "student" | "coach" | "admin"
            const payload = {
                email: credentials.email,
                password: credentials.password,
                role: cfg.ROLE_MAP[credentials.role] || credentials.role
            };
            return apiRequest("POST", "/api/login", payload);
        },

        adminLogin: function (credentials) {
            return apiRequest("POST", "/api/admin-login", credentials);
        },

        adminVerifyOtp: function (payload) {
            return apiRequest("POST", "/api/admin-login/verify-otp", payload);
        },

        adminResendOtp: function (payload) {
            return apiRequest("POST", "/api/admin-login/resend-otp", payload);
        },

        register: function (data) {
            // data: {name, email, password, role, sport, contact_number, gender, date_of_birth}
            const payload = { ...data };
            if (payload.role) {
                payload.role = cfg.ROLE_MAP[payload.role] || payload.role;
            }
            return apiRequest("POST", "/api/register", payload);
        },

        verifySignupOtp: function (data) {
            return apiRequest("POST", "/api/account-verification/verify", data);
        },

        resendSignupOtp: function (data) {
            return apiRequest("POST", "/api/account-verification/send", data);
        },

        forgotPassword: function (data) {
            return apiRequest("POST", "/api/forgot-password", data);
        },

        verifyResetOtp: function (data) {
            return apiRequest("POST", "/api/forgot-password/verify-otp", data);
        },

        resendResetOtp: function (data) {
            return apiRequest("POST", "/api/forgot-password/resend-otp", data);
        },

        resetPassword: function (data) {
            return apiRequest("POST", "/api/reset-password", data);
        },

        logout: function () {
            return apiRequest("POST", "/api/logout");
        },

        // ── Session ─────────────────────────────────────────────────────────
        getSession: function () {
            return apiRequest("GET", "/api/session");
        },

        getAdminSession: function () {
            return apiRequest("GET", "/api/admin/session");
        },

        // ── Data (Student / Coach / Admin) ─────────────────────────────────
        getAssessments: function () {
            return apiRequest("GET", "/api/assessments");
        },

        getTrainingSessions: function () {
            return apiRequest("GET", "/api/training-sessions");
        },

        getGoals: function () {
            return apiRequest("GET", "/api/goals");
        },

        getFeedback: function () {
            return apiRequest("GET", "/api/feedback");
        },

        getCoachAthletes: function () {
            return apiRequest("GET", "/api/coach/athletes");
        },

        // ── Admin ───────────────────────────────────────────────────────────
        getUsers: function () {
            return apiRequest("GET", "/api/users");
        },

        // ── Write (Coach only) ──────────────────────────────────────────────
        createAssessment: function (data) {
            return apiRequest("POST", "/api/assessments", data);
        },

        createTrainingSession: function (data) {
            return apiRequest("POST", "/api/training-sessions", data);
        },

        createGoal: function (data) {
            return apiRequest("POST", "/api/goals", data);
        },

        createFeedback: function (data) {
            return apiRequest("POST", "/api/feedback", data);
        },

        // ── Utilities ───────────────────────────────────────────────────────
        redirectToDashboard: function (role) {
            const page = cfg.DASHBOARD_PAGES[role] || cfg.DASHBOARD_PAGES.player;
            window.location.href = page;
        },

        redirectToLogin: function (role) {
            const page = cfg.LOGIN_PAGES[role] || cfg.LOGIN_PAGES.player;
            window.location.href = page;
        },

        showMessage: function (elementId, text, type) {
            const el = document.getElementById(elementId);
            if (!el) return;
            el.textContent = text;
            el.className = "message " + (type || "");
            el.style.display = "block";
        },

        hideMessage: function (elementId) {
            const el = document.getElementById(elementId);
            if (!el) return;
            el.style.display = "none";
        }
    };
})();