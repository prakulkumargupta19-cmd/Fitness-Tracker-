
        (function () {
            "use strict";

            const API_BASE = window.FITNESS_API_BASE || window.APP_CONFIG?.API_BASE || "";
            const otpForm = document.getElementById("otpForm");
            const otpInputs = Array.from(document.querySelectorAll(".otp-input"));
            const verifyButton = document.getElementById("verifyButton");
            const resendButton = document.getElementById("resendButton");
            const message = document.getElementById("message");
            const emailDisplay = document.getElementById("emailDisplay");
            const roleDescription = document.getElementById("roleDescription");
            const backLink = document.getElementById("backLink");
            let resendInterval;
            let resendSeconds = 60;
            let pendingRole = null;
            let pendingEmail = null;

            const roleDetails = {
                student: { label: "student", login: "../student/student-login.html", dashboard: "../student/student-dashboard.html" },
                coach: { label: "coach", login: "../coach/coach-login.html", dashboard: "../coach/coach-dashboard.html" },
                admin: { label: "administrator", login: "../admin/admin-login.html", dashboard: "../admin/admin-dashboard.html" }
            };

            function showMessage(text, type) {
                message.textContent = text;
                message.className = "message" + (type ? " " + type : "");
            }

            function setOtpEnabled(enabled) {
                otpInputs.forEach(function (input) { input.disabled = !enabled; });
                verifyButton.disabled = !enabled;
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
                    resendButton.textContent = "Resend OTP (" + resendSeconds + "s)";
                }, 1000);
            }

            async function readJson(response) {
                return response.json().catch(function () { return {}; });
            }

            otpInputs.forEach(function (input, index) {
                input.addEventListener("input", function () {
                    input.value = input.value.replace(/\D/g, "").slice(-1);
                    if (input.value && otpInputs[index + 1]) otpInputs[index + 1].focus();
                });
                input.addEventListener("keydown", function (event) {
                    if (event.key === "Backspace" && !input.value && otpInputs[index - 1]) otpInputs[index - 1].focus();
                    if (event.key === "ArrowLeft" && otpInputs[index - 1]) otpInputs[index - 1].focus();
                    if (event.key === "ArrowRight" && otpInputs[index + 1]) otpInputs[index + 1].focus();
                });
                input.addEventListener("paste", function (event) {
                    event.preventDefault();
                    const digits = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
                    digits.split("").forEach(function (digit, digitIndex) { otpInputs[digitIndex].value = digit; });
                    if (digits) otpInputs[Math.min(digits.length - 1, 5)].focus();
                });
            });

            otpForm.addEventListener("submit", async function (event) {
                event.preventDefault();
                const otp = otpInputs.map(function (input) { return input.value; }).join("");
                if (!/^\d{6}$/.test(otp)) {
                    showMessage("Enter the complete 6-digit verification code.", "error");
                    const emptyInput = otpInputs.find(function (input) { return !input.value; });
                    if (emptyInput) emptyInput.focus();
                    return;
                }

                verifyButton.disabled = true;
                verifyButton.textContent = "Verifying...";
                try {
                    const response = await fetch(API_BASE + "/api/login/verify-otp", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        credentials: "include",
                        body: JSON.stringify({ email: pendingEmail, otp: otp })
                    });
                    const data = await readJson(response);
                    if (!response.ok || !data.success) throw new Error(data.message || "Invalid or expired OTP.");
                    const account = roleDetails[data.user && data.user.role];
                    if (!account) throw new Error("The verified account role could not be confirmed.");
                    clearInterval(resendInterval);
                    showMessage("Login verified. Opening your dashboard...", "success");
                    verifyButton.textContent = "Verified";
                    window.setTimeout(function () { window.location.replace(account.dashboard); }, 500);
                } catch (error) {
                    showMessage(error.message || "Unable to verify the code.", "error");
                    verifyButton.disabled = false;
                    verifyButton.textContent = "Verify OTP";
                }
            });

            resendButton.addEventListener("click", async function () {
                resendButton.disabled = true;
                resendButton.textContent = "Sending...";
                try {
                    const response = await fetch(API_BASE + "/api/login/resend-otp", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        credentials: "include",
                        body: JSON.stringify({ email: pendingEmail })
                    });
                    const data = await readJson(response);
                    if (!response.ok || !data.success) throw new Error(data.message || "Unable to resend the code.");
                    otpInputs.forEach(function (input) { input.value = ""; });
                    showMessage(data.message || "A new code has been sent.", "success");
                    startResendCooldown();
                } catch (error) {
                    showMessage(error.message || "Unable to resend the code.", "error");
                    resendButton.disabled = false;
                    resendButton.textContent = "Resend OTP";
                }
            });

            fetch(API_BASE + "/api/login/pending-otp", {
                method: "GET",
                credentials: "include",
                cache: "no-store"
            }).then(async function (response) {
                const data = await readJson(response);
                if (!response.ok || !data.success || !roleDetails[data.role]) {
                    throw new Error(data.message || "Start again from your login page.");
                }
                pendingRole = data.role;
                pendingEmail = data.email;
                roleDescription.textContent = "Enter the verification code sent for your " + roleDetails[pendingRole].label + " account.";
                emailDisplay.textContent = "Code sent to " + pendingEmail;
                backLink.href = roleDetails[pendingRole].login;
                setOtpEnabled(true);
                otpInputs[0].focus();
                startResendCooldown();
            }).catch(function (error) {
                emailDisplay.textContent = "No active login verification.";
                showMessage(error.message || "Start again from your login page.", "error");
                resendButton.disabled = true;
                setOtpEnabled(false);
            });
        }());
    