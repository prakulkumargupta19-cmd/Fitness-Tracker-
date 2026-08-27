/* Shared, backend-only authentication flow for every role portal. */
(function () {
  "use strict";
  const role = location.pathname.includes("/admin/") ? "admin" : location.pathname.includes("/coach/") ? "coach" : "player";
  const prefix = role === "admin" ? "admin" : role === "coach" ? "coach" : "student";
  const page = location.pathname.split("/").pop();
  const loginPage = role === "admin" ? "admin-login.html" : role === "coach" ? "coach-login.html" : "student-login.html";
  const dashboardPage = role === "admin" ? "admin-dashboard.html" : role === "coach" ? "coach-dashboard.html" : "student-dashboard.html";
  const call = (path, body) => fetch(path, {method: "POST", headers: {"Content-Type":"application/json"}, credentials:"include", body: JSON.stringify(body)})
    .then(async r => ({ok:r.ok, data: await r.json().catch(() => ({message:"Unexpected server response."}))}));
  const field = (...ids) => ids.map(id => document.getElementById(id)).find(Boolean);
  const show = text => { const el = field("errorMessage", "message"); if (el) { el.textContent = text; el.style.display = "block"; el.classList.remove("hidden"); } else alert(text); };
  const emailInput = () => field("email", "studentEmail", "coachEmail", "adminEmail") || document.querySelector('input[type="email"]');
  const otp = () => [...document.querySelectorAll(".otp-input")].map(el => el.value).join("") || (field("otp") || {}).value || "";
  const redirect = target => { location.href = target; };
  const storedEmail = () => sessionStorage.getItem("authEmail") || sessionStorage.getItem("resetEmail") || sessionStorage.getItem("studentSignupEmail") || sessionStorage.getItem("coachSignupEmail") || sessionStorage.getItem("adminSignupEmail");

  function setPending(mode, email) { sessionStorage.setItem("authMode", mode); sessionStorage.setItem("authEmail", email); }
  function displayPendingEmail() {
    const email = storedEmail();
    if (!email) return;
    // Each existing OTP design uses one of these IDs.  Always render the
    // current flow's exact email; never rely on the template's placeholder.
    ["userEmail", "emailDisplay", "verificationEmail", "emailAddress"].forEach(id => {
      const element = document.getElementById(id);
      if (element) element.textContent = email;
    });
  }
  function verifyTarget() { return page.includes("signup") ? `${prefix}-signup-verify.html` : "verify.html"; }
  function protectDashboard() {
    fetch("/api/session", {credentials:"include"}).then(r => r.ok ? r.json() : null).then(data => {
      if (!data || !data.authenticated || data.user.role !== role) redirect(loginPage);
      else window.__USER = data.user;
    }).catch(() => redirect(loginPage));
  }
  if (page.includes("dashboard")) { protectDashboard(); return; }
  displayPendingEmail();

  document.addEventListener("submit", async event => {
    const form = event.target;
    if (!form.matches("form")) return;
    event.preventDefault(); event.stopImmediatePropagation();
    const email = (emailInput()?.value || "").trim().toLowerCase();
    if (page.includes("login")) {
      const password = (field("password") || {}).value || "";
      if (!email || !password) return show("Please enter your email and password.");
      const result = await call("/api/login", {email, password});
      if (!result.ok || !result.data.success) return show(result.data.message || "Invalid email or password.");
      setPending("login", email); redirect("verify.html"); return;
    }
    if (page.includes("signup") && !page.includes("verify")) {
      const name = (field("fullName", "name") || {}).value || "";
      const password = (field("password", "studentPassword", "coachPassword") || {}).value || "";
      const confirm = (field("confirmPassword") || {}).value || "";
      if (password !== confirm) return show("Passwords do not match.");
      const result = await call("/api/register", {name, email, password, confirm_password: confirm, role: role === "player" ? "student" : role});
      if (!result.ok || !result.data.success) return show(result.data.message || "Unable to create account.");
      setPending("signup", email); redirect(verifyTarget()); return;
    }
    if (page.includes("forgot")) {
      if (!email) return show("Please enter your email address.");
      const result = await call("/api/forgot-password", {email});
      if (!result.ok || !result.data.success) return show(result.data.message || "Unable to send a verification code.");
      setPending("reset", email); redirect("verify.html"); return;
    }
    if (page.includes("reset-password")) {
      const password = (field("newPassword", "password") || {}).value || "";
      const confirm = (field("confirmPassword") || {}).value || "";
      const result = await call("/api/reset-password", {email: storedEmail(), new_password: password, confirm_password: confirm});
      if (!result.ok || !result.data.success) return show(result.data.message || "Unable to reset password.");
      sessionStorage.clear(); show("Password reset successfully. Redirecting to login…"); setTimeout(() => redirect(loginPage), 900);
    }
  }, true);

  document.addEventListener("click", async event => {
    const target = event.target.closest("button"); if (!target) return;
    const isVerify = /verify/i.test(target.id || target.textContent);
    const isResend = /resend/i.test(target.id || target.textContent);
    if (!isVerify && !isResend) return;
    event.preventDefault(); event.stopImmediatePropagation();
    const email = storedEmail(); const mode = page.includes("signup") ? "signup" : sessionStorage.getItem("authMode");
    if (!email) return show("Your verification session has expired. Please start again.");
    if (isResend) {
      const endpoint = mode === "signup" ? "/api/account-verification/send" : mode === "login" ? "/api/admin-login/resend-otp" : "/api/forgot-password/resend-otp";
      const result = await call(endpoint, {email}); return show(result.data.message || "Unable to resend OTP.");
    }
    const code = otp(); if (!/^\d{6}$/.test(code)) return show("Please enter a valid 6-digit OTP.");
    const endpoint = mode === "signup" ? "/api/account-verification/verify" : mode === "login" ? "/api/login/verify-otp" : "/api/forgot-password/verify-otp";
    const result = await call(endpoint, {email, otp: code});
    if (!result.ok || !result.data.success) return show(result.data.message || "Incorrect OTP. Please try again.");
    if (mode === "reset") return redirect("reset-password.html");
    sessionStorage.removeItem("authMode"); sessionStorage.removeItem("authEmail");
    const actualRole = result.data.user && result.data.user.role;
    redirect(actualRole === "admin" ? "../admin/admin-dashboard.html" : actualRole === "coach" ? "../coach/coach-dashboard.html" : "../student/student-dashboard.html");
  }, true);
})();
