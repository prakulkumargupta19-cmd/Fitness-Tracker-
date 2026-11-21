"use strict";

document.querySelectorAll("[data-external-handler-1]").forEach(function (element) {
  element.onclick = function (event) {
showSection('dashboard', this)
  };
});

document.querySelectorAll("[data-external-handler-2]").forEach(function (element) {
  element.onclick = function (event) {
showSection('athletes', this)
  };
});

document.querySelectorAll("[data-external-handler-3]").forEach(function (element) {
  element.onclick = function (event) {
showSection('deactivatedStudents', this)
  };
});

document.querySelectorAll("[data-external-handler-4]").forEach(function (element) {
  element.onclick = function (event) {
showSection('coaches', this)
  };
});

document.querySelectorAll("[data-external-handler-5]").forEach(function (element) {
  element.onclick = function (event) {
showSection('attendance', this)
  };
});

document.querySelectorAll("[data-external-handler-6]").forEach(function (element) {
  element.onclick = function (event) {
showSection('events', this)
  };
});

document.querySelectorAll("[data-external-handler-7]").forEach(function (element) {
  element.onclick = function (event) {
showSection('schedule', this)
  };
});

document.querySelectorAll("[data-external-handler-8]").forEach(function (element) {
  element.onclick = function (event) {
showSection('sports', this)
  };
});

document.querySelectorAll("[data-external-handler-9]").forEach(function (element) {
  element.onclick = function (event) {
showSection('liveScores', this)
  };
});

document.querySelectorAll("[data-external-handler-10]").forEach(function (element) {
  element.onclick = function (event) {
showSection('announcements', this)
  };
});

document.querySelectorAll("[data-external-handler-11]").forEach(function (element) {
  element.onclick = function (event) {
showSection('diagnostics', this)
  };
});

document.querySelectorAll("[data-external-handler-12]").forEach(function (element) {
  element.onclick = function (event) {
showSection('profile', this)
  };
});

document.querySelectorAll("[data-external-handler-13]").forEach(function (element) {
  element.onclick = function (event) {
showSection('settings', this)
  };
});

document.querySelectorAll("[data-external-handler-14]").forEach(function (element) {
  element.onclick = function (event) {
logout()
  };
});

document.querySelectorAll("[data-external-handler-15]").forEach(function (element) {
  element.onclick = function (event) {
toggleSidebar()
  };
});

document.querySelectorAll("[data-external-handler-16]").forEach(function (element) {
  element.onclick = function (event) {
showSectionByName('coaches')
  };
});

document.querySelectorAll("[data-external-handler-17]").forEach(function (element) {
  element.onclick = function (event) {
showSectionByName('attendance')
  };
});

document.querySelectorAll("[data-external-handler-18]").forEach(function (element) {
  element.onclick = function (event) {
showSectionByName('athletes')
  };
});

document.querySelectorAll("[data-external-handler-19]").forEach(function (element) {
  element.onclick = function (event) {
showSectionByName('coaches')
  };
});

document.querySelectorAll("[data-external-handler-20]").forEach(function (element) {
  element.onclick = function (event) {
showSectionByName('attendance')
  };
});

document.querySelectorAll("[data-external-handler-21]").forEach(function (element) {
  element.onclick = function (event) {
showSectionByName('announcements')
  };
});

document.querySelectorAll("[data-external-handler-22]").forEach(function (element) {
  element.onclick = function (event) {
showSectionByName('events')
  };
});

document.querySelectorAll("[data-external-handler-23]").forEach(function (element) {
  element.oninput = function (event) {
renderAthletes()
  };
});

document.querySelectorAll("[data-external-handler-24]").forEach(function (element) {
  element.onclick = function (event) {
setAthleteView('box')
  };
});

document.querySelectorAll("[data-external-handler-25]").forEach(function (element) {
  element.onclick = function (event) {
setAthleteView('list')
  };
});

document.querySelectorAll("[data-external-handler-26]").forEach(function (element) {
  element.oninput = function (event) {
renderDeactivatedStudents()
  };
});

