
        const API_BASE = window.FITNESS_API_BASE || "";

        const otpInputs = document.querySelectorAll(".otp-input");
        const verifyButton = document.getElementById("verifyButton");
        const resendButton = document.getElementById("resendButton");
        const message = document.getElementById("message");
        const timerElement = document.getElementById("timer");
        const userEmail = document.getElementById("userEmail");

        const resetEmail = sessionStorage.getItem("resetEmail");

        sessionStorage.removeItem("otpVerified");
        sessionStorage.removeItem("resetOtp");

        if (!resetEmail) {
            userEmail.textContent = "No email found";
            verifyButton.disabled = true;
            showMessage(
                "Please start the password reset process again.",
                "error"
            );
        } else {
            userEmail.textContent = maskEmail(resetEmail);
        }

        function maskEmail(email) {
            const parts = email.split("@");
            if (parts.length !== 2) return email;

            const username = parts[0];
            const domain = parts[1];

            if (username.length <= 2) {
                return "*".repeat(username.length) + "@" + domain;
            }

            return (
                username.charAt(0) +
                "*".repeat(username.length - 2) +
                username.charAt(username.length - 1) +
                "@" +
                domain
            );
        }

        function showMessage(text, type) {
            message.textContent = text;
            message.className = "message " + type;
        }

        function getOTP() {
            return Array.from(otpInputs).map(input => input.value).join("");
        }

        otpInputs.forEach((input, index) => {
            input.addEventListener("input", function () {
                this.value = this.value.replace(/\D/g, "").slice(0, 1);
                if (this.value && index < otpInputs.length - 1) {
                    otpInputs[index + 1].focus();
                }
            });

            input.addEventListener("keydown", function (event) {
                if (event.key === "Backspace" && !this.value && index > 0) {
                    otpInputs[index - 1].focus();
                }
                if (event.key === "ArrowLeft" && index > 0) {
                    otpInputs[index - 1].focus();
                }
                if (event.key === "ArrowRight" && index < otpInputs.length - 1) {
                    otpInputs[index + 1].focus();
                }
            });

            input.addEventListener("paste", function (event) {
                event.preventDefault();
                const pastedData = event.clipboardData
                    .getData("text")
                    .replace(/\D/g, "")
                    .slice(0, 6);

                pastedData.split("").forEach((digit, i) => {
                    if (otpInputs[i]) otpInputs[i].value = digit;
                });

                if (pastedData.length > 0) {
                    otpInputs[Math.min(pastedData.length - 1, 5)].focus();
                }
            });
        });

        let timeLeft = 120;
        let countdown = null;

        function startTimer() {
            clearInterval(countdown);
            timeLeft = 120;
            resendButton.disabled = true;
            updateTimer();

            countdown = setInterval(() => {
                timeLeft--;
                updateTimer();

                if (timeLeft <= 0) {
                    clearInterval(countdown);
                    timerElement.textContent = "Expired";
                    resendButton.disabled = false;
                }
            }, 1000);
        }

        function updateTimer() {
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            timerElement.textContent =
                String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0");
        }

        verifyButton.addEventListener("click", async function () {
            const otp = getOTP();

            if (!resetEmail) {
                showMessage("No reset email found. Please start over.", "error");
                return;
            }

            if (otp.length !== 6) {
                showMessage("Please enter the complete 6-digit OTP.", "error");
                return;
            }

            if (timeLeft <= 0) {
                showMessage("This OTP has expired. Request a new one.", "error");
                return;
            }

            verifyButton.disabled = true;
            verifyButton.textContent = "Verifying...";
            message.className = "message";

            try {
                const response = await fetch(`${API_BASE}/api/forgot-password/verify-otp`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    credentials: "include",
                    body: JSON.stringify({ email: resetEmail, otp: otp })
                });

                const data = await response.json().catch(() => ({}));

                if (!response.ok) {
                    throw new Error(data.message || "Invalid or expired OTP.");
                }

                if (data.reset_token) {
                    sessionStorage.setItem("resetToken", data.reset_token);
                }
                sessionStorage.setItem("resetEmail", resetEmail);
                clearInterval(countdown);
                showMessage(data.message || "OTP verified successfully.", "success");
                verifyButton.textContent = "OTP Verified";

                setTimeout(() => {
                    window.location.replace("../shared/set-password.html");
                }, 700);

            } catch (error) {
                console.error("OTP verification error:", error);
                showMessage(error.message || "Unable to verify OTP.", "error");
                verifyButton.disabled = false;
                verifyButton.textContent = "Verify OTP";
            }
        });

        resendButton.addEventListener("click", async function () {
            if (!resetEmail) return;

            resendButton.disabled = true;
            resendButton.textContent = "Sending...";

            try {
                const response = await fetch(`${API_BASE}/api/forgot-password/resend-otp`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    credentials: "include",
                    body: JSON.stringify({ email: resetEmail })
                });

                const data = await response.json().catch(() => ({}));

                if (!response.ok) {
                    throw new Error(data.message || "Unable to resend OTP.");
                }

                sessionStorage.removeItem("resetOtp");
                sessionStorage.removeItem("otpVerified");

                otpInputs.forEach(input => input.value = "");
                otpInputs[0].focus();
                startTimer();

                showMessage(data.message || "A new OTP has been sent.", "success");

            } catch (error) {
                console.error("Resend OTP error:", error);
                showMessage(error.message || "Unable to resend OTP.", "error");
                resendButton.disabled = false;
            }

            resendButton.textContent = "Resend OTP";
        });

        if (resetEmail) {
            startTimer();
            otpInputs[0].focus();
        }
    