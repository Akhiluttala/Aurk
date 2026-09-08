"use strict";
const menu = document.querySelector(".admin-menu-toggle");
if (menu) {
  menu.hidden = false;
  document.body.classList.add("admin-nav-ready");
  menu.addEventListener("click", () => {
    const open = document.body.classList.toggle("admin-menu-open");
    menu.setAttribute("aria-expanded", String(open));
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && document.body.classList.contains("admin-menu-open")) {
      document.body.classList.remove("admin-menu-open");
      menu.setAttribute("aria-expanded", "false");
      menu.focus();
    }
  });
}
// Native form submissions retain browser network error/retry behavior. No optimistic mutations.
document.querySelectorAll('form[method="post"]').forEach(form => {
  form.addEventListener("submit", event => {
    if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
      event.preventDefault();
      return;
    }
    // Defer disabling until the clicked button's name/value has been serialized.
    window.setTimeout(() => {
      form.setAttribute("aria-busy", "true");
      form.querySelectorAll('button[type="submit"],button:not([type])').forEach(button => {
        button.dataset.originalText = button.textContent;
        button.disabled = true;
        button.textContent = "Saving...";
      });
    }, 0);
  });
});
window.addEventListener("pageshow", () => {
  document.querySelectorAll("form[aria-busy]").forEach(form => form.removeAttribute("aria-busy"));
  document.querySelectorAll("button[data-original-text]").forEach(button => {
    button.disabled = false;
    button.textContent = button.dataset.originalText;
    delete button.dataset.originalText;
  });
});
