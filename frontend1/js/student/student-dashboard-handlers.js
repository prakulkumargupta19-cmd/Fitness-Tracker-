"use strict";

document.querySelectorAll("[data-external-handler-1]").forEach(function (element) {
  element.onclick = function (event) {
switchSection('profile-view')
  };
});

document.querySelectorAll("[data-external-handler-2]").forEach(function (element) {
  element.onclick = function (event) {
switchSection('settings-view')
  };
});

document.querySelectorAll("[data-external-handler-3]").forEach(function (element) {
  element.onclick = function (event) {
switchSection('goals')
  };
});

document.querySelectorAll("[data-external-handler-4]").forEach(function (element) {
  element.onclick = function (event) {
switchSection('attendance')
  };
});

document.querySelectorAll("[data-external-handler-5]").forEach(function (element) {
  element.onclick = function (event) {
switchSection('attendance')
  };
});

document.querySelectorAll("[data-external-handler-6]").forEach(function (element) {
  element.onclick = function (event) {
switchSection('feedback')
  };
});

document.querySelectorAll("[data-external-handler-7]").forEach(function (element) {
  element.onclick = function (event) {
toggleEditProfile()
  };
});

document.querySelectorAll("[data-external-handler-8]").forEach(function (element) {
  element.onsubmit = function (event) {
saveStudentProfile(event)
  };
});

document.querySelectorAll("[data-external-handler-9]").forEach(function (element) {
  element.onclick = function (event) {
toggleEditProfile()
  };
});
