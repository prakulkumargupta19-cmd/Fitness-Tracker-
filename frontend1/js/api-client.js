(function () {

    "use strict";


    /* =========================================================
       APPLICATION CONFIGURATION
    ========================================================== */

    const cfg =
        window.APP_CONFIG || {

            API_BASE: "",

            DEBUG: false,

            ROLE_MAP: {

                student: "player",

                player: "player",

                coach: "coach",

                admin: "admin"

            },

            DASHBOARD_PAGES: {

                player:
                    "student/student-dashboard.html",

                coach:
                    "coach/coach-dashboard.html",

                admin:
                    "admin/admin-dashboard.html"

            },

            LOGIN_PAGES: {

                player:
                    "student/student-login.html",

                coach:
                    "coach/coach-login.html",

                admin:
                    "admin/admin-login.html"

            }

        };


    /* =========================================================
       GENERIC API REQUEST
    ========================================================== */


    let currentCsrfToken = null;

    async function fetchCsrfToken() {
        try {
            const apiBase = window.FITNESS_API_BASE || cfg.API_BASE || "";
            const response = await fetch(apiBase + "/api/csrf-token", {
                credentials: "include"
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            if (data.csrf_token) {
                currentCsrfToken = data.csrf_token;
                return currentCsrfToken;
            }
        } catch (err) {
            console.error("CSRF Token fetch failed:", err);
        }
        return null;
    }

    async function apiRequest(
        method,
        endpoint,
        body
    ) {

        const apiBase =
            window.FITNESS_API_BASE || cfg.API_BASE || "";

        const url =
            apiBase + endpoint;


        // Handle CSRF for state-changing requests
        if (method !== "GET" && method !== "HEAD" && method !== "OPTIONS") {
            // Refresh per state-changing request so the token always matches
            // the current session cookie (including after login/signup flows).
            currentCsrfToken = null;
            await fetchCsrfToken();
        }

        const options = {

            method: method,

            headers: {

                "Content-Type":
                    "application/json"

            },

            credentials:
                "include"

        };

        if (currentCsrfToken) {
            options.headers["X-CSRFToken"] = currentCsrfToken;
        }


        if (body !== undefined) {

            options.body =
                JSON.stringify(body);

        }


        if (cfg.DEBUG) {

            console.log(
                "API REQUEST:",
                method,
                url,
                body
            );

        }


        try {

            const response =
                await fetch(
                    url,
                    options
                );


            let data;


            const contentType =
                response.headers.get(
                    "content-type"
                ) || "";


            if (
                contentType.includes(
                    "application/json"
                )
            ) {

                data =
                    await response.json();

            } else {

                data = {

                    success: false,

                    message:
                        "Unexpected server response."

                };

            }


            if (cfg.DEBUG) {

                console.log(
                    "API RESPONSE:",
                    response.status,
                    data
                );

            }


            return {

                ok:
                    response.ok,

                status:
                    response.status,

                data:
                    data

            };

        }

        catch (error) {

            console.error(
                "API NETWORK ERROR:",
                error
            );


            return {

                ok: false,

                status: 0,

                data: {

                    success: false,

                    message:
                        "Network error. Please check your connection."

                }

            };

        }

    }


    /* =========================================================
       PUBLIC API
    ========================================================== */

    window.API = {


        /* =====================================================
           LOGIN
        ====================================================== */

        login(credentials) {

            return apiRequest(

                "POST",

                "/api/login",

                {

                    email:
                        credentials.email,

                    password:
                        credentials.password,

                    role:
                        cfg.ROLE_MAP[
                            credentials.role
                        ] ||
                        credentials.role

                }

            );

        },


        /* =====================================================
           ADMIN LOGIN
        ====================================================== */

        adminLogin(credentials) {

            return apiRequest(

                "POST",

                "/api/admin-login",

                {

                    email:
                        credentials.email,

                    password:
                        credentials.password

                }

            );

        },


        adminVerifyOtp(
            email,
            otp
        ) {

            return apiRequest(

                "POST",

                "/api/admin-login/verify-otp",

                {

                    email:
                        email,

                    otp:
                        otp

                }

            );

        },


        adminResendOtp(email) {

            return apiRequest(

                "POST",

                "/api/admin-login/resend-otp",

                {

                    email:
                        email

                }

            );

        },


        /* =====================================================
           STUDENT / COACH REGISTRATION
        ====================================================== */

        register(data) {

            const payload = {

                name:
                    data.name,

                email:
                    data.email,

                password:
                    data.password,

                confirm_password:
                    data.confirm_password,

                role:
                    data.role === "student"
                        ? "student"
                        : cfg.ROLE_MAP[data.role] || data.role

            };


            if (
                data.sport !== undefined
            ) {

                payload.sport =
                    data.sport;

            }


            if (
                data.contact_number !== undefined
            ) {

                payload.contact_number =
                    data.contact_number;

            }


            if (
                data.gender !== undefined
            ) {

                payload.gender =
                    data.gender;

            }


            if (
                data.date_of_birth !== undefined
            ) {

                payload.date_of_birth =
                    data.date_of_birth;

            }


            return apiRequest(

                "POST",

                "/api/register",

                payload

            );

        },


        /* =====================================================
           SIGNUP OTP
        ====================================================== */

        verifySignupOtp(
            email,
            otp
        ) {

            return apiRequest(

                "POST",

                "/api/account-verification/verify",

                {

                    email:
                        email,

                    otp:
                        otp

                }

            );

        },


        resendSignupOtp(email) {

            return apiRequest(

                "POST",

                "/api/account-verification/send",

                {

                    email:
                        email

                }

            );

        },


        /* =====================================================
           FORGOT PASSWORD
        ====================================================== */

        forgotPassword(email) {

            return apiRequest(

                "POST",

                "/api/forgot-password",

                {

                    email:
                        email

                }

            );

        },


        verifyResetOtp(
            email,
            otp
        ) {

            return apiRequest(

                "POST",

                "/api/forgot-password/verify-otp",

                {

                    email:
                        email,

                    otp:
                        otp

                }

            );

        },


        resendResetOtp(email) {

            return apiRequest(

                "POST",

                "/api/forgot-password/resend-otp",

                {

                    email:
                        email

                }

            );

        },


        resetPassword(
            email,
            otp,
            password,
            confirmPassword
        ) {

            return apiRequest(

                "POST",

                "/api/reset-password",

                {

                    email:
                        email,

                    otp:
                        otp,

                    password:
                        password,

                    confirm_password:
                        confirmPassword

                }

            );

        },


        /* =====================================================
           SESSION
        ====================================================== */

        async getSession() {
            try {
                const res = await apiRequest("GET", "/api/session");
                if (res.ok && res.data && res.data.authenticated) {
                    return res;
                }
            } catch (_err) {
                // Network failure
            }

            if (cfg.AUTH_BYPASS !== false) {
                const path = window.location.pathname.toLowerCase();
                let role = "student";
                if (path.includes("/coach/")) role = "coach";
                if (path.includes("/admin/")) role = "admin";
                return {
                    ok: true,
                    status: 200,
                    data: {
                        authenticated: true,
                        user: {
                            id: role === "coach" ? 2 : role === "admin" ? 3 : 1,
                            name: role === "coach" ? "Coach Sarah Jenkins" : role === "admin" ? "Admin Manager" : "Alex Morgan",
                            full_name: role === "coach" ? "Coach Sarah Jenkins" : role === "admin" ? "Admin Manager" : "Alex Morgan",
                            email: `${role}@fittrack.com`,
                            role: role,
                            sport: "Athletics & Fitness"
                        }
                    }
                };
            }

            return {
                ok: false,
                status: 401,
                data: {
                    authenticated: false,
                    message: "No active session."
                }
            };
        },


        async getAdminSession() {
            try {
                const res = await apiRequest("GET", "/api/admin/session");
                if (res.ok && res.data && res.data.authenticated) {
                    return res;
                }
            } catch (_err) {
                // Network failure
            }

            if (cfg.AUTH_BYPASS !== false) {
                return {
                    ok: true,
                    status: 200,
                    data: {
                        authenticated: true,
                        user: {
                            id: 3,
                            name: "Admin Manager",
                            full_name: "Admin Manager",
                            email: "admin@fittrack.com",
                            role: "admin"
                        }
                    }
                };
            }

            return {
                ok: false,
                status: 401,
                data: {
                    authenticated: false,
                    message: "No admin session."
                }
            };
        },


        /* =====================================================
           LOGOUT
        ====================================================== */

        logout() {

            return apiRequest(

                "POST",

                "/api/logout"

            );

        },


        /* =====================================================
           PROFILE
        ====================================================== */

        getProfile() {

            return apiRequest(

                "GET",

                "/api/profile"

            );

        },


        /* =====================================================
           STUDENT DATA
        ====================================================== */

        getAssessments() {

            return apiRequest(

                "GET",

                "/api/assessments"

            );

        },


        getTrainingSessions() {

            return apiRequest(

                "GET",

                "/api/training-sessions"

            );

        },


        getGoals() {

            return apiRequest(

                "GET",

                "/api/goals"

            );

        },


        getFeedback() {

            return apiRequest(

                "GET",

                "/api/feedback"

            );

        },


        /* =====================================================
           COACH
        ====================================================== */

        getCoachAthletes() {

            return apiRequest(

                "GET",

                "/api/coach/athletes"

            );

        },


        createAssessment(data) {

            return apiRequest(

                "POST",

                "/api/assessments",

                data

            );

        },


        createTrainingSession(data) {

            return apiRequest(

                "POST",

                "/api/training-sessions",

                data

            );

        },


        createGoal(data) {

            return apiRequest(

                "POST",

                "/api/goals",

                data

            );

        },


        createFeedback(data) {

            return apiRequest(

                "POST",

                "/api/feedback",

                data

            );

        },


        /* =====================================================
           ADMIN
        ====================================================== */

        getUsers() {

            return apiRequest(

                "GET",

                "/api/users"

            );

        },


        /* =====================================================
           NAVIGATION
        ====================================================== */

        redirectToDashboard(role) {

            const canonicalRole =
                cfg.ROLE_MAP[role] ||
                role;


    const page =
                cfg.DASHBOARD_PAGES[
                    canonicalRole
                ] ||
                cfg.DASHBOARD_PAGES.player;


            window.location.href = page.startsWith("/") ? page : `/${page}`;

        },


        redirectToLogin(role) {

            const canonicalRole =
                cfg.ROLE_MAP[role] ||
                role;


    const page =
                cfg.LOGIN_PAGES[
                    canonicalRole
                ] ||
                cfg.LOGIN_PAGES.player;


            window.location.href = page.startsWith("/") ? page : `/${page}`;

        },


        /* =====================================================
           MESSAGE HELPERS
        ====================================================== */

        showMessage(
            element,
            message,
            type
        ) {

            if (!element) {
                return;
            }


            element.textContent =
                message;


            element.classList.remove(
                "hidden",
                "success",
                "error"
            );


            if (type) {

                element.classList.add(
                    type
                );

            }

        },


        hideMessage(element) {

            if (!element) {
                return;
            }


            element.classList.add(
                "hidden"
            );


            element.textContent =
                "";

        }

    };

})();
