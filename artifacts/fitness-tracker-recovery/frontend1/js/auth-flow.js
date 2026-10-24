/* ================================================================
   AUTH FLOW
   Fitness Performance Tracker
   ================================================================

   ROLE FLOW

   ADMIN
   -----
   /api/login
        ↓
   OTP
        ↓
   /api/login/verify-otp
        ↓
   Admin Dashboard


   COACH
   -----
   /api/login
        ↓
   Direct Flask Session
        ↓
   Coach Dashboard


   STUDENT
   -------
   /api/login
        ↓
   Direct Flask Session
        ↓
   Student Dashboard


   IMPORTANT
   ----------
   There is NO /api/coach-login endpoint.

   Coaches use:

       POST /api/login

   with:

       {
           email,
           password,
           role: "coach"
       }

================================================================ */


/* ================================================================
   API BASE
================================================================ */

const API_BASE =
    window.FITNESS_API_BASE ||
    window.APP_CONFIG?.API_BASE ||
    "";


/* ================================================================
   HELPERS
================================================================ */

function getPageName() {

    return window.location.pathname
        .split("/")
        .pop()
        .toLowerCase();

}


function getRoleFromPage() {

    const path =
        window.location.pathname.toLowerCase();


    if (
        path.includes("/admin/") ||
        path.includes("admin-login") ||
        path.includes("admin-dashboard")
    ) {

        return "admin";

    }


    if (
        path.includes("/coach/") ||
        path.includes("coach-login") ||
        path.includes("coach-dashboard")
    ) {

        return "coach";

    }


    if (
        path.includes("/student/") ||
        path.includes("student-login") ||
        path.includes("student-dashboard")
    ) {

        return "student";

    }


    return null;

}


function canonicalRole(role) {

    role =
        String(role || "").toLowerCase().trim();


    if (role === "student") {

        return "player";

    }


    return role;

}


function dashboardForRole(role) {

    role =
        canonicalRole(role);


    if (role === "admin") {

        return "/admin/admin-dashboard.html";

    }


    if (role === "coach") {

        return "/coach/coach-dashboard.html";

    }


    if (role === "player") {

        return "/student/student-dashboard.html";

    }


    return "/";

}


function showAuthMessage(
    element,
    text,
    type = "error"
) {

    if (!element) {

        return;

    }


    element.textContent =
        text;


    element.className =
        `message ${type}`;

}


/* ================================================================
   SAFE JSON
================================================================ */

async function safeJson(response) {

    try {

        return await response.json();

    } catch (error) {

        return {};

    }

}


/* ================================================================
   LOGIN
================================================================ */

