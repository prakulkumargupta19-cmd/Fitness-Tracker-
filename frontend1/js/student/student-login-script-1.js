
"use strict";


/* =========================================================
   API
========================================================= */

const API_BASE = window.FITNESS_API_BASE || "";


/* =========================================================
   ELEMENTS
========================================================= */

const loginForm =
    document.getElementById("studentLoginForm");

const emailInput =
    document.getElementById("email");

const passwordInput =
    document.getElementById("password");

const rememberInput =
    document.getElementById("remember");

const loginButton =
    document.getElementById("loginButton");

const errorMessage =
    document.getElementById("errorMessage");

const togglePasswordButton =
    document.getElementById("togglePassword");


/* =========================================================
   MESSAGE
========================================================= */

function showMessage(text, type = "error") {

    errorMessage.textContent = text;

    errorMessage.style.display = "block";


    if (type === "success") {

        errorMessage.style.background = "#ecfdf3";

        errorMessage.style.color = "#166534";

        errorMessage.style.borderColor = "#bbf7d0";

    } else {

        errorMessage.style.background = "#fff1f2";

        errorMessage.style.color = "#be123c";

        errorMessage.style.borderColor = "#fecdd3";
    }
}


function clearMessage() {

    errorMessage.textContent = "";

    errorMessage.style.display = "none";
}


/* =========================================================
   PASSWORD TOGGLE
========================================================= */

togglePasswordButton.addEventListener(
    "click",
    function () {

        const isPassword =
            passwordInput.type === "password";


        if (isPassword) {

            passwordInput.type = "text";


            togglePasswordButton.innerHTML = `
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round">

                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24">
                    </path>

                    <line
                        x1="1"
                        y1="1"
                        x2="23"
                        y2="23">
                    </line>

                </svg>
            `;


            togglePasswordButton.setAttribute(
                "aria-label",
                "Hide password"
            );


        } else {

            passwordInput.type = "password";


            togglePasswordButton.innerHTML = `
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round">

                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z">
                    </path>

                    <circle
                        cx="12"
                        cy="12"
                        r="3">
                    </circle>

                </svg>
            `;


            togglePasswordButton.setAttribute(
                "aria-label",
                "Show password"
            );
        }

    }
);


/* =========================================================
   REMEMBERED EMAIL
========================================================= */

const savedEmail =
    sessionStorage.getItem("student_login_email");


if (savedEmail) {

    emailInput.value = savedEmail;

    rememberInput.checked = true;
}


/* =========================================================
   STUDENT LOGIN
========================================================= */

loginForm.addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();

        clearMessage();


        /* -----------------------------------------------------
           GET VALUES
        ----------------------------------------------------- */

        const email =
            emailInput.value.trim().toLowerCase();

        const password =
            passwordInput.value;

        const remember =
            rememberInput.checked;


        /* -----------------------------------------------------
           VALIDATION
        ----------------------------------------------------- */

        if (!email) {

            showMessage(
                "Please enter your student email."
            );

            emailInput.focus();

            return;
        }


        if (!email.includes("@")) {

            showMessage(
                "Please enter a valid email address."
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


        /* -----------------------------------------------------
           DISABLE BUTTON
        ----------------------------------------------------- */

        loginButton.disabled = true;

        loginButton.textContent =
            "Signing in...";


        try {

            /* =================================================
               LOGIN REQUEST
            ================================================= */

            const csrfResponse = await fetch(
                API_BASE + "/api/csrf-token",
                { credentials: "include" }
            );
            const csrfData = await csrfResponse.json().catch(() => ({}));
            if (!csrfResponse.ok || !csrfData.csrf_token) {
                throw new Error("Unable to start a secure login session. Please refresh and try again.");
            }

            const response =
                await fetch(
                    API_BASE + "/api/login",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": csrfData.csrf_token
                        },

                        /*
                         * IMPORTANT:
                         * This allows the browser to keep/send
                         * the Flask session cookie.
                         */

                        credentials: "include",

                        body: JSON.stringify({

                            email: email,

                            password: password,

                            role: "student"

                        })
                    }
                );


            /* -------------------------------------------------
               READ RESPONSE
            ------------------------------------------------- */

            let data = {};

            try {

                data = await response.json();

            } catch (error) {

                data = {};

            }


            /* =================================================
               LOGIN FAILED
            ================================================= */

            if (!response.ok || !data.success) {

                showMessage(
                    data.message ||
                    "Invalid student email or password."
                );

                loginButton.disabled = false;

                loginButton.textContent =
                    "Login as Student →";

                return;
            }


            /* =================================================
               CHECK USER
            ================================================= */

            if (!data.user) {

                showMessage(
                    "Login succeeded, but user information was not returned."
                );

                loginButton.disabled = false;

                loginButton.textContent =
                    "Login as Student →";

                return;
            }


            /* =================================================
               CHECK STUDENT ROLE
            ================================================= */

            const role =
                String(data.user.role || "")
                    .toLowerCase();


            if (
                role !== "student" &&
                role !== "player"
            ) {

                showMessage(
                    "This account is not registered as a student."
                );

                loginButton.disabled = false;

                loginButton.textContent =
                    "Login as Student →";

                return;
            }


            /* =================================================
               REMEMBER EMAIL
            ================================================= */

            if (remember) {

                sessionStorage.setItem(
                    "student_login_email",
                    email
                );

            } else {

                sessionStorage.removeItem(
                    "student_login_email"
                );
            }


            /* =================================================
               LOGIN SUCCESS
            ================================================= */

            const sessionResponse = await fetch(API_BASE + "/api/session", {
                credentials: "include"
            });
            const sessionData = await sessionResponse.json().catch(() => ({}));
            const sessionRole = String(sessionData.user?.role || "").toLowerCase();
            if (!sessionResponse.ok || !sessionData.authenticated || !["student", "player"].includes(sessionRole)) {
                throw new Error("Login succeeded, but the student session could not be confirmed.");
            }

            showMessage("Login successful. Redirecting...", "success");
            loginButton.textContent = "Opening dashboard...";
            window.location.replace("student-dashboard.html");


        } catch (error) {

            console.error(
                "Student login error:",
                error
            );


            showMessage(
                error.message ||
                "Unable to connect to the server. Please check that Flask is running."
            );


            loginButton.disabled = false;

            loginButton.textContent =
                "Login as Student →";
        }

    }
);
