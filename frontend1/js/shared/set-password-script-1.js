

        /* =====================================================
           EXISTING BACKEND LOGIC
        ===================================================== */

        const API_URL = window.FITNESS_API_BASE || "";


        document
            .getElementById("resetButton")
            .addEventListener("click", async () => {

                const password =
                    document.getElementById("password").value;

                const confirmPassword =
                    document.getElementById("confirmPassword").value;

                const email =
                    sessionStorage.getItem("resetEmail");

                const resetToken =
                    sessionStorage.getItem("resetToken");

                const message =
                    document.getElementById("message");


                if (password !== confirmPassword) {

                    message.textContent =
                        "Passwords do not match.";

                    message.className =
                        "message error";

                    return;
                }


                try {

                    const response =
                        await fetch(
                            API_URL + "/api/reset-password",
                            {
                                method: "POST",

                                headers: {
                                    "Content-Type":
                                        "application/json"
                                },

                                credentials: "include",

                                body: JSON.stringify({
                                    email,
                                    password,
                                    reset_token: resetToken,
                                    stage: "reset"
                                })
                            }
                        );


                    const result =
                        await response.json();


                    if (
                        !response.ok ||
                        !result.success
                    ) {

                        throw new Error(
                            result.message ||
                            "Unable to reset password."
                        );

                    }


                    message.textContent =
                        result.role === "coach"
                            ? "Password reset successfully. Redirecting to Coach Login..."
                            : "Password reset successfully. Redirecting to Login...";

                    message.className =
                        "message success";

                    sessionStorage.removeItem("resetToken");
                    sessionStorage.removeItem("resetEmail");


                    setTimeout(() => {

                        const role =
                            result.role;

                        const redirectUrl =
                            role === "admin"
                                ? "../admin/admin-login.html"
                                : role === "coach"
                                    ? "../coach/coach-login.html?reset=success"
                                    : "../student/student-login.html";

                        window.location.href =
                            redirectUrl;

                    }, 1800);


                } catch (error) {

                    message.textContent =
                        error.message;

                    message.className =
                        "message error";

                }

            });


        /* =====================================================
           PASSWORD VISIBILITY
           UI ONLY — DOES NOT CHANGE BACKEND LOGIC
        ===================================================== */

        document
            .querySelectorAll(".toggle-password")
            .forEach(button => {

                button.addEventListener("click", () => {

                    const targetId =
                        button.dataset.target;

                    const input =
                        document.getElementById(targetId);

                    if (input.type === "password") {

                        input.type = "text";

                        button.setAttribute(
                            "aria-label",
                            "Hide password"
                        );

                    } else {

                        input.type = "password";

                        button.setAttribute(
                            "aria-label",
                            "Show password"
                        );

                    }

                });

            });

    