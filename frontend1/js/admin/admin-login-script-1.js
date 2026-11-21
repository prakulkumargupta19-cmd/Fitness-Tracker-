

    /* =====================================================
        PASSWORD VISIBILITY
    ====================================================== */

    const password =
        document.getElementById("password");

    const togglePassword =
        document.getElementById("togglePassword");


    function togglePasswordVisibility() {

        if (password.type === "password") {

            password.type = "text";

            togglePassword.setAttribute(
                "aria-label",
                "Hide password"
            );

            togglePassword.innerHTML = `
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                >
                    <path
                        d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"
                    ></path>

                    <path
                        d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"
                    ></path>

                    <path
                        d="M14.12 14.12a3 3 0 1 1-4.24-4.24"
                    ></path>

                    <line
                        x1="1"
                        y1="1"
                        x2="23"
                        y2="23"
                    ></line>

                </svg>
            `;

        } else {

            password.type = "password";

            togglePassword.setAttribute(
                "aria-label",
                "Show password"
            );

            togglePassword.innerHTML = `
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                >

                    <path
                        d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"
                    ></path>

                    <circle
                        cx="12"
                        cy="12"
                        r="3"
                    ></circle>

                </svg>
            `;

        }

    }


    togglePassword.addEventListener(
        "click",
        togglePasswordVisibility
    );


    togglePassword.addEventListener(
        "keydown",
        function(event) {

            if (
                event.key === "Enter" ||
                event.key === " "
            ) {

                event.preventDefault();

                togglePasswordVisibility();

            }

        }
    );


    /* =====================================================
        BACKEND
    ===================================================== */

    const API_URL = window.FITNESS_API_BASE || "";


    /* =====================================================
        ADMIN LOGIN
    ===================================================== */

    const form =
        document.getElementById("adminLoginForm");

    form.addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();


            const email =
                document
                    .getElementById("email")
                    .value
                    .trim()
                    .toLowerCase();


            const passwordValue =
                document
                    .getElementById("password")
                    .value;


            const errorMessage =
                document.getElementById(
                    "errorMessage"
                );


            const loginButton =
                document.getElementById(
                    "loginButton"
                );


            /* ---------------------------------------------
               VALIDATION
            --------------------------------------------- */

            if (!email || !passwordValue) {

                errorMessage.textContent =
                    "Please enter your email and password.";

                errorMessage.style.display =
                    "block";

                return;

            }


            errorMessage.style.display =
                "none";


            loginButton.disabled =
                true;

            loginButton.textContent =
                "Signing in...";


            /* ---------------------------------------------
               SEND LOGIN REQUEST
            --------------------------------------------- */

            try {

                const response =
                    await fetch(
                        API_URL + "/api/admin-login",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            credentials:
                                "include",

                            body:
                                JSON.stringify({
                                    email:
                                        email,

                                    password:
                                        passwordValue,

                                    role:
                                        "admin"
                                })
                        }
                    );


                const result =
                    await response.json();


                /* -----------------------------------------
                   LOGIN FAILED
                ----------------------------------------- */

                if (
                    !response.ok ||
                    result.success !== true
                ) {

                    throw new Error(
                        result.message ||
                        "Unable to log in."
                    );

                }

                if (!result.otp_required || !result.user || result.user.role !== "admin") {
                    throw new Error("The server did not confirm administrator login verification.");
                }


                loginButton.textContent =
                    "Login successful...";


                setTimeout(
                    function() {

                        window.location.href =
                            "../shared/login-otp.html?role=admin";

                    },
                    300
                );

            }


            /* ---------------------------------------------
               ERROR HANDLING
            --------------------------------------------- */

            catch(error) {

                console.error(
                    "ADMIN LOGIN ERROR:",
                    error
                );


                errorMessage.textContent =
                    error.message ||
                    "Unable to connect to the server.";


                errorMessage.style.display =
                    "block";


                loginButton.disabled =
                    false;

                loginButton.textContent =
                    "Login as Admin →";

            }

        }
    );

