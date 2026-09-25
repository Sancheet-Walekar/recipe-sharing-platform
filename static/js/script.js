/* ==================================================================
   RecipeShare - small interface helpers (vanilla JavaScript)

   IMPORTANT: JavaScript only improves the user experience.
   All real checks (validation, security, ownership) happen in Flask.
   ================================================================== */

// Run our code once the HTML page has fully loaded.
document.addEventListener("DOMContentLoaded", function () {
    setupFlashMessages();
});


/* ---------- Flash messages: close button + auto-hide ---------- */
function setupFlashMessages() {
    const FLASH_AUTO_HIDE_MS = 6000;
    const flashes = document.querySelectorAll(".flash");

    flashes.forEach(function (flash) {
        const closeButton = flash.querySelector(".flash-close");

        // Fade out, then remove the element from the page.
        function hideFlash() {
            flash.style.opacity = "0";
            setTimeout(function () {
                flash.remove();
            }, 400);
        }

        if (closeButton) {
            closeButton.addEventListener("click", hideFlash);
        }

        // Success/info messages disappear on their own; errors stay until closed.
        if (!flash.classList.contains("flash-error")) {
            setTimeout(hideFlash, FLASH_AUTO_HIDE_MS);
        }
    });
}
