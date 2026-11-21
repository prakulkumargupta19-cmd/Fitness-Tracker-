
        "use strict";

        const API_URL = window.FITNESS_API_BASE || "";
        const forgotPasswordForm = document.getElementById("forgotPasswordForm");
        const sendButton = document.getElementById("sendButton");
        const emailInput = document.getElementById("email");
        const message = document.getElementById("message");

        forgotPasswordForm.addEventListener("submit", async function (event) {
            event.preventDefault();
            const email = emailInput.value.trim().toLowerCase();

            message.textContent = "";
            message.className = "message";

            if (!email) {
                message.textContent = "Please enter your email.";
                message.className = "message error";
                emailInput.focus();
                return;
            }

            if (!emailInput.checkValidity()) {
                message.textContent = "Please enter a valid email address.";
                message.className = "message error";
                emailInput.focus();
                return;
            }

            sendButton.disabled = true;
            sendButton.textContent = "Sending...";

            try {
                const response = await fetch(API_URL + "/api/forgot-password", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    credentials: "include",
                    body: JSON.stringify({ email })
                });

                const result = await response.json().catch(function () {
                    return {};
                });

                if (!response.ok || !result.success) {
                    throw new Error(result.message || "Unable to send OTP.");
                }

                sessionStorage.setItem("resetEmail", email);

                message.textContent = "OTP sent. Redirecting...";
                message.className = "message success";

                setTimeout(function () {
                    window.location.href = "verify-otp.html";
                }, 700);
            } catch (error) {
                message.textContent = error.message || "Unable to send OTP.";
                message.className = "message error";

                sendButton.disabled = false;
                sendButton.textContent = "Continue";
            }
        });
    