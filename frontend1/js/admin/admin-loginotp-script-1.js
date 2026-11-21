
"use strict";

(function () {

    const API_URL = window.FITNESS_API_BASE || "";

    const otpForm = document.getElementById("otpForm");
    const otpInput = document.getElementById("otp");
    const verifyBtn = document.getElementById("verifyBtn");
    const verifyText = document.getElementById("verifyText");
    const verifySpinner = document.getElementById("verifySpinner");

    const resendBtn = document.getElementById("resendBtn");
    const resendMessage = document.getElementById("resendMessage");

    const message = document.getElementById("message");
    const emailDisplay = document.getElementById("emailDisplay");

    const adminEmail = (
        sessionStorage.getItem("adminLoginEmail") || ""
    ).trim().toLowerCase();

    let resendCooldown = null;
    let resendSeconds = 60;

    function showMessage(text, type) {
        message.textContent = text;
        message.className = "message " + (type || "");
    }

    function clearMessage() {
        message.textContent = "";
        message.className = "message";
    }

    function maskEmail(email) {
        const parts = email.split("@");

        if (parts.length !== 2) {
            return email;
        }

        const name = parts[0];
        const domain = parts[1];

        if (name.length <= 2) {
            return name.charAt(0) + "***@" + domain;
        }

        return (
            name.charAt(0) +
            "***" +
            name.charAt(name.length - 1) +
            "@" +
            domain
        );
    }

    function startResendCooldown(seconds) {
        clearInterval(resendCooldown);

        resendSeconds = seconds;
        resendBtn.disabled = true;

        resendBtn.textContent =
            "Resend OTP (" + resendSeconds + "s)";

        resendCooldown = setInterval(function () {

            resendSeconds--;

            if (resendSeconds <= 0) {
                clearInterval(resendCooldown);
                resendCooldown = null;
                resendBtn.disabled = false;
                resendBtn.textContent = "Resend OTP";
                return;
            }

            resendBtn.textContent =
                "Resend OTP (" + resendSeconds + "s)";

        }, 1000);
    }

    if (!adminEmail) {
        showMessage(
            "Administrator email information is missing. Please log in again.",
            "error"
        );

        verifyBtn.disabled = true;
        resendBtn.disabled = true;

        return;
    }

    emailDisplay.textContent =
        "Code sent to " + maskEmail(adminEmail);

    otpInput.addEventListener("input", function () {
        otpInput.value = otpInput.value
            .replace(/\D/g, "")
            .slice(0, 6);
    });

    otpForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        clearMessage();

        const otp = otpInput.value.trim();

        if (!/^\d{6}$/.test(otp)) {
            showMessage(
                "Please enter the complete 6-digit OTP.",
                "error"
            );
            otpInput.focus();
            return;
        }

        verifyBtn.disabled = true;
        verifyText.textContent = "Verifying...";
        verifySpinner.hidden = false;

        try {

            const response = await fetch(
                API_URL + "/api/admin-login/verify-otp",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    credentials: "include",
                    body: JSON.stringify({
                        email: adminEmail,
                        otp: otp
                    })
                }
            );

            const data = await response.json().catch(function () {
                return {};
            });

            if (!response.ok || !data.success) {
                throw new Error(
                    data.message ||
                    "Invalid or expired OTP."
                );
            }

            showMessage(
                "OTP verified successfully. Opening Admin Dashboard...",
                "success"
            );

            sessionStorage.removeItem("adminLoginEmail");

            clearInterval(resendCooldown);

            setTimeout(function () {
                window.location.replace("admin-dashboard.html");
            }, 700);

        } catch (error) {

            showMessage(
                error.message ||
                "Unable to verify OTP. Please try again.",
                "error"
            );

            otpInput.value = "";
            otpInput.focus();

            verifyBtn.disabled = false;
            verifyText.textContent = "Verify OTP";
            verifySpinner.hidden = true;
        }

    });

    resendBtn.addEventListener("click", async function () {

        clearMessage();
        resendMessage.textContent = "";

        resendBtn.disabled = true;
        resendMessage.textContent = "Sending new OTP...";

        try {

            const response = await fetch(
                API_URL + "/api/admin-login/resend-otp",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    credentials: "include",
                    body: JSON.stringify({
                        email: adminEmail
                    })
                }
            );

            const data = await response.json().catch(function () {
                return {};
            });

            if (!response.ok || !data.success) {
                throw new Error(
                    data.message ||
                    "Unable to resend OTP."
                );
            }

            resendMessage.textContent =
                "A new OTP has been sent.";

            otpInput.value = "";
            otpInput.focus();

            startResendCooldown(60);

        } catch (error) {

            resendMessage.textContent =
                error.message ||
                "Unable to resend OTP.";

            resendBtn.disabled = false;
            resendBtn.textContent = "Resend OTP";
        }

    });

    otpInput.focus();
    startResendCooldown(60);

})();
