
        (function () {
            const form = document.getElementById("signupForm");
            const button = document.getElementById("signupButton");
            const buttonText = document.getElementById("buttonText");
            const error = document.getElementById("errorMessage");

            function showError(text) { error.textContent = text; error.hidden = false; }
            function setupToggle(inputId, buttonId, iconId, label) {
                const input = document.getElementById(inputId);
                const toggle = document.getElementById(buttonId);
                const icon = document.getElementById(iconId);
                toggle.addEventListener("click", function () {
                    const visible = input.type === "password";
                    input.type = visible ? "text" : "password";
                    toggle.setAttribute("aria-label", (visible ? "Hide " : "Show ") + label);
                    toggle.setAttribute("aria-pressed", String(visible));
                    icon.innerHTML = visible ? '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>' : '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>';
                });
            }
            setupToggle("password", "togglePassword", "passwordEye", "password");
            setupToggle("confirmPassword", "toggleConfirmPassword", "confirmPasswordEye", "confirm password");

            form.addEventListener("submit", async function (event) {
                event.preventDefault();
                error.hidden = true;
                if (!form.reportValidity()) return;

                const contactNumber = document.getElementById("contactNumber").value.trim();
                const password = document.getElementById("password").value;
                const confirmPassword = document.getElementById("confirmPassword").value;
                if (!/^\d{10}$/.test(contactNumber)) { showError("Please enter a valid 10-digit contact number."); return; }
                if (password.length < 8) { showError("Password must contain at least 8 characters."); return; }
                if (password !== confirmPassword) { showError("Passwords do not match."); return; }

                button.disabled = true;
                buttonText.textContent = "Creating Account...";
                try {
                    const response = await fetch((window.FITNESS_API_BASE || "") + "/api/signup", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        credentials: "include",
                        body: JSON.stringify({
                            name: document.getElementById("fullName").value.trim(),
                            email: document.getElementById("coachEmail").value.trim().toLowerCase(),
                            contact_number: contactNumber,
                            password: password,
                            confirm_password: confirmPassword,
                            role: "coach",
                        })
                    });
                    const data = await response.json().catch(function () { return {}; });
                    if (!response.ok || !data.success) throw new Error(data.message || "Unable to create coach account.");
                    sessionStorage.setItem("authEmail", document.getElementById("coachEmail").value.trim().toLowerCase());
                    window.location.href = "coach-signup-verify.html";
                } catch (requestError) {
                    console.error("Coach signup error:", requestError);
                    showError(requestError.message || "Unable to create account. Please try again.");
                    button.disabled = false;
                    buttonText.textContent = "Create Account";
                }
            });
        }());
    