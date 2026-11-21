

(function () {

    "use strict";


    /* =====================================================
       ELEMENTS
    ===================================================== */

    const signupForm =
        document.getElementById("signupForm");

    const fullNameInput =
        document.getElementById("fullName");

    const emailInput =
        document.getElementById("studentEmail");

    const mobileNumberInput =
        document.getElementById("mobileNumber");

    const emergencyContactInput =
        document.getElementById("emergencyContact");

    const passwordInput =
        document.getElementById("password");

    const confirmPasswordInput =
        document.getElementById("confirmPassword");

    const termsInput =
        document.getElementById("terms");

    const signupButton =
        document.getElementById("signupButton");

    const buttonText =
        document.getElementById("buttonText");

    const errorMessage =
        document.getElementById("errorMessage");

    const successMessage =
        document.getElementById("successMessage");


    /* =====================================================
       MESSAGE FUNCTIONS
    ===================================================== */

    function showError(message) {

        if (successMessage) {

            successMessage.classList.add("hidden");

            successMessage.textContent = "";

        }

        if (errorMessage) {

            errorMessage.textContent = message;

            errorMessage.classList.remove("hidden");

        }

    }


    function showSuccess(message) {

        if (errorMessage) {

            errorMessage.classList.add("hidden");

            errorMessage.textContent = "";

        }

        if (successMessage) {

            successMessage.textContent = message;

            successMessage.classList.remove("hidden");

        }

    }


    function clearMessages() {

        if (errorMessage) {

            errorMessage.classList.add("hidden");

            errorMessage.textContent = "";

        }

        if (successMessage) {

            successMessage.classList.add("hidden");

            successMessage.textContent = "";

        }

    }


    /* =====================================================
       PASSWORD VISIBILITY
       SAME STYLE AS STUDENT LOGIN PAGE
    ===================================================== */

    function setupPasswordToggle(input, button) {

        if (!input || !button) {
            return;
        }


        button.addEventListener(
            "click",
            function () {

                const isPassword =
                    input.type === "password";


                if (isPassword) {

                    input.type = "text";


                    button.innerHTML = `

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
                                d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"
                            ></path>

                            <line
                                x1="1"
                                y1="1"
                                x2="23"
                                y2="23"
                            ></line>

                        </svg>

                    `;


                    button.setAttribute(
                        "aria-label",
                        "Hide password"
                    );


                } else {

                    input.type = "password";


                    button.innerHTML = `

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


                    button.setAttribute(
                        "aria-label",
                        "Show password"
                    );

                }

            }
        );

    }


    setupPasswordToggle(
        passwordInput,
        document.getElementById("passwordToggle")
    );


    setupPasswordToggle(
        confirmPasswordInput,
        document.getElementById("confirmPasswordToggle")
    );


    /* =====================================================
       SIGNUP
    ===================================================== */

    signupForm.addEventListener(
        "submit",
        async function (event) {

            event.preventDefault();

            clearMessages();


            const fullName =
                fullNameInput.value.trim();

            const email =
                emailInput.value
                    .trim()
                    .toLowerCase();

            const mobileNumber =
                mobileNumberInput.value.trim();

            const emergencyContact =
                emergencyContactInput.value.trim();


            /*
             * Never trim passwords.
             */

            const password =
                passwordInput.value;

            const confirmPassword =
                confirmPasswordInput.value;

            const termsAccepted =
                termsInput.checked;


            /* =================================================
               VALIDATION
            ================================================= */

            if (!fullName) {

                showError(
                    "Please enter your full name."
                );

                fullNameInput.focus();

                return;
            }


            if (!email) {

                showError(
                    "Please enter your email address."
                );

                emailInput.focus();

                return;
            }


            if (
                !email.includes("@") ||
                !email.includes(".")
            ) {

                showError(
                    "Please enter a valid email address."
                );

                emailInput.focus();

                return;
            }


            if (!/^\d{10}$/.test(mobileNumber)) {

                showError(
                    "Please enter a valid 10-digit mobile number."
                );

                mobileNumberInput.focus();

                return;
            }


            if (!/^\d{10}$/.test(emergencyContact)) {

                showError(
                    "Please enter a valid 10-digit emergency contact number."
                );

                emergencyContactInput.focus();

                return;
            }


            if (!password) {

                showError(
                    "Please enter a password."
                );

                passwordInput.focus();

                return;
            }


            if (!confirmPassword) {

                showError(
                    "Please confirm your password."
                );

                confirmPasswordInput.focus();

                return;
            }


            if (password.length < 8) {

                showError(
                    "Password must contain at least 8 characters."
                );

                passwordInput.focus();

                return;
            }


            if (password !== confirmPassword) {

                showError(
                    "Passwords do not match."
                );

                confirmPasswordInput.focus();

                return;
            }


            if (!termsAccepted) {

                showError(
                    "Please accept the Terms & Privacy Policy."
                );

                termsInput.focus();

                return;
            }


            /* =================================================
               DISABLE BUTTON
            ================================================= */

            signupButton.disabled = true;

            buttonText.textContent =
                "Creating Account...";


            try {

                /* =================================================
                   REAL BACKEND REQUEST
                ================================================= */

                const response =
                    await API.register({

                        name: fullName,

                        email: email,

                        password: password,

                        contact_number: mobileNumber,

                        confirm_password:
                            confirmPassword,

                        role: "student"

                    });


                console.log(
                    "STUDENT SIGNUP RESPONSE:",
                    response.status,
                    response.data
                );


                /* =================================================
                   SERVER ERROR
                ================================================= */

                if (
                    !response.ok ||
                    !response.data ||
                    response.data.success !== true
                ) {

                    showError(

                        response.data &&
                        response.data.message

                            ? response.data.message

                            : "Unable to create account. Please try again."

                    );

                    return;
                }


                /* =================================================
                   TEMPORARY SIGNUP DATA
                ================================================= */

                sessionStorage.setItem(
                    "signupEmail",
                    email
                );

                sessionStorage.setItem(
                    "signupName",
                    fullName
                );

                sessionStorage.setItem(
                    "signupMobileNumber",
                    mobileNumber
                );

                sessionStorage.setItem(
                    "signupEmergencyContact",
                    emergencyContact
                );


                /* =================================================
                   SUCCESS MESSAGE
                ================================================= */

                showSuccess(

                    response.data.message ||
                    "OTP sent to your email."

                );


                /* =================================================
                   REDIRECT
                ================================================= */

                setTimeout(
                    function () {

                        window.location.href =
                            "student-signup-verify.html";

                    },
                    500
                );

            }


            catch (error) {

                console.error(
                    "STUDENT SIGNUP ERROR:",
                    error
                );

                showError(
                    "Unable to connect to the server. Please try again."
                );

            }


            finally {

                signupButton.disabled = false;

                buttonText.textContent =
                    "Create Account";

            }

        }
    );

})();

