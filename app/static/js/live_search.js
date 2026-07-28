
// --------------JS FOR LIVE SEARCH.....................

document.addEventListener("DOMContentLoaded", function () {

    const searchInput = document.getElementById("search-input");

    if (!searchInput) return;

    let timer = null;

    searchInput.addEventListener("keyup", function () {

        clearTimeout(timer);

        timer = setTimeout(function () {

            loadTable(1);

        }, 300);

    });

});


function loadTable(page = 1) {

    const search = document.getElementById("search-input").value;

    // Get current module URL
    const baseUrl = window.location.pathname.replace(/\/$/, "");

    // Loader
    const spinner = document.getElementById("loading-spinner");
    const table = document.getElementById("table-container");

    spinner.classList.remove("d-none");
    table.style.opacity = "0.5";

    fetch(
        `${baseUrl}/table?search=${encodeURIComponent(search)}&page=${page}`
    )
    .then(response => {
        if (!response.ok) {
            throw new Error("Failed to load data");
        }
        return response.text();
    })
    .then(html => {
        table.innerHTML = html;

        // Hide loader after successful response
        spinner.classList.add("d-none");
        table.style.opacity = "1";
    })
    .catch(error => {

        // Hide loader even if an error occurs
        spinner.classList.add("d-none");
        table.style.opacity = "1";

        console.error(error);
    });
}
