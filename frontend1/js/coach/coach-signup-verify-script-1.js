
        const API_BASE = window.FITNESS_API_BASE || "";

        const otpInputs = document.querySelectorAll(".otp-input");
        const verifyButton = document.getElementById("verifyButton");
        const resendButton = document.getElementById("resendButton");
        const message = document.getElementById("message");
        const timerElement = document.getElementById("timer");
        const userEmailElement = document.getElementById("userEmail");

        const coachEmail = sessionStorage.getItem("authEmail");

        if (!coachEmail) {
            showMessage("Your signup session has expired. Please create your account again.", "error");
            verifyButton.disabled = true;
            resendButton.disabled = true;
        } else {
            userEmailElement.textContent = maskEmail(coachEmail);
        }

        function maskEmail(email) {
            const parts = email.split("@");
            if (parts.length !== 2) return email;
            const username = parts[0];
            const domain = parts[1];
            if (username.length <= 2) {
                return "*".repeat(username.length) + "@" + domain;
            }
            return username.charAt(0) + "*".repeat(username.length - 2) + username.charAt(username.length - 1) + "@" + domain;
        }

        otpInputs.forEach((input, index) => {
            input.addEventListener("input", function() {
                this.value = this.value.replace(/\D/g, "").slice(0, 1);
                if (this.value && index < otpInputs.length - 1) {
                    otpInputs[index + 1].focus();
                }
            });

            input.addEventListener("keydown", function(event) {
                if (event.key === "Backspace" && !this.value && index > 0) {
                    otpInputs[index - 1].focus();
                }
            });

            input.addEventListener("paste", function(event) {
                event.preventDefault();
                const pastedData = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
                pastedData.split("").forEach((digit, i) => {
                    if (otpInputs[i]) {
                        otpInputs[i].value = digit;
                    }
                });
                if (pastedData.length === 6) {
                    otpInputs[5].focus();
                }
            });
        });

        function getOTP() {
            let otp = "";
            otpInputs.forEach(input => {
                otp += input.value;
            });
            return otp;
        }

        function clearOTP() {
            otpInputs.forEach(input => {
                input.value = "";
            });
            otpInputs[0].focus();
        }

        function showMessage(text, type) {
            message.textContent = text;
            message.className = "message " + type;
        }

        verifyButton.addEventListener("click", async function() {
            const otp = getOTP();

            if (otp.length !== 6) {
                showMessage("Please enter the complete 6-digit OTP.", "error");
                return;
            }

            if (!coachEmail) {
                showMessage("Signup session expired. Please create your account again.", "error");
                return;
            }

            verifyButton.disabled = true;
            verifyButton.textContent = "Verifying...";

            try {
                const response = await fetch(`${API_BASE}/api/account-verification/verify`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    credentials: "include",
                    body: JSON.stringify({ email: coachEmail, otp: otp })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.message || data.error || "Invalid or expired OTP.");
                }

                showMessage(data.message || "Email verified. Your application is waiting for admin approval.", "success");

                sessionStorage.removeItem("authEmail");
                sessionStorage.removeItem("authMode");

                setTimeout(function() {
                    window.location.href = "coach-waiting.html";
                }, 1200);

            } catch (error) {
                console.error("OTP verification error:", error);
                showMessage(error.message || "Unable to verify OTP. Please try again.", "error");
                verifyButton.disabled = false;
                verifyButton.textContent = "Verify OTP";
            }
        });

        let timeLeft = 120;
        let countdown;

        function startCountdown() {
            clearInterval(countdown);
            countdown = setInterval(function() {
                const minutes = Math.floor(timeLeft / 60);
                const seconds = timeLeft % 60;

                timerElement.textContent = String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0");

                if (timeLeft <= 0) {
                    clearInterval(countdown);
                    timerElement.textContent = "Expired";
                    resendButton.disabled = false;
                    return;
                }
                timeLeft--;
            }, 1000);
        }

        startCountdown();

        resendButton.addEventListener("click", async function() {
            if (!coachEmail) {
                showMessage("Signup session expired. Please create your account again.", "error");
                return;
            }

            resendButton.disabled = true;
            resendButton.textContent = "Sending...";

            try {
                const response = await fetch(`${API_BASE}/api/account-verification/send`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    credentials: "include",
                    body: JSON.stringify({ email: coachEmail })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.message || data.error || "Unable to resend OTP.");
                }

                timeLeft = 120;
                timerElement.textContent = "02:00";
                clearOTP();
                startCountdown();

                showMessage(data.message || "A new OTP has been sent to your email.", "success");
                resendButton.textContent = "Resend OTP";
                resendButton.disabled = true;

            } catch (error) {
                console.error("Resend OTP error:", error);
                showMessage(error.message || "Unable to resend OTP. Please try again.", "error");
                resendButton.disabled = false;
                resendButton.textContent = "Resend OTP";
            }
        });
    