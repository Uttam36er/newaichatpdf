document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('uploadArea');
    const pdfFile = document.getElementById('pdfFile');
    const uploadStatus = document.getElementById('uploadStatus');
    const querySection = document.getElementById('querySection');
    const questionInput = document.getElementById('questionInput');
    const askButton = document.getElementById('askButton');
    const loading = document.getElementById('loading');
    const response = document.getElementById('response');

    // Handle drag and drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.add('highlight');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.remove('highlight');
        });
    });

    // Handle file drop
    uploadArea.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    // Handle file selection via click
    uploadArea.addEventListener('click', () => {
        pdfFile.click();
    });

    pdfFile.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type === 'application/pdf') {
                uploadFile(file);
            } else {
                showStatus('Please upload a PDF file', 'error');
            }
        }
    }

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            showStatus('Uploading and processing PDF...', 'info');
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (response.ok) {
                showStatus(`${data.filename} uploaded successfully!`, 'success');
                querySection.style.display = 'block';
            } else {
                showStatus(data.error, 'error');
            }
        } catch (error) {
            showStatus('Error uploading file', 'error');
        }
    }

    function showStatus(message, type) {
        uploadStatus.textContent = message;
        uploadStatus.className = 'status-message ' + type;
    }

    // Handle question asking
    askButton.addEventListener('click', async () => {
        const question = questionInput.value.trim();
        if (!question) {
            return;
        }

        loading.style.display = 'flex';
        response.innerHTML = '';
        questionInput.value = '';

        try {
            const res = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question })
            });

            const data = await res.json();
            if (res.ok) {
                displayResponse(data);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            response.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        } finally {
            loading.style.display = 'none';
        }
    });

    function displayResponse(data) {
        const html = `
            <h3>Answer:</h3>
            <p>${data.answer}</p>
            <h4>Sources from ${data.pdf_name}:</h4>
            ${data.sources.map(source => `
                <div class="source-text">${source}</div>
            `).join('')}
        `;
        response.innerHTML = html;
    }
});
