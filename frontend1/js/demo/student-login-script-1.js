
  const t = document.getElementById("toggle");
  if (t) t.onclick = () => {
    const p = document.getElementById("password");
    p.type = p.type === "password" ? "text" : "password";
  };
  document.getElementById("loginForm").onsubmit = e => {
    e.preventDefault();
    // TODO: call your student login API here
  };
