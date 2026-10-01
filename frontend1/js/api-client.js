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

    async function apiRequest(
        method,
        endpoint,
        body
    ) {

        const apiBase =
            window.FITNESS_API_BASE || cfg.API_BASE || "";

        const url =
            apiBase + endpoint;


        const options = {

            method: method,

            headers: {

                "Content-Type":
                    "application/json"

            },

            credentials:
                "include"

        };


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

        getSession() {

            return apiRequest(

                "GET",

                "/api/session"

            );

        },


        getAdminSession() {

            return apiRequest(

                "GET",

                "/api/admin/session"

            );

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


            window.location.href =
                page;

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


            window.location.href =
                page;

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