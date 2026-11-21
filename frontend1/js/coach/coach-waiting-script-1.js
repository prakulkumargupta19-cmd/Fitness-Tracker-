
        "use strict";

        const coachEmail = sessionStorage.getItem("authEmail") || sessionStorage.getItem("coach_email");
        const statusElement = document.getElementById("approvalStatus");
        const infoElement = document.getElementById("approvalInfo");

        async function checkApprovalStatus() {
            if (!coachEmail) return;

            try {
                const apiBase = window.FITNESS_API_BASE || window.APP_CONFIG?.API_BASE || "";
                const response = await fetch(
                    `${apiBase}/api/coach/status?email=${encodeURIComponent(coachEmail)}`
                );

                const data = await response.json().catch(() => ({}));

                if (!response.ok || !data.success) return;

                if (data.coach_status === "approved") {
                    statusElement.textContent = "Account Approved";
                    statusElement.className = "status approved";
                    window.location.href = "coach-login.html";
                } else if (data.coach_status === "rejected") {
                    statusElement.textContent = "Application Not Approved";
                    statusElement.className = "status rejected";
                    infoElement.textContent =
                        "Your registration was not approved. Please contact the administrator for more information.";
                }
            } catch (error) {
                console.error("Unable to check coach approval status:", error);
            }
        }

        checkApprovalStatus();
        setInterval(checkApprovalStatus, 5000);
    