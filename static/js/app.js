document.querySelectorAll("[data-loading-form]").forEach((form) => {
  form.addEventListener("submit", () => {
    const button = form.querySelector('button[type="submit"]');

    if (!button) {
      return;
    }

    button.disabled = true;
    button.classList.add("is-loading");
  });
});

const dialog = document.getElementById("totpDialog");
const downloadName = document.getElementById("downloadName");

if (dialog) {
  document.querySelectorAll("[data-download-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const form = dialog.querySelector("form");
      const input = dialog.querySelector("input");
      form.action = button.dataset.downloadAction;
      form.reset();

      if (downloadName) {
        downloadName.textContent = "دانلود " + button.dataset.downloadName + " نیاز به کد TOTP دارد.";
      }

      dialog.showModal();
      setTimeout(() => input.focus(), 80);
    });
  });
}
