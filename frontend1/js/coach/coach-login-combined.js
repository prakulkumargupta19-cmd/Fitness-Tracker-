

        (function () {

            "use strict";


            /* =====================================================
               API BASE URL
            ===================================================== */

            const API_BASE = window.FITNESS_API_BASE || "";



            /* =====================================================
               ELEMENTS
            ===================================================== */

            const loginForm =
                document.getElementById("loginForm");

            const emailInput =
                document.getElementById("email");

            const passwordInput =
                document.getElementById("password");

            const rememberMe =
                document.getElementById("rememberMe");

            const loginButton =
                document.getElementById("loginButton");

            const loginButtonText =
                document.getElementById("loginButtonText");

            const message =
                document.getElementById("message");

            const togglePassword =
                document.getElementById("togglePassword");

            const toggleIcon =
                document.getElementById("toggleIcon");



            /* =====================================================
               SHOW MESSAGE
            ====================================================== */

            function showMessage(
                text,
                type = "error"
            ) {

                message.textContent = text;

                message.className =
                    "message " + type;

            }



            /* =====================================================
               CLEAR MESSAGE
            ====================================================== */

            function clearMessage() {

                message.textContent = "";

                message.className =
                    "message";

            }



            /* =====================================================
               PASSWORD VISIBILITY
            ====================================================== */

            if (
                togglePassword &&
                toggleIcon &&
                passwordInput
            ) {

                togglePassword.addEventListener(
                    "click",
                    function () {

                        const isPassword =
                            passwordInput.type === "password";


                        passwordInput.type =
                            isPassword
                                ? "text"
                                : "password";


                        toggleIcon.innerHTML = isPassword
                            ? '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>'
                            : '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';


                        togglePassword.setAttribute(
                            "aria-label",
                            isPassword
                                ? "Hide password"
                                : "Show password"
                        );


                        togglePassword.setAttribute(
                            "aria-pressed",
                            isPassword
                                ? "true"
                                : "false"
                        );

                    }
                );

            }



            /* =====================================================
               REMEMBER EMAIL

               Only the email is remembered.
               The password is NEVER stored.
            ===================================================== */

            const savedEmail =
                sessionStorage.getItem(
                    "coach_login_email"
                );


            if (savedEmail) {

                emailInput.value =
                    savedEmail;

                rememberMe.checked =
                    true;

            }



            /* =====================================================
               LOGIN
            ===================================================== */

            loginForm.addEventListener(
                "submit",
                async function (event) {

                    event.preventDefault();

                    clearMessage();


                    const email =
                        emailInput.value
                            .trim()
                            .toLowerCase();


                    /*
                     * IMPORTANT:
                     * Do not trim passwords.
                     */

                    const password =
                        passwordInput.value;


                    /* ---------------------------------------------
                       BASIC VALIDATION
                    --------------------------------------------- */

                    if (!email) {

                        showMessage(
                            "Please enter your email address."
                        );

                        emailInput.focus();

                        return;

                    }


                    if (!password) {

                        showMessage(
                            "Please enter your password."
                        );

                        passwordInput.focus();

                        return;

                    }



                    /* ---------------------------------------------
                       DISABLE BUTTON
                    --------------------------------------------- */

                    loginButton.disabled =
                        true;

                    loginButtonText.textContent =
                        "Signing in...";



                    try {

                        /* =========================================
                           STEP 1

                           Authenticate with Flask.
                        ========================================== */

                        const loginResponse =
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
                                        role: "coach"
                                    })
                                }
                            );



                        let loginData = {};


                        try {

                            loginData =
                                await loginResponse.json();

                        } catch (jsonError) {

                            loginData = {};

                        }



                        /* =========================================
                           SERVER LOGIN ERROR
                        ========================================== */

                        if (
                            !loginResponse.ok ||
                            !loginData.success
                        ) {

                            throw new Error(
                                loginData.message ||
                                "Invalid coach email or password."
                            );

                        }

                        if (!loginData.user || loginData.user.role !== "coach") {
                            throw new Error("The server did not confirm coach login.");
                        }

                        /* =========================================
                           STEP 2

                           Check the REAL Flask session.

                           We do NOT trust localStorage,
                           sessionStorage, or a token.
                        ========================================== */

                        const sessionResponse =
                            await fetch(
                                `${API_BASE}/api/session`,
                                {
                                    method: "GET",
                                    credentials: "include"
                                }
                            );


                        let sessionData = {};


                        try {

                            sessionData =
                                await sessionResponse.json();

                        } catch (jsonError) {

                            sessionData = {};

                        }



                        /* =========================================
                           SESSION MUST BE AUTHENTICATED
                        ========================================== */

                        if (
                            !sessionResponse.ok ||
                            !sessionData.authenticated ||
                            !sessionData.user
                        ) {

                            throw new Error(
                                "Login succeeded, but the session could not be established."
                            );

                        }



                        /* =========================================
                           STEP 3

                           Check the ACTUAL DATABASE ROLE
                           returned by the Flask session.
                        ========================================== */

                        const actualRole =
                            String(
                                sessionData.user.role || ""
                            )
                            .trim()
                            .toLowerCase();


                        if (
                            actualRole !== "coach"
                        ) {

                            throw new Error(
                                "This account is not registered as a coach."
                            );

                        }



                        /* =========================================
                           REMEMBER EMAIL
                        ========================================== */

                        if (
                            rememberMe.checked
                        ) {

                            sessionStorage.setItem(
                                "coach_login_email",
                                email
                            );

                        } else {

                            sessionStorage.removeItem(
                                "coach_login_email"
                            );

                        }



                        /* =========================================
                           OPTIONAL DISPLAY INFORMATION

                           These are NOT used for authentication.
                        ========================================== */

                        if (
                            sessionData.user.name
                        ) {

                            sessionStorage.setItem(
                                "coachName",
                                sessionData.user.name
                            );

                        }


                        if (
                            sessionData.user.id
                        ) {

                            sessionStorage.setItem(
                                "coachId",
                                String(
                                    sessionData.user.id
                                )
                            );

                        }



                        /* =========================================
                           SUCCESS
                        ========================================== */

                        showMessage(
                            "Login successful. Redirecting...",
                            "success"
                        );



                        /* =========================================
                           REDIRECT
                        ========================================== */

                        setTimeout(
                            function () {

                                window.location.assign(
                                    "coach-dashboard.html"
                                );

                            },
                            300
                        );

                    }


                    catch (error) {

                        console.error(
                            "Coach login error:",
                            error
                        );


                        showMessage(
                            error.message ||
                            "Unable to login. Please try again."
                        );


                        loginButton.disabled =
                            false;

                        loginButtonText.textContent =
                            "Sign In";

                    }

                }
            );

        })();

    
        if (new URLSearchParams(window.location.search).get("reset") === "success") {
            const message = document.getElementById("message");
            if (message) {
                message.textContent = "Password reset successfully. You can now log in.";
                message.className = "message success";
            }
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    