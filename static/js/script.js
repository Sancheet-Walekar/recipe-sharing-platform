/* ==================================================================
   RecipeShare - small interface helpers (vanilla JavaScript)

   IMPORTANT: JavaScript only improves the user experience.
   All real checks (validation, security, ownership) happen in Flask.
   ================================================================== */

// Run our code once the HTML page has fully loaded.
document.addEventListener("DOMContentLoaded", function () {
    setupFlashMessages();
    setupConfirmForms();
    setupImagePreview();
    setupFilterAutoSubmit();
    setupStarRating();
});


/* ---------- Review form: show a word for the chosen star rating ---------- */
function setupStarRating() {
    const starBox = document.querySelector(".star-input");
    if (!starBox) {
        return;
    }

    const text = starBox.querySelector(".star-input-text");
    const words = { 1: "Poor", 2: "Fair", 3: "Good", 4: "Very good", 5: "Excellent" };

    starBox.querySelectorAll("input[name='rating']").forEach(function (radio) {
        radio.addEventListener("change", function () {
            text.textContent = radio.value + " out of 5 - " + words[radio.value];
        });
    });
}


/* ---------- Recipes page: apply a filter as soon as it changes ---------- */
// The Search button still works without JavaScript; this just saves a click.
function setupFilterAutoSubmit() {
    const selects = document.querySelectorAll("#filter-form .auto-submit");

    selects.forEach(function (select) {
        select.addEventListener("change", function () {
            select.form.submit();
        });
    });
}


/* ---------- Recipe photo: preview + quick size/type check ---------- */
function setupImagePreview() {
    const input = document.querySelector(".image-input");
    if (!input) {
        return; // this page has no image upload field
    }

    const preview = input.parentElement.querySelector(".image-preview");
    const maxMegabytes = Number(input.dataset.maxMb) || 2;
    const allowedTypes = ["image/jpeg", "image/png", "image/webp"];

    // A small red message under the field (created once, reused)
    const message = document.createElement("small");
    message.className = "field-error";
    input.insertAdjacentElement("afterend", message);

    input.addEventListener("change", function () {
        const file = input.files[0];
        message.textContent = "";
        preview.hidden = true;

        if (!file) {
            return;
        }

        if (!allowedTypes.includes(file.type)) {
            message.textContent = "Please choose a JPG, PNG or WEBP image.";
            input.value = "";
            return;
        }

        if (file.size > maxMegabytes * 1024 * 1024) {
            message.textContent = "This image is larger than " + maxMegabytes + " MB. Please choose a smaller one.";
            input.value = "";
            return;
        }

        // Show the chosen picture before it is uploaded
        preview.src = URL.createObjectURL(file);
        preview.hidden = false;
    });
}


/* ---------- "Are you sure?" before dangerous actions ---------- */
// Any <form data-confirm="Question?"> asks the question before submitting.
function setupConfirmForms() {
    const forms = document.querySelectorAll("form[data-confirm]");

    forms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const question = form.getAttribute("data-confirm");
            if (!window.confirm(question)) {
                event.preventDefault(); // user clicked "Cancel": do not submit
            }
        });
    });
}


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
