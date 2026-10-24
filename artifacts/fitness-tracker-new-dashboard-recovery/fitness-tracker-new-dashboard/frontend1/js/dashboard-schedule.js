(function (global) {
  "use strict";
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const api = async (path, method = "GET", body) => {
    const base = (global.FITNESS_API_BASE || global.APP_CONFIG?.API_BASE || "").replace(/\/$/, "");
    const headers = body ? { "Content-Type": "application/json" } : {};
    if (method !== "GET") {
      const tokenResponse = await fetch(`${base}/api/csrf-token`, { credentials: "include" });
      const tokenData = await tokenResponse.json().catch(() => ({}));
      if (!tokenResponse.ok || !tokenData.csrf_token) throw Error("Unable to start a secure schedule request. Please refresh and try again.");
      headers["X-CSRFToken"] = tokenData.csrf_token;
    }
    const response = await fetch(base + path, { method, credentials: "include", headers, body: body ? JSON.stringify(body) : undefined });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || result.success === false) throw Error(result.message || "Schedule request failed.");
    return result.data ?? result;
  };
  const dateKey = (d) => String(d || "").slice(0, 10);
  function mount({ root, role }) {
    root = typeof root === "string" ? document.querySelector(root) : root;
    if (!root || root.dataset.scheduleMounted) return;
    root.dataset.scheduleMounted = "true";
    let cursor = new Date(); cursor.setDate(1);
    const panel = document.createElement("section"); panel.className = "dashboard-schedule";
    panel.innerHTML = `<div class="schedule-heading"><div><span class="schedule-kicker">SHARED SCHEDULE</span><h2>Calendar & upcoming sessions</h2></div>${role === "admin" ? '<button type="button" class="schedule-add-toggle">Add session</button>' : ""}</div><div class="schedule-layout"><div class="schedule-calendar"><div class="schedule-calendar-head"><button type="button" data-month="-1" aria-label="Previous month">‹</button><strong data-month-label></strong><button type="button" data-month="1" aria-label="Next month">›</button></div><div class="schedule-week">${["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map(x=>`<span>${x}</span>`).join("")}</div><div class="schedule-days"></div><div class="schedule-legend"><span class="practice">Practice</span><span class="assessment">Assessment</span><span class="event">Event</span></div></div><div class="schedule-upcoming"><h3>Upcoming</h3><div class="schedule-items">Loading…</div></div></div>${role !== "student" ? `<form class="schedule-form" hidden><h3>${role === "coach" ? "Request a session" : "Publish a session"}</h3><div class="schedule-form-grid"><label>Programme<select name="programme_id" required><option value="">Choose programme</option></select></label><label>Session name<input name="title" required maxlength="180" placeholder="e.g. Strength assessment"></label><label>Type<select name="session_type"><option value="practice">Practice</option><option value="assessment">Assessment</option></select></label><label>Date<input name="session_date" type="date" required></label><label>Start<input name="start_time" type="time" required></label><label>End<input name="end_time" type="time" required></label><label>Venue<input name="venue" maxlength="255"></label><label class="wide">Notes<input name="notes"></label></div><button type="submit">${role === "coach" ? "Send request" : "Publish session"}</button><p class="schedule-status" aria-live="polite"></p></form>` : ""}<div class="schedule-admin"><h3>Coach workload & requests</h3><div class="schedule-workload"></div><div class="schedule-requests"></div></div>`;
    root.append(panel);
    let items = [];
    const render = () => {
      const y = cursor.getFullYear(), m = cursor.getMonth();
      panel.querySelector("[data-month-label]").textContent = cursor.toLocaleDateString(undefined,{month:"long",year:"numeric"});
      const first = (new Date(y,m,1).getDay()+6)%7, count = new Date(y,m+1,0).getDate();
      const cells = Array(first).fill(null).concat(Array.from({length:count},(_,i)=>new Date(y,m,i+1)));
      while(cells.length%7) cells.push(null);
      panel.querySelector(".schedule-days").innerHTML = cells.map(d=>{ if(!d)return '<span class="schedule-day empty" aria-hidden="true"></span>'; const key=`${y}-${String(m+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`, found=items.filter(x=>dateKey(x.date)===key); return `<button type="button" class="schedule-day ${key===dateKey(new Date().toISOString().slice(0,10))?"today":""}" data-day="${key}" aria-label="${key}${found.length?`, ${found.length} scheduled item${found.length===1?"":"s"}`:""}"><span>${d.getDate()}</span><i>${[...new Set(found.map(x=>x.kind))].map(k=>`<b class="${esc(k)}"></b>`).join("")}</i></button>`; }).join("");
      panel.querySelector(".schedule-items").innerHTML = items.filter(x=>dateKey(x.date)>=dateKey(new Date().toISOString())).slice(0,12).map(x=>`<article class="schedule-item ${esc(x.kind)}"><div><b>${esc(x.title)}</b><small>${esc(x.date)} · ${esc(x.time||"")}</small><small>${esc(x.venue||"Venue TBA")}${x.coach?` · ${esc(x.coach)}`:""}</small></div><span>${esc(x.kind)}</span></article>`).join("") || '<p class="schedule-muted">No upcoming sessions or events.</p>';
    };
    const reload = async () => {
      try {
        const [sessions, events] = await Promise.all([api("/api/fit-track/schedule"),api("/api/dashboard/events")]);
        items = sessions.map(s=>({date:s.session_date,time:`${s.start_time}–${s.end_time}`,title:s.title||s.programme,venue:s.venue,coach:s.coach,kind:s.session_type||"practice"})).concat(events.map(e=>({date:e.event_date,title:e.title,venue:e.venue,kind:"event"}))).sort((a,b)=>`${a.date} ${a.time||""}`.localeCompare(`${b.date} ${b.time||""}`)); render();
      } catch (e) { panel.querySelector(".schedule-items").textContent=e.message; }
    };
    panel.querySelectorAll("[data-month]").forEach(b=>b.addEventListener("click",()=>{cursor.setMonth(cursor.getMonth()+Number(b.dataset.month));render();}));
    panel.querySelector(".schedule-add-toggle")?.addEventListener("click",()=>{const f=panel.querySelector(".schedule-form"); f.hidden=!f.hidden;});
    const form=panel.querySelector(".schedule-form");
    if(form){
      (async()=>{try{const data=await api("/api/fit-track/programmes");const list=Array.isArray(data)?data:data.data||[];form.elements.programme_id.innerHTML='<option value="">Choose programme</option>'+list.map(p=>`<option value="${p.id}">${esc(p.name)} · ${esc(p.sport)}</option>`).join("");}catch(e){form.querySelector(".schedule-status").textContent=e.message;}})();
      form.addEventListener("submit",async e=>{e.preventDefault();const b=form.querySelector("button[type=submit]");b.disabled=true;try{const d=Object.fromEntries(new FormData(form));delete d.title;await api("/api/fit-track/schedule","POST",d);form.reset();form.querySelector(".schedule-status").textContent=role==="coach"?"Request sent to admin for approval.":"Session published.";await reload();}catch(err){form.querySelector(".schedule-status").textContent=err.message;}finally{b.disabled=false;}});
    }
    if(role==="admin" || role==="coach"){
      (async()=>{try{if(role==="admin"){const [stats,requests]=await Promise.all([api("/api/coaching-schedule/workload"),api("/api/coaching-schedule/requests?status=pending")]);panel.querySelector(".schedule-workload").innerHTML=stats.map(c=>`<div class="workload-row"><b>${esc(c.coach)}</b><span>${c.assigned_dates} assigned dates · ${c.booked_dates} used</span><strong class="${c.booked_dates>c.assigned_dates?"overload":c.booked_dates<c.assigned_dates?"underload":"balanced"}">${c.booked_dates>c.assigned_dates?"Overloaded":c.booked_dates<c.assigned_dates?"Under target":"On target"}</strong></div>`).join("")||'<p class="schedule-muted">No active coach assignments yet.</p>';panel.querySelector(".schedule-requests").innerHTML=requests.map(r=>`<div class="request-row"><span>${esc(r.coach)} · ${esc(r.programme)} · ${esc(r.session_date)} ${esc(r.start_time)} · ${esc(r.session_type)}</span><button data-review="${r.id}" data-status="approved">Approve</button><button data-review="${r.id}" data-status="rejected">Decline</button></div>`).join("")||'<p class="schedule-muted">No pending requests.</p>';panel.querySelectorAll("[data-review]").forEach(b=>b.addEventListener("click",async()=>{try{await api(`/api/coaching-schedule/requests/${b.dataset.review}`,"PATCH",{status:b.dataset.status});b.closest(".request-row").remove();await reload();}catch(e){global.alert(e.message);}}));}else{const mine=await api("/api/coaching-schedule/requests");panel.querySelector(".schedule-admin h3").textContent="My session requests";panel.querySelector(".schedule-workload").remove();panel.querySelector(".schedule-requests").innerHTML=mine.map(r=>`<div class="request-row"><span>${esc(r.programme)} · ${esc(r.session_date)} ${esc(r.start_time)} · ${esc(r.session_type)}</span><strong>${esc(r.status)}</strong></div>`).join("")||'<p class="schedule-muted">No requests submitted.</p>';}}catch(e){panel.querySelector(".schedule-workload").textContent=e.message;}})();
    }
    reload();
  }
  global.DashboardSchedule={mount};
})(window);