document.querySelectorAll("[data-external-handler-27]").forEach(function (element) {
  element.onclick = function (event) {
setDeactivatedView('box')
  };
});

document.querySelectorAll("[data-external-handler-28]").forEach(function (element) {
  element.onclick = function (event) {
setDeactivatedView('list')
  };
});

document.querySelectorAll("[data-external-handler-29]").forEach(function (element) {
  element.onclick = function (event) {
this.closest('dialog').close()
  };
});

document.querySelectorAll("[data-external-handler-30]").forEach(function (element) {
  element.onchange = function (event) {
renderAttendance()
  };
});

document.querySelectorAll("[data-external-handler-31]").forEach(function (element) {
  element.onchange = function (event) {
updateAttendanceDateDisplay(); renderAttendance()
  };
});

document.querySelectorAll("[data-external-handler-32]").forEach(function (element) {
  element.onclick = function (event) {
saveAdminAttendance()
  };
});

document.querySelectorAll("[data-external-handler-33]").forEach(function (element) {
  element.onchange = function (event) {
toggleAllAttendanceRows(this.checked)
  };
});

document.querySelectorAll("[data-external-handler-34]").forEach(function (element) {
  element.onclick = function (event) {
loadAdminDiagnostics()
  };
});

document.querySelectorAll("[data-external-handler-35]").forEach(function (element) {
  element.onsubmit = function (event) {
return false;
  };
});

document.querySelectorAll("[data-external-handler-36]").forEach(function (element) {
  element.onclick = function (event) {
openAddSportModal()
  };
});

document.querySelectorAll("[data-external-handler-37]").forEach(function (element) {
  element.onclick = function (event) {
loadAdminMatches()
  };
});

document.querySelectorAll("[data-external-handler-38]").forEach(function (element) {
  element.onclick = function (event) {
loadAdminMatches()
  };
});

document.querySelectorAll("[data-external-handler-39]").forEach(function (element) {
  element.onclick = function (event) {
showSectionByName('profile')
  };
});

document.querySelectorAll("[data-external-handler-40]").forEach(function (element) {
  element.onclick = function (event) {
logout()
  };
});

document.querySelectorAll("[data-external-handler-41]").forEach(function (element) {
  element.onclick = function (event) {
closeAthleteModal()
  };
});

document.querySelectorAll("[data-external-handler-42]").forEach(function (element) {
  element.onclick = function (event) {
closeAthleteModal()
  };
});

document.querySelectorAll("[data-external-handler-43]").forEach(function (element) {
  element.onclick = function (event) {
closeAthleteModal()
  };
});

document.querySelectorAll("[data-external-handler-44]").forEach(function (element) {
  element.onclick = function (event) {
closeAddSportModal()
  };
});

document.querySelectorAll("[data-external-handler-45]").forEach(function (element) {
  element.onclick = function (event) {
closeAddSportModal()
  };
});

document.querySelectorAll("[data-external-handler-46]").forEach(function (element) {
  element.onclick = function (event) {
addAssessmentField()
  };
});

document.querySelectorAll("[data-external-handler-47]").forEach(function (element) {
  element.onclick = function (event) {
closeAddSportModal()
  };
});

document.querySelectorAll("[data-external-handler-48]").forEach(function (element) {
  element.onclick = function (event) {
closeRolePopup()
  };
});

document.querySelectorAll("[data-external-handler-49]").forEach(function (element) {
  element.onclick = function (event) {
closeRolePopup()
  };
});

document.querySelectorAll("[data-external-handler-50]").forEach(function (element) {
  element.onclick = function (event) {
savePopupRoles()
  };
});

document.querySelectorAll("[data-external-handler-51]").forEach(function (element) {
  element.onclick = function (event) {
window.loadAssessmentFields(window.currentSportId)
  };
});

document.querySelectorAll("[data-external-handler-52]").forEach(function (element) {
  element.onclick = function (event) {
window.createAssessment(window.currentSportId, 'present')
  };
});

document.querySelectorAll("[data-external-handler-53]").forEach(function (element) {
  element.onclick = function (event) {
window.viewAssessments(window.currentSportId)
  };
});
