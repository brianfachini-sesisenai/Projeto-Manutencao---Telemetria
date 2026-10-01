/* Aplica o tema salvo antes do primeiro render para evitar "flash" de tema errado. */
(function () {
  try {
    var saved = JSON.parse(localStorage.getItem("theme"));
    var t = saved || (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", t);
  } catch (e) { document.documentElement.setAttribute("data-theme", "light"); }
})();
