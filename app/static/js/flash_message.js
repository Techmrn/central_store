

//Auto showing success flash message - Removal Temperory

document.addEventListener("DOMContentLoaded", () => {

    const alerts = document.querySelectorAll(".alert");

    if (alerts.length > 0) {

        // Remove ?success=... from URL
        const url = new URL(window.location);
        url.searchParams.delete("success");

        window.history.replaceState({}, "", url);

        alerts.forEach(alert => {

            setTimeout(() => {

                if (alert.parentNode) {
                    bootstrap.Alert
                        .getOrCreateInstance(alert)
                        .close();
                }

            }, 3000);

        });

    }

});