async function handleLoginForm(form) {

    const emailInput =
        form.querySelector(
            'input[type="email"], input[name="email"], #email'
        );


    const passwordInput =
        form.querySelector(
            'input[type="password"], input[name="password"], #password'
        );


    const messageElement =
        form.querySelector(
            "#message, .message"
        );


    const submitButton =
        form.querySelector(
            'button[type="submit"]'
        );


    if (!emailInput || !passwordInput) {

        return;

    }


    const email =
        emailInput.value.trim();

    const password =
        passwordInput.value;


    if (!email || !password) {

        showAuthMessage(
            messageElement,
            "Please enter your email and password."
        );

        return;

    }


    const pageRole =
        getRoleFromPage();


    /*
     * If this is a coach login page, force the role to coach.
     */

    let role =
        pageRole;


    if (!role) {

        role = "student";

    }


    if (submitButton) {

        submitButton.disabled = true;

        submitButton.dataset.originalText =
            submitButton.textContent;

        submitButton.textContent =
            "Signing in...";

    }


    try {

        /*
         * ALL NORMAL LOGIN REQUESTS USE /api/login.
         *
         * There is deliberately no /api/coach-login.
         */

        const response =
            await fetch(
                `${API_BASE}/api/login`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    credentials: "include",

                    body: JSON.stringify({

                        email: email,

                        password: password,

                        role: role

                    })

                }
            );


        const data =
            await safeJson(response);


        if (!response.ok || !data.success) {

            throw new Error(
                data.message ||
                "Invalid email or password."
            );

        }


        const returnedUser =
            data.user || {};


        const returnedRole =
            canonicalRole(
                returnedUser.role || role
            );


        /*
         * ============================================================
         * COACH
         * ============================================================
         *
         * Coach authentication is password-only.
         *
         * The backend already created the Flask session.
         */

        if (returnedRole === "coach") {

            if (pageRole && pageRole !== "coach") {

                throw new Error(
                    "This account does not belong to this login page."
                );

            }


            showAuthMessage(
                messageElement,
                "Coach login successful. Redirecting...",
                "success"
            );


            setTimeout(
                function () {

                    window.location.href =
                        dashboardForRole("coach");

                },
                300
            );


            return;

        }


        if (returnedRole === "player") {
            if (pageRole && pageRole !== "student") {
                throw new Error(
                    "This account does not belong to this login page."
                );
            }

            showAuthMessage(
                messageElement,
                "Student login successful. Redirecting...",
                "success"
            );

            setTimeout(function () {
                window.location.href = dashboardForRole("player");
            }, 300);

            return;
        }

        /*
         * Administrator sign-in requires an OTP confirmation.
         */
        if (returnedRole === "admin") {

            /*
             * Store email temporarily so the OTP page knows
             * which account is being verified.
             */

            sessionStorage.setItem(
                "otp_email",
                email
            );


            sessionStorage.setItem(
                "otp_role",
                returnedRole
            );


            /*
             * The backend may return an explicit OTP-required
             * response or the login endpoint may already indicate
             * that verification is required.
             */

            showAuthMessage(
                messageElement,
                "Verification code sent. Redirecting...",
                "success"
            );


            setTimeout(
                function () {

                    window.location.href =
                        "/admin/admin-loginotp.html";

                },
                300
            );


            return;

        }


        /*
         * Unknown role
         */

        throw new Error(
            "Unable to determine account role."
        );


    } catch (error) {

        console.error(
            "Login error:",
            error
        );


        showAuthMessage(
            messageElement,
            error.message ||
            "Login failed. Please try again."
        );


        if (submitButton) {

            submitButton.disabled = false;

            submitButton.textContent =
                submitButton.dataset.originalText ||
                "Login";

        }

    }

}


/* ================================================================
   SIGNUP
================================================================ */

async function handleSignupForm(form) {

    const emailInput =
        form.querySelector(
            'input[type="email"], input[name="email"], #email'
        );


    const passwordInput =
        form.querySelector(
            'input[type="password"], input[name="password"], #password'
        );


    const nameInput =
        form.querySelector(
            'input[name="name"], #name'
        );


    const messageElement =
        form.querySelector(
            "#message, .message"
        );


    if (!emailInput || !passwordInput) {

        return;

    }


    const email =
        emailInput.value.trim();

    const password =
        passwordInput.value;

    const name =
        nameInput
            ? nameInput.value.trim()
            : "";


    const role =
        getRoleFromPage() || "student";


    try {

        const response =
            await fetch(
                `${API_BASE}/api/signup`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    credentials: "include",

                    body: JSON.stringify({

                        name: name,

                        email: email,

                        password: password,

                        role: role

                    })

                }
            );


        const data =
            await safeJson(response);


        if (!response.ok || !data.success) {

            throw new Error(
                data.message ||
                "Unable to create account."
            );

        }


        sessionStorage.setItem(
            "otp_email",
            email
        );


        sessionStorage.setItem(
            "otp_role",
            canonicalRole(role)
        );


        showAuthMessage(
            messageElement,
            data.message ||
            "Verification code sent.",
            "success"
        );


    } catch (error) {

        showAuthMessage(
            messageElement,
            error.message ||
            "Signup failed."
        );

    }

}


/* ================================================================
   LOGOUT
================================================================ */

async function logoutUser(role = null) {

    role =
        canonicalRole(
            role || getRoleFromPage()
        );


    let endpoint =
        "/api/logout";


    if (role === "admin") {

        endpoint =
            "/api/admin/logout";

    }


    try {

        await fetch(
            `${API_BASE}${endpoint}`,
            {
                method: "POST",

                credentials: "include"
            }
        );

    } catch (error) {

        console.error(
            "Logout error:",
            error
        );

    }


    sessionStorage.clear();


    window.location.href =
        role === "admin"
            ? "/admin/admin-login.html"
            : role === "coach"
                ? "/coach/coach-login.html"
                : "/student/student-login.html";

}


/* ================================================================
   SESSION CHECK
================================================================ */

async function checkSession(requiredRole = null) {

    try {

        const response =
            await fetch(
                `${API_BASE}/api/session`,
                {
                    method: "GET",

                    credentials: "include",

                    cache: "no-store"
                }
            );


        if (!response.ok) {

            return null;

        }


        const data =
            await safeJson(response);


        if (!data.success || !data.authenticated) {

            return null;

        }


        const user =
            data.user || {};


        const actualRole =
            canonicalRole(
                user.role
            );


        if (
            requiredRole &&
            canonicalRole(requiredRole) !== actualRole
        ) {

            return null;

        }


        return user;


    } catch (error) {

        console.error(
            "Session check error:",
            error
        );


        return null;

    }

}


/* ================================================================
   PROTECT DASHBOARD
================================================================ */

async function protectDashboard(requiredRole) {

    const user =
        await checkSession(requiredRole);


    if (user) {

        return user;

    }


    const role =
        canonicalRole(
            requiredRole
        );


    window.location.replace(
        dashboardLoginForRole(role)
    );


    return null;

}


function dashboardLoginForRole(role) {

    if (role === "admin") {

        return "/admin/admin-login.html";

    }


    if (role === "coach") {

        return "/coach/coach-login.html";

    }


    return "/student/student-login.html";

}


/* ================================================================
   LOGIN PAGE AUTO SETUP
================================================================ */

function setupLoginPage() {

    const page =
        getPageName();


    if (!page.endsWith("-login.html")) {

        return;

    }


    /*
     * Coach-login.html has its own login handler because it contains
     * the complete coach-specific UI.
     *
     * Therefore auth-flow.js does NOT attach another submit handler
     * to coach-login.html.
     *
     * This prevents duplicate login requests.
     */

    if (page === "coach-login.html") {

        return;

    }


    const form =
        document.querySelector(
            "#loginForm"
        );


    if (!form) {

        return;

    }


    form.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();

            handleLoginForm(form);

        }
    );

}


/* ================================================================
   SIGNUP PAGE AUTO SETUP
================================================================ */

function setupSignupPage() {

    const page =
        getPageName();


    if (!page.includes("signup")) {

        return;

    }


    const form =
        document.querySelector(
            "#signupForm, form"
        );


    if (!form) {

        return;

    }


    form.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();

            handleSignupForm(form);

        }
    );

}


/* ================================================================
   LOGOUT BUTTONS
================================================================ */

function setupLogoutButtons() {

    const logoutButtons =
        document.querySelectorAll(
            "[data-logout], #logoutBtn, .logout-btn"
        );


    logoutButtons.forEach(
        function (button) {

            button.addEventListener(
                "click",
                async function (event) {

                    event.preventDefault();

                    const role =
                        button.dataset.role ||
                        getRoleFromPage();

                    await logoutUser(role);

                }
            );

        }
    );

}


/* ================================================================
   DASHBOARD PROTECTION
================================================================ */

async function setupDashboardProtection() {

    const page =
        getPageName();


    let requiredRole =
        null;


    if (page === "admin-dashboard.html") {

        requiredRole =
            "admin";

    }


    if (page === "coach-dashboard.html") {

        requiredRole =
            "coach";

    }


    if (page === "student-dashboard.html") {

        requiredRole =
            "student";

    }


    if (!requiredRole) {

        return;

    }


    const user =
        await checkSession(requiredRole);


    if (!user) {

        window.location.replace(
            dashboardLoginForRole(
                canonicalRole(requiredRole)
            )
        );

        return;

    }


    /*
     * Optional: expose logged-in user information
     * to dashboard scripts.
     */

    window.currentUser =
        user;


    document.dispatchEvent(
        new CustomEvent(
            "auth:ready",
            {
                detail: {
                    user: user
                }
            }
        )
    );

}


/* ================================================================
   FORGOT PASSWORD
================================================================ */

