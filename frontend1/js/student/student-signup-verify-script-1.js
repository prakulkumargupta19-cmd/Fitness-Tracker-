

    /* =========================================================
       ELEMENTS
    ========================================================= */

    const otpInputs =
        document.querySelectorAll(".otp-input");

    const verifyButton =
        document.getElementById("verifyButton");

    const resendButton =
        document.getElementById("resendButton");

    const message =
        document.getElementById("message");

    const timerElement =
        document.getElementById("timer");

    const userEmail =
        document.getElementById("userEmail");


    /* =========================================================
       API BASE URL
       
    API base can be overridden through FITNESS_API_BASE.
    ========================================================= */

    const API_BASE = window.FITNESS_API_BASE || "";


    /* =========================================================
       GET SIGNUP EMAIL
    ========================================================= */

    const email =
        sessionStorage.getItem("signupEmail");


    if (!email) {

        showMessage(
            "Signup session not found. Please register again.",
            "error"
        );

        verifyButton.disabled = true;
        resendButton.disabled = true;

    } else {

        userEmail.textContent =
            maskEmail(email);

    }


    /* =========================================================
       MASK EMAIL
    ========================================================= */

    function maskEmail(email) {

        const parts =
            email.split("@");

        if (parts.length !== 2) {
            return email;
        }

        const username =
            parts[0];

        const domain =
            parts[1];

        if (username.length <= 2) {

            return (
                "*".repeat(username.length) +
                "@" +
                domain
            );

        }

        return (
            username.charAt(0) +
            "*".repeat(username.length - 2) +
            username.charAt(username.length - 1) +
            "@" +
            domain
        );
    }


    /* =========================================================
       SHOW MESSAGE
    ========================================================= */

    function showMessage(text, type) {

        message.textContent = text;

        message.className =
            "message " + type;
    }


    /* =========================================================
       GET OTP
    ========================================================= */

    function getOTP() {

        return Array.from(otpInputs)
            .map(input => input.value)
            .join("");

    }


    /* =========================================================
       OTP INPUT HANDLING
    ========================================================= */

    otpInputs.forEach((input, index) => {

        input.addEventListener(
            "input",
            function () {

                this.value =
                    this.value
                        .replace(/\D/g, "")
                        .slice(0, 1);

                if (
                    this.value &&
                    index < otpInputs.length - 1
                ) {

                    otpInputs[index + 1].focus();

                }

            }
        );


        input.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key === "Backspace" &&
                    !this.value &&
                    index > 0
                ) {

                    otpInputs[index - 1].focus();

                }


                if (
                    event.key === "ArrowLeft" &&
                    index > 0
                ) {

                    otpInputs[index - 1].focus();

                }


                if (
                    event.key === "ArrowRight" &&
                    index < otpInputs.length - 1
                ) {

                    otpInputs[index + 1].focus();

                }

            }
        );


        input.addEventListener(
            "paste",
            function (event) {

                event.preventDefault();

                const pastedData =
                    event.clipboardData
                        .getData("text")
                        .replace(/\D/g, "")
                        .slice(0, 6);


                pastedData
                    .split("")
                    .forEach((digit, i) => {

                        if (otpInputs[i]) {

                            otpInputs[i].value =
                                digit;

                        }

                    });


                if (pastedData.length > 0) {

                    otpInputs[
                        Math.min(
                            pastedData.length - 1,
                            5
                        )
                    ].focus();

                }

            }
        );

    });


    /* =========================================================
       TIMER
    ========================================================= */

    let timeLeft = 120;

    let countdown;


    function startTimer() {

        clearInterval(countdown);

        timeLeft = 120;

        resendButton.disabled = true;

        timerElement.textContent =
            "02:00";


        countdown =
            setInterval(() => {

                timeLeft--;


                const minutes =
                    Math.floor(timeLeft / 60);

                const seconds =
                    timeLeft % 60;


                timerElement.textContent =
                    String(minutes).padStart(2, "0") +
                    ":" +
                    String(seconds).padStart(2, "0");


                if (timeLeft <= 0) {

                    clearInterval(countdown);

                    timerElement.textContent =
                        "Expired";

                    resendButton.disabled =
                        false;

                }

            }, 1000);

    }


    /* =========================================================
       VERIFY OTP
       
       REAL BACKEND API
    ========================================================= */

    verifyButton.addEventListener(
        "click",
        async function () {

            const otp =
                getOTP();


            /* -------------------------
               VALIDATION
            ------------------------- */

            if (!email) {

                showMessage(
                    "Signup session expired. Please register again.",
                    "error"
                );

                return;

            }


            if (otp.length !== 6) {

                showMessage(
                    "Please enter the complete 6-digit OTP.",
                    "error"
                );

                return;

            }


            if (timeLeft <= 0) {

                showMessage(
                    "This OTP has expired. Please request a new OTP.",
                    "error"
                );

                return;

            }


            /* -------------------------
               LOADING STATE
            ------------------------- */

            verifyButton.disabled =
                true;

            resendButton.disabled =
                true;

            verifyButton.textContent =
                "Verifying...";


            try {

                /* =================================================
                   SEND OTP TO FLASK BACKEND
                ================================================= */

                const response =
                    await fetch(
                        `${API_BASE}/api/account-verification/verify`,
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
                                    email: email,
                                    otp: otp
                                })
                        }
                    );


                /* -------------------------
                   READ RESPONSE
                ------------------------- */

                const data =
                    await response
                        .json()
                        .catch(() => ({}));


                console.log(
                    "SIGNUP OTP VERIFICATION:",
                    response.status,
                    data
                );


                /* -------------------------
                   VERIFICATION FAILED
                ------------------------- */

                if (!response.ok ||
                    data.success !== true) {

                    throw new Error(
                        data.message ||
                        "OTP verification failed."
                    );

                }


                /* =================================================
                   ACCOUNT CREATED SUCCESSFULLY
                ================================================= */

                showMessage(
                    "Account verified. Continue to complete your profile...",
                    "success"
                );


                /*
                 * Save the email temporarily so the
                 * Student Login page can use it.
                 */
                sessionStorage.setItem(
                    "studentEmail",
                    email
                );


                /*
                 * The signup email has now been
                 * successfully verified.
                 */
                sessionStorage.removeItem(
                    "signupEmail"
                );


                /*
                 * Stop the timer.
                 */
                clearInterval(countdown);


                verifyButton.textContent =
                    "Verified";


                /* =================================================
                   REDIRECT TO PROFILE SETUP
                ================================================= */

                setTimeout(
                    function () {

                        window.location.replace(
                            "student-signup.html?step=basic"
                        );

                    },
                    1000
                );

            }


            catch (error) {

                console.error(
                    "Student signup OTP error:",
                    error
                );


                showMessage(
                    error.message ||
                    "Unable to verify OTP. Please try again.",
                    "error"
                );


                verifyButton.disabled =
                    false;

                resendButton.disabled =
                    timeLeft <= 0;

                verifyButton.textContent =
                    "Verify OTP";

            }

        }
    );


    /* =========================================================
       RESEND OTP
       
       REAL BACKEND API
    ========================================================= */

    resendButton.addEventListener(
        "click",
        async function () {

            if (!email) {

                showMessage(
                    "Signup session expired. Please register again.",
                    "error"
                );

                return;

            }


            resendButton.disabled =
                true;

            verifyButton.disabled =
                true;

            resendButton.textContent =
                "Sending...";


            try {

                /* =================================================
                   REQUEST NEW OTP
                ================================================= */

                const response =
                    await fetch(
                        `${API_BASE}/api/account-verification/send`,
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
                                    email: email
                                })
                        }
                    );


                const data =
                    await response
                        .json()
                        .catch(() => ({}));


                console.log(
                    "RESEND OTP:",
                    response.status,
                    data
                );


                if (!response.ok ||
                    data.success !== true) {

                    throw new Error(
                        data.message ||
                        "Unable to resend OTP."
                    );

                }


                /* -------------------------
                   CLEAR OLD OTP
                ------------------------- */

                otpInputs.forEach(
                    input => {
                        input.value = "";
                    }
                );


                otpInputs[0].focus();


                showMessage(
                    "A new OTP has been sent to your email.",
                    "success"
                );


                resendButton.textContent =
                    "Resend OTP";


                verifyButton.disabled =
                    false;


                /* -------------------------
                   RESTART TIMER
                ------------------------- */

                startTimer();

            }


            catch (error) {

                console.error(
                    "Resend OTP error:",
                    error
                );


                showMessage(
                    error.message ||
                    "Unable to resend OTP.",
                    "error"
                );


                resendButton.disabled =
                    false;

                verifyButton.disabled =
                    false;

                resendButton.textContent =
                    "Resend OTP";

            }

        }
    );


    /* =========================================================
       START TIMER
    ========================================================= */

    startTimer();

