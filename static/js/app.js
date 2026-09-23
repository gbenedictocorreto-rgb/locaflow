/* LocaFlow app.js: dark mode toggle */
(function () {
  "use strict";
  var KEY = "locaflow-theme";
  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(KEY, theme);
  }
  document.addEventListener("DOMContentLoaded", function () {
    var saved = localStorage.getItem(KEY) || (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    apply(saved);
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var current = document.documentElement.getAttribute("data-theme");
        apply(current === "dark" ? "light" : "dark");
      });
    });
  });
})();
