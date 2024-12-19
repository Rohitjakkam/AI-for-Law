// Add loading animation HTML and CSS
const loadingHTML = `<div class="loading-spinner"></div>`;

// Handle query submission
document.getElementById('submit-query').addEventListener('click', async function () {
    const query = document.getElementById('query').value.trim();
    const responseContainer = document.getElementById("response");

    if (query === "") {
        alert("Please enter a query.");
        return;
    }

    // Show loading animation
    responseContainer.innerHTML = loadingHTML;

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ query }),
        });

        const data = await response.json();
        if (response.ok && data.response) {
            const markdownResponse = data.response;
            responseContainer.innerHTML = marked.parse(markdownResponse);
        } else {
            responseContainer.textContent = "Error: " + (data.error || "Unknown error occurred.");
        }
    } catch (error) {
        responseContainer.textContent = "Error: " + error.message;
    }
});

// Trigger file input when upload button is clicked
document.getElementById('upload-btn').addEventListener('click', function () {
    document.getElementById('file-upload').click();
});

// Handle file upload for document analysis
document.getElementById('file-upload').addEventListener('change', async function () {
    const file = this.files[0];
    const responseContainer = document.getElementById("response");

    if (!file) {
        alert("No file selected. Please choose a file.");
        return;
    }

    // Show loading animation
    responseContainer.innerHTML = loadingHTML;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            body: formData,
        });

        const data = await response.json();
        if (response.ok && data.analysis) {
            const markdownResponse = data.analysis;
            responseContainer.innerHTML = marked.parse(markdownResponse);
        } else {
            responseContainer.textContent = "Error: " + (data.error || "Unknown error occurred.");
        }
    } catch (error) {
        responseContainer.textContent = "Error: " + error.message;
    }
});