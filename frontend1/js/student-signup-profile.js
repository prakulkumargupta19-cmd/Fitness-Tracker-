(function () {
    "use strict";

    const basicStep = document.getElementById("basicInfoStep");
    const personalStep = document.getElementById("personalInfoStep");
    const basicForm = document.getElementById("basicInfoForm");
    const personalForm = document.getElementById("personalInfoForm");
    const basicMessage = document.getElementById("basicProfileMessage");
    const profileMessage = document.getElementById("profileMessage");
    const apiBase = window.FITNESS_API_BASE || "";

    if (!basicStep || !personalStep || !basicForm || !personalForm) return;

    function savedBasicInfo() {
        return JSON.parse(sessionStorage.getItem("studentProfileBasic") || "null");
    }

    function showStep(step) {
        const selectedStep = ["basic", "personal"].includes(step) ? step : "account";
        const accountStep = document.getElementById("accountSignupStep");
        accountStep.hidden = selectedStep !== "account";
        basicStep.hidden = selectedStep !== "basic";
        personalStep.hidden = selectedStep !== "personal";

        const url = new URL(window.location.href);
        if (selectedStep === "account") url.searchParams.delete("step");
        else url.searchParams.set("step", selectedStep);
        window.history.replaceState(null, "", url);
    }

    const previousInfo = savedBasicInfo();
    if (previousInfo) {
        ["gender", "semester", "department", "blood_group", "medical_history", "address",
            "parent_name", "parent_phone", "parent_address"].forEach(function (field) {
            const input = document.getElementById(field);
            if (input && previousInfo[field] !== undefined) input.value = previousInfo[field];
        });
        document.getElementById("dob").value = previousInfo.date_of_birth || "";
    }

    const dob = document.getElementById("dob");
    const today = new Date();
    dob.max = today.getFullYear() + "-" + String(today.getMonth() + 1).padStart(2, "0") + "-" +
        String(today.getDate()).padStart(2, "0");

    basicForm.addEventListener("submit", function (event) {
        event.preventDefault();
        basicMessage.hidden = true;
        if (!basicForm.reportValidity()) return;

        sessionStorage.setItem("studentProfileBasic", JSON.stringify({
            gender: document.getElementById("gender").value,
            semester: document.getElementById("semester").value,
            department: document.getElementById("department").value.trim(),
            date_of_birth: dob.value,
            blood_group: document.getElementById("blood_group").value,
            medical_history: document.getElementById("medical_history").value.trim(),
            address: document.getElementById("address").value.trim(),
            parent_name: document.getElementById("parent_name").value.trim(),
            parent_phone: document.getElementById("parent_phone").value.trim(),
            parent_address: document.getElementById("parent_address").value.trim(),
        }));
        showStep("personal");
    });

    document.getElementById("personalBack").addEventListener("click", function () {
        showStep("basic");
    });

    personalForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        profileMessage.hidden = true;
        if (!personalForm.reportValidity()) return;

        const basic = savedBasicInfo();
        if (!basic || !basic.date_of_birth) {
            basicMessage.textContent = "Complete Basic Information before continuing.";
            basicMessage.hidden = false;
            showStep("basic");
            return;
        }

        const selectedSports = Array.from(
            document.querySelectorAll('input[name="sports"]:checked')
        ).map(function (input) {
            return input.value;
        });
        if (!selectedSports.length) {
            profileMessage.textContent = "Please select at least one sport.";
            profileMessage.hidden = false;
            return;
        }

        const height = Number(document.getElementById("height").value);
        const weight = Number(document.getElementById("weight").value);
        const heightCm = document.getElementById("height-unit").value === "ft"
            ? height * 30.48
            : height;
        const weightKg = document.getElementById("weight-unit").value === "lbs"
            ? weight * 0.453592
            : weight;
        const submitButton = personalForm.querySelector("button[type=submit]");
        submitButton.disabled = true;
        submitButton.textContent = "Saving...";

        try {
            const response = await fetch(apiBase + "/api/profile/setup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({
                    ...basic,
                    emergency_contact: sessionStorage.getItem("signupEmergencyContact") || "",
                    height_cm: heightCm.toFixed(2),
                    weight_kg: weightKg.toFixed(2),
                    sports: selectedSports,
                    sport_activity: selectedSports.join(", "),
                    goal: document.getElementById("goal").value.trim(),
                }),
            });
            const data = await response.json().catch(function () {
                return {};
            });
            if (!response.ok || !data.success) {
                throw new Error(data.message || "Unable to save your profile.");
            }

            sessionStorage.setItem("student_login_email", sessionStorage.getItem("studentEmail") || "");
            ["studentProfileBasic", "signupName", "signupMobileNumber", "signupEmergencyContact"]
                .forEach(function (key) {
                    sessionStorage.removeItem(key);
                });
            window.location.href = "student-login.html";
        } catch (error) {
            console.error("Profile setup error:", error);
            profileMessage.textContent = error.message || "Unable to connect to the server. Please try again.";
            profileMessage.hidden = false;
            submitButton.disabled = false;
            submitButton.textContent = "Complete Profile →";
        }
    });

    const requestedStep = new URLSearchParams(window.location.search).get("step");
    if (requestedStep === "personal" && !previousInfo) {
        basicMessage.textContent = "Complete Basic Information before continuing.";
        basicMessage.hidden = false;
        showStep("basic");
    } else {
        showStep(requestedStep);
    }
}());
