(function () {
  "use strict";
  // Admin identities live in a separate table; the current chat store only
  // supports student and coach user IDs.
  if (window.location.pathname.toLowerCase().includes("/admin/")) return;
  const root = document.createElement("section");
  root.className = "dashboard-chat";
  root.id = "dashboardChat";
  root.setAttribute("aria-hidden", "true");
  root.innerHTML = `<aside class="dashboard-chat-sidebar"><div class="dashboard-chat-top"><div class="dashboard-chat-topline"><span>Chats</span><button class="dashboard-chat-close" type="button" aria-label="Close chat">×</button></div><input class="dashboard-chat-search" type="search" placeholder="Search people..." aria-label="Search people"></div><div class="dashboard-chat-contacts"><div class="dashboard-chat-empty">Search for a person to start chatting.</div></div></aside><div class="dashboard-chat-main"><div class="dashboard-chat-heading">Select a person to chat</div><div class="dashboard-chat-messages"><div class="dashboard-chat-empty">Your conversations will appear here.</div></div><form class="dashboard-chat-compose"><input maxlength="2000" placeholder="Type a message..." aria-label="Message" disabled><button type="submit" disabled>Send</button></form></div>`;
  const launcher = document.createElement("button");
  launcher.type = "button";
  launcher.className = "dashboard-chat-launcher";
  launcher.innerHTML = '<i class="bi bi-chat-dots-fill" aria-hidden="true"></i>Chat';
  launcher.setAttribute("aria-controls", "dashboardChat");
  document.body.append(launcher, root);

  const contactsEl = root.querySelector(".dashboard-chat-contacts");
  const messagesEl = root.querySelector(".dashboard-chat-messages");
  const heading = root.querySelector(".dashboard-chat-heading");
  const search = root.querySelector(".dashboard-chat-search");
  const form = root.querySelector(".dashboard-chat-compose");
  const input = form.querySelector("input");
  const send = form.querySelector("button");
  let selected = null;
  let debounce;

  async function api(path, options) {
    const method = options?.method || "GET";
    const headers = { "Content-Type": "application/json" };
    if (method !== "GET") {
      const tokenResponse = await fetch(`${window.FITNESS_API_BASE || ""}/api/csrf-token`, { credentials: "include" });
      const tokenData = await tokenResponse.json().catch(() => ({}));
      if (tokenData.csrf_token) headers["X-CSRFToken"] = tokenData.csrf_token;
    }
    try {
      const response = await fetch(`${window.FITNESS_API_BASE || window.APP_CONFIG?.API_BASE || ""}${path}`, {
        method, credentials: "include", headers,
        ...(options?.body ? { body: JSON.stringify(options.body) } : {})
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok || result.success === false) throw new Error(result.message || "Unable to load chat.");
      return result.data || [];
    } catch (error) {
      throw error;
    }
  }
  function showError(container, message) {
    container.innerHTML = "";
    const error = document.createElement("div"); error.className = "dashboard-chat-error"; error.textContent = message; container.append(error);
  }
  function makeContact(user) {
    const button = document.createElement("button"); button.type = "button";
    button.className = `dashboard-chat-contact${selected?.id === user.id ? " active" : ""}`;
    const avatar = document.createElement("span"); avatar.className = "dashboard-chat-avatar"; avatar.textContent = (user.full_name || "?").trim().charAt(0).toUpperCase();
    const detail = document.createElement("span"); detail.className = "dashboard-chat-contact-name"; detail.textContent = user.full_name || "Account";
    const role = document.createElement("span"); role.className = "dashboard-chat-contact-role"; role.textContent = user.role || "member"; detail.append(role); button.append(avatar, detail);
    button.addEventListener("click", () => openConversation(user)); return button;
  }
  async function loadContacts(query = "") {
    try {
      const data = await api(`/api/chat/contacts?q=${encodeURIComponent(query)}`);
      contactsEl.replaceChildren();
      if (!data.length) { contactsEl.innerHTML = '<div class="dashboard-chat-empty">No people found.</div>'; return; }
      data.forEach(user => contactsEl.append(makeContact(user)));
    } catch (error) { showError(contactsEl, error.message); }
  }
  async function openConversation(user) {
    selected = user; heading.textContent = user.full_name; input.disabled = send.disabled = false;
    contactsEl.querySelectorAll(".dashboard-chat-contact").forEach(item => item.classList.remove("active"));
    const active = [...contactsEl.querySelectorAll(".dashboard-chat-contact")].find(item => item.querySelector(".dashboard-chat-contact-name")?.childNodes[0]?.textContent === user.full_name);
    active?.classList.add("active"); messagesEl.innerHTML = '<div class="dashboard-chat-empty">Loading conversation...</div>';
    try {
      const data = await api(`/api/chat/messages?with_user_id=${encodeURIComponent(user.id)}`);
      messagesEl.replaceChildren();
      if (!data.length) messagesEl.innerHTML = '<div class="dashboard-chat-empty">Say hello to start the conversation.</div>';
      data.forEach(message => {
        const ownId = window.__USER?.id ?? window.APP_CONFIG?.CURRENT_USER_ID;
        const bubble = document.createElement("div"); bubble.className = `dashboard-chat-bubble${String(message.sender_user_id) === String(ownId) ? " mine" : ""}`;
        bubble.textContent = message.message;
        const time = document.createElement("span"); time.className = "dashboard-chat-time"; time.textContent = message.created_at ? new Date(message.created_at).toLocaleString() : ""; bubble.append(time); messagesEl.append(bubble);
      });
      messagesEl.scrollTop = messagesEl.scrollHeight;
    } catch (error) { showError(messagesEl, error.message); }
  }
  launcher.addEventListener("click", () => {
    const isOpen = root.classList.toggle("is-open"); root.setAttribute("aria-hidden", String(!isOpen));
    if (isOpen) { search.focus(); loadContacts(search.value.trim()); }
  });
  root.querySelector(".dashboard-chat-close").addEventListener("click", () => { root.classList.remove("is-open"); root.setAttribute("aria-hidden", "true"); });
  search.addEventListener("input", () => { clearTimeout(debounce); debounce = setTimeout(() => loadContacts(search.value.trim()), 180); });
  form.addEventListener("submit", async event => {
    event.preventDefault(); const text = input.value.trim(); if (!text || !selected) return;
    send.disabled = true;
    try { await api("/api/chat/messages", { method: "POST", body: { receiver_user_id: selected.id, message: text } }); input.value = ""; await openConversation(selected); }
    catch (error) { showError(messagesEl, error.message); }
    finally { send.disabled = false; }
  });
}());
