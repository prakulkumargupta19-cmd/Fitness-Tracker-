"use strict";

document.querySelectorAll("[data-external-handler-1]").forEach(function (element) {
  element.onclick = function (event) {
showSection('dashboard', this)
  };
});

document.querySelectorAll("[data-external-handler-2]").forEach(function (element) {
  element.onclick = function (event) {
showSection('attendance', this)
  };
});

document.querySelectorAll("[data-external-handler-3]").forEach(function (element) {
  element.onclick = function (event) {
showSection('athletes', this)
  };
});

document.querySelectorAll("[data-external-handler-4]").forEach(function (element) {
  element.onclick = function (event) {
showSection('announcements', this)
  };
});

document.querySelectorAll("[data-external-handler-5]").forEach(function (element) {
  element.onclick = function (event) {
showSection('events', this)
  };
});

document.querySelectorAll("[data-external-handler-6]").forEach(function (element) {
  element.onclick = function (event) {
showSection('liveScores', this)
  };
});

document.querySelectorAll("[data-external-handler-7]").forEach(function (element) {
  element.onclick = function (event) {
showSection('schedule', this)
  };
});

document.querySelectorAll("[data-external-handler-8]").forEach(function (element) {
  element.onclick = function (event) {
showSection('profile', this)
  };
});

document.querySelectorAll("[data-external-handler-9]").forEach(function (element) {
  element.onclick = function (event) {
showSection('settings', this)
  };
});

document.querySelectorAll("[data-external-handler-10]").forEach(function (element) {
  element.onclick = function (event) {
showSectionByName('profile')
  };
});

document.querySelectorAll("[data-external-handler-11]").forEach(function (element) {
  element.onclick = function (event) {
logout()
  };
});

document.querySelectorAll("[data-external-handler-12]").forEach(function (element) {
  element.onclick = function (event) {
toggleSidebar()
  };
});

document.querySelectorAll("[data-external-handler-13]").forEach(function (element) {
  element.onclick = function (event) {
showSectionByName('attendance')
  };
});

document.querySelectorAll("[data-external-handler-14]").forEach(function (element) {
  element.onclick = function (event) {
showSectionByName('athletes')
  };
});

document.querySelectorAll("[data-external-handler-15]").forEach(function (element) {
  element.onclick = function (event) {
showSectionByName('attendance')
  };
});

document.querySelectorAll("[data-external-handler-16]").forEach(function (element) {
  element.onclick = function (event) {
showSectionByName('athletes')
  };
});

document.querySelectorAll("[data-external-handler-17]").forEach(function (element) {
  element.onclick = function (event) {
loadAttendance()
  };
});

document.querySelectorAll("[data-external-handler-18]").forEach(function (element) {
  element.onchange = function (event) {
loadAttendance()
  };
});

document.querySelectorAll("[data-external-handler-19]").forEach(function (element) {
  element.onchange = function (event) {
loadAttendance()
  };
});

document.querySelectorAll("[data-external-handler-20]").forEach(function (element) {
  element.onclick = function (event) {
markAll('present')
  };
});

document.querySelectorAll("[data-external-handler-21]").forEach(function (element) {
  element.onclick = function (event) {
markAll('absent')
  };
});

document.querySelectorAll("[data-external-handler-22]").forEach(function (element) {
  element.onclick = function (event) {
saveAttendance()
  };
});

document.querySelectorAll("[data-external-handler-23]").forEach(function (element) {
  element.onclick = function (event) {
closeAthleteDetails()
  };
});

document.querySelectorAll("[data-external-handler-24]").forEach(function (element) {
  element.onchange = function (event) {
renderAthletes()
  };
});

document.querySelectorAll("[data-external-handler-25]").forEach(function (element) {
  element.onchange = function (event) {
renderAthletes()
  };
});

document.querySelectorAll("[data-external-handler-26]").forEach(function (element) {
  element.onchange = function (event) {
renderAthletes()
  };
});

document.querySelectorAll("[data-external-handler-27]").forEach(function (element) {
  element.onclick = function (event) {
resetAthleteFilters()
  };
});

document.querySelectorAll("[data-external-handler-28]").forEach(function (element) {
  element.onclick = function (event) {
setAthleteView('box')
  };
});

document.querySelectorAll("[data-external-handler-29]").forEach(function (element) {
  element.onclick = function (event) {
setAthleteView('list')
  };
});

document.querySelectorAll("[data-external-handler-30]").forEach(function (element) {
  element.onclick = function (event) {
loadCoachLiveScores()
  };
});

document.querySelectorAll("[data-external-handler-31]").forEach(function (element) {
  element.onclick = function (event) {
logout()
  };
});

document.querySelectorAll("[data-external-handler-32]").forEach(function (element) {
  element.onclick = function (event) {
document.getElementById('performanceDialog').close()
  };
});

document.querySelectorAll("[data-external-handler-33]").forEach(function (element) {
  element.onclick = function (event) {
    viewAttendanceHistory();
  };
});



document.getElementById("extraSessionForm").onsubmit = async function (event) {
  event.preventDefault();
  const form = event.currentTarget;
  const status = document.getElementById("extraSessionFormStatus");
  if (!form.reportValidity()) return;

  const startTime = document.getElementById("extraSessionStart").value;
  const endTime = document.getElementById("extraSessionEnd").value;
  if (startTime >= endTime) {
    status.textContent = "The end time must be later than the start time.";
    status.dataset.state = "error";
    return;
  }

  const submitButton = form.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  status.textContent = "Submitting your request…";
  status.dataset.state = "info";
  try {
    const data = {
      sport_id: document.getElementById("extraSessionSport").value,
      requested_date: document.getElementById("extraSessionDate").value,
      start_time: startTime,
      end_time: endTime,
    };

    await apiRequest("/api/coach/request-extra-session", {
      method: "POST",
      body: JSON.stringify(data)
    });

    status.textContent = "Request submitted. An administrator will review it.";
    status.dataset.state = "success";
  } catch (err) {
    status.textContent = err.message || "The extra session request could not be submitted.";
    status.dataset.state = "error";
  } finally {
    submitButton.disabled = false;
  }
};
