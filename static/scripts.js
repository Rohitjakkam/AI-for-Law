// Handle query submission
document.getElementById('submit-query').addEventListener('click', async function() {
    const query = document.getElementById('query').value.trim();
    
    if (query === "") {
        alert("Please enter a query.");
        return;
    }

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ query })
        });

        const data = await response.json();
        if (response.ok && data.response) {
            const markdownResponse = data.response;
            document.getElementById("response").innerHTML = marked.parse(markdownResponse); // Use marked.parse() instead of marked()
        } else {
            document.getElementById("response").textContent = "Error: " + (data.error || "Unknown error");
        }
    } catch (error) {
        document.getElementById("response").textContent = "Error: " + error.message;
    }
});

// Handle file upload for document analysis
document.getElementById('submit-file').addEventListener('click', async function() {
    const fileInput = document.getElementById('file-upload');
    const file = fileInput.files[0];
    
    if (!file) {
        alert("Please upload a file.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        if (response.ok && data.analysis) {
            const markdownResponse = data.analysis;
            document.getElementById("response").innerHTML = marked.parse(markdownResponse); // Use marked.parse() instead of marked()
        } else {
            document.getElementById("response").textContent = "Error: " + (data.error || "Unknown error");
        }
    } catch (error) {
        document.getElementById("response").textContent = "Error: " + error.message;
    }
});