async function handleForgotPasswordForm(form) {

    const emailInput =
        form.querySelector(
            'input[type="email"], input[name="email"], #email'
        );


    const messageElement =
        form.querySelector(
            "#message, .message"
        );


    if (!emailInput) {

        return;

    }


    const email =
        emailInput.value.trim();


    if (!email) {

        showAuthMessage(
            messageElement,
            "Please enter your email address."
        );

        return;

    }


    try {

        const response =
            await fetch(
                `${API_BASE}/api/forgot-password`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    credentials: "include",

                    body: JSON.stringify({

                        email: email

                    })

                }
            );


        const data =
            await safeJson(response);


        if (!response.ok || !data.success) {

            throw new Error(
                data.message ||
                "Unable to send reset code."
            );

        }


        sessionStorage.setItem(
            "reset_email",
            email
        );


        showAuthMessage(
            messageElement,
            data.message ||
            "Password reset code sent.",
            "success"
        );


    } catch (error) {

        showAuthMessage(
            messageElement,
            error.message ||
            "Unable to send reset code."
        );

    }

}


/* ================================================================
   FORGOT PASSWORD AUTO SETUP
================================================================ */

function setupForgotPasswordPage() {

    const page =
        getPageName();


    if (
        !page.includes("forgot-password")
    ) {

        return;

    }


    const form =
        document.querySelector(
            "#forgotPasswordForm, form"
        );


    if (!form) {

        return;

    }


    form.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();

            handleForgotPasswordForm(form);

        }
    );

}


/* ================================================================
   RESET PASSWORD
================================================================ */

async function handleResetPasswordForm(form) {

    const emailInput =
        form.querySelector(
            'input[type="email"], input[name="email"], #email'
        );


    const codeInput =
        form.querySelector(
            'input[name="otp"], input[name="code"], #otp, #code'
        );


    const passwordInput =
        form.querySelector(
            'input[name="password"], #password'
        );


    const messageElement =
        form.querySelector(
            "#message, .message"
        );


    if (
        !emailInput ||
        !codeInput ||
        !passwordInput
    ) {

        return;

    }


    const email =
        emailInput.value.trim();

    const otp =
        codeInput.value.trim();

    const password =
        passwordInput.value;


    if (!email || !otp || !password) {

        showAuthMessage(
            messageElement,
            "Please complete all required fields."
        );

        return;

    }


    try {

        const response =
            await fetch(
                `${API_BASE}/api/reset-password`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    credentials: "include",

                    body: JSON.stringify({

                        email: email,

                        otp: otp,

                        password: password

                    })

                }
            );


        const data =
            await safeJson(response);


        if (!response.ok || !data.success) {

            throw new Error(
                data.message ||
                "Unable to reset password."
            );

        }


        showAuthMessage(
            messageElement,
            data.message ||
            "Password reset successful.",
            "success"
        );


        setTimeout(
            function () {

                window.location.href =
                    "/";

            },
            1000
        );


    } catch (error) {

        showAuthMessage(
            messageElement,
            error.message ||
            "Password reset failed."
        );

    }

}


/* ================================================================
   RESET PASSWORD AUTO SETUP
================================================================ */

function setupResetPasswordPage() {

    const page =
        getPageName();


    if (
        !page.includes("reset-password")
    ) {

        return;

    }


    const form =
        document.querySelector(
            "#resetPasswordForm, form"
        );


    if (!form) {

        return;

    }


    form.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();

            handleResetPasswordForm(form);

        }
    );

}


/* ================================================================
   GLOBAL INITIALIZATION
================================================================ */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        setupLoginPage();

        setupSignupPage();

        setupForgotPasswordPage();

        setupResetPasswordPage();

        setupLogoutButtons();

        setupDashboardProtection();

    }
);


/* ================================================================
   GLOBAL EXPORTS
================================================================ */

window.AuthFlow = {

    API_BASE,

    getRoleFromPage,

    canonicalRole,

    dashboardForRole,

    checkSession,

    protectDashboard,

    logoutUser,

    handleLoginForm,

    handleSignupForm,

    handleForgotPasswordForm,

    handleResetPasswordForm

};