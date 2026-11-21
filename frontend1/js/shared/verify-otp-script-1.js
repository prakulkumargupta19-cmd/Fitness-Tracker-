
        "use strict";

        const API_URL = window.FITNESS_API_BASE || "";
        const otpForm = document.getElementById("otpForm");
        const otpInputs = Array.from(document.querySelectorAll(".otp-digit"));
        const verifyButton = document.getElementById("verifyButton");
        const resendButton = document.getElementById("resendButton");
        const message = document.getElementById("message");
        const timerDisplay = document.getElementById("timer");
        const userEmail = document.getElementById("userEmail");

        const email = sessionStorage.getItem("resetEmail");
        let timeLeft = 3 * 60;
        let timerInterval;
        let resendInterval;
        let resendSeconds = 60;

        userEmail.textContent = email || "Email not found";

        function showMessage(text, type) {
            message.textContent = text;
            message.className = "message " + type;
        }

        function getOTP() {
            return otpInputs.map(function (input) {
                return input.value;
            }).join("");
        }

        function startTimer() {
            clearInterval(timerInterval);
            timeLeft = 3 * 60;
            timerDisplay.textContent = "3:00";

            timerInterval = setInterval(function () {
                timeLeft--;

                const minutes = Math.floor(timeLeft / 60);
                const seconds = timeLeft % 60;

                timerDisplay.textContent =
                    minutes + ":" + seconds.toString().padStart(2, "0");

                if (timeLeft <= 0) {
                    clearInterval(timerInterval);
                    timerDisplay.textContent = "Expired";
                }
            }, 1000);
        }

        function startResendCooldown() {
            clearInterval(resendInterval);
            resendSeconds = 60;
            resendButton.disabled = true;
            resendButton.textContent = "Resend OTP (60s)";

            resendInterval = setInterval(function () {
                resendSeconds--;

                if (resendSeconds <= 0) {
                    clearInterval(resendInterval);
                    resendButton.disabled = false;
                    resendButton.textContent = "Resend OTP";
                    return;
                }

                resendButton.textContent =
                    "Resend OTP (" + resendSeconds + "s)";
            }, 1000);
        }

        otpInputs.forEach(function (input, index) {
            input.addEventListener("input", function () {
                input.value = input.value.replace(/\D/g, "").slice(-1);

                if (input.value && otpInputs[index + 1]) {
                    otpInputs[index + 1].focus();
                }
            });

            input.addEventListener("keydown", function (event) {
                if (
                    event.key === "Backspace" &&
                    !input.value &&
                    otpInputs[index - 1]
                ) {
                    otpInputs[index - 1].focus();
                }

                if (event.key === "ArrowLeft" && otpInputs[index - 1]) {
                    otpInputs[index - 1].focus();
                }

                if (event.key === "ArrowRight" && otpInputs[index + 1]) {
                    otpInputs[index + 1].focus();
                }
            });

            input.addEventListener("paste", function (event) {
                event.preventDefault();

                const digits = event.clipboardData
                    .getData("text")
                    .replace(/\D/g, "")
                    .slice(0, 6);

                digits.split("").forEach(function (digit, digitIndex) {
                    otpInputs[digitIndex].value = digit;
                });

                if (digits) {
                    otpInputs[Math.min(digits.length - 1, 5)].focus();
                }
            });
        });

        otpForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const otp = getOTP();

            if (!otp) {
                showMessage("Please enter the OTP.", "error");
                otpInputs[0].focus();
                return;
            }

            if (!/^\d{6}$/.test(otp)) {
                showMessage("Please enter the complete 6-digit OTP.", "error");

                const emptyInput = otpInputs.find(function (input) {
                    return !input.value;
                });
                if (emptyInput) {
                    emptyInput.focus();
                }

                return;
            }

            verifyButton.disabled = true;
            verifyButton.textContent = "Verifying...";

            try {
                const response = await fetch(
                    API_URL + "/api/forgot-password/verify-otp",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        credentials: "include",
                        body: JSON.stringify({
                            email: email,
                            otp: otp
                        })
                    }
                );

                const result = await response.json().catch(function () {
                    return {};
                });

                if (!response.ok || !result.success) {
                    throw new Error(result.message || "Invalid OTP.");
                }

                if (result.reset_token) {
                    sessionStorage.setItem("resetToken", result.reset_token);
                }

                showMessage("OTP verified. Redirecting...", "success");
                verifyButton.textContent = "Verified";

                setTimeout(function () {
                    window.location.href = "set-password.html";
                }, 700);
            } catch (error) {
                message.textContent = error.message || "Unable to verify OTP.";
                message.className = "message error";
                verifyButton.disabled = false;
                verifyButton.textContent = "Verify OTP";
            }
        });

        resendButton.addEventListener("click", async function () {
            resendButton.disabled = true;
            resendButton.textContent = "Sending...";

            try {
                const response = await fetch(
                    API_URL + "/api/forgot-password/resend-otp",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        credentials: "include",
                        body: JSON.stringify({
                            email: email
                        })
                    }
                );

                const result = await response.json().catch(function () {
                    return {};
                });

                if (!response.ok || !result.success) {
                    throw new Error(result.message || "Unable to resend OTP.");
                }

                otpInputs.forEach(function (input) {
                    input.value = "";
                });

                showMessage("OTP resent successfully.", "success");
                startTimer();
                startResendCooldown();
                otpInputs[0].focus();
            } catch (error) {
                message.textContent = error.message || "Unable to resend OTP.";
                message.className = "message error";
                resendButton.disabled = false;
                resendButton.textContent = "Resend OTP";
            }
        });

        startTimer();
        startResendCooldown();
    