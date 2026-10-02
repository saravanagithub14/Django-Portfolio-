// Light/dark toggle for every [data-theme-toggle] button. The saved choice is applied before
// first paint by the inline script in each page's <head>; this file only handles clicks.
(function () {
  var root = document.documentElement;

  function isLight() {
    return root.dataset.theme
      ? root.dataset.theme === "light"
      : matchMedia("(prefers-color-scheme: light)").matches;
  }

  function label() {
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.textContent = isLight() ? "Dark mode" : "Light mode";
      btn.setAttribute("aria-pressed", String(isLight()));
    });
  }

  document.addEventListener("click", function (e) {
    if (!e.target.closest("[data-theme-toggle]")) return;
    root.dataset.theme = isLight() ? "dark" : "light";
    try { localStorage.setItem("theme", root.dataset.theme); } catch (err) {}
    label();
    document.dispatchEvent(new CustomEvent("themechange"));
  });

  label();
})();
