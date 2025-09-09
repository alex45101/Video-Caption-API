const SUBMIT_BUTTOM = document.getElementById('uploadButton');
const SUBTITLE_FORM = document.getElementById('captionForm');
const PROGRESS_BAR = document.getElementById('videoStatus');
const FILE_INPUT = document.querySelector('input[type="file"]');

const api = new VideoAPI();

const JOB_INFO = {
    "job_id": undefined,
    "interval_id": undefined
};

const DEFAULT_SUBTITLE_SETTINGS = {
    "font": "Arial",
    "font_size": 24,
    "font_color": "#FFFFFF",
    "stroke_color": "#000000",
    "stroke_width": 2,
    "position_id": 1,
    "shadow": false,
    "max_chars": 30,
    "max_duration": 2.5,
    "max_gap": 1.5
};

window.onload = () => {
    SUBMIT_BUTTOM.onclick = submit;

    // Add file input change listener
    FILE_INPUT.addEventListener('change', handleFileUpload);

    //setup default values for the form
    for (let i = 0; i < SUBTITLE_FORM.length; i++) {
        let defaultValue = DEFAULT_SUBTITLE_SETTINGS[SUBTITLE_FORM[i].name];

        if(SUBTITLE_FORM[i].type === "checkbox"){
            SUBTITLE_FORM[i].checked = defaultValue;
            continue;
        }

        SUBTITLE_FORM[i].value = defaultValue;
    }
};

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
        // Find the upload label container
        const uploadLabel = document.querySelector('label[class*="border-dashed"]');
        
        // Format file size
        const fileSize = formatFileSize(file.size);
        
        // Update the upload area to show the uploaded file
        uploadLabel.className = 'flex flex-col items-center justify-center border-2 border-dashed border-green-400 bg-green-50 rounded-lg p-8 cursor-pointer transition mb-2';
        uploadLabel.innerHTML = `
            <input type="file" class="hidden" id="videoInput">
            <span class="flex flex-col items-center">
                <svg class="w-12 h-12 text-green-500 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <span class="text-green-600 font-medium">${file.name}</span>
                <span class="text-sm text-green-500 mt-1">${fileSize}</span>
            </span>
        `;
        
        // Re-attach the event listener to the new input element
        const newFileInput = uploadLabel.querySelector('input[type="file"]');
        newFileInput.addEventListener('change', handleFileUpload);
    }
}

function updateSubtitlePreview() {
    const previewElement = document.querySelector('.bg-gray-900.rounded-lg');
    
    if (!previewElement) return;
    
    // Get current form values
    const font = document.getElementById('fontInput').value;
    const fontSize = document.getElementById('fontSizeInput').value || 24;
    const fontColor = document.getElementById('fontColorInput').value;
    const strokeColor = document.getElementById('strokeColorInput').value;
    const strokeWidth = document.getElementById('strokeWidthInput').value || 2;
    const shadow = document.getElementById('shadowEnabledInput').checked;
    
    // Build the text style
    let textStyle = `
        font-family: ${font};
        font-size: ${Math.max(16, Math.min(fontSize * 0.8, 32))}px;
        color: ${fontColor};
        -webkit-text-stroke: ${strokeWidth}px ${strokeColor};
        text-stroke: ${strokeWidth}px ${strokeColor};
    `;
    
    // Add shadow if enabled
    if (shadow) {
        textStyle += `text-shadow: 2px 2px 4px rgba(0,0,0,0.8);`;
    }
    
    // Update the preview
    previewElement.innerHTML = `<span style="${textStyle}">Sample subtitle text</span>`;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function submit() {
    // Check if file is selected
    if (!FILE_INPUT.files[0]) {
        showErrorNotification("Please select a video file to upload.");
        return;
    }

    const subtitleFormData = new FormData(SUBTITLE_FORM);

    const shadowChecked = SUBTITLE_FORM.querySelector('[name="shadow"]').checked;
    subtitleFormData.set('shadow', shadowChecked);

    // Debug: Log FormData contents
    console.log("FormData contents:");
    for (let [key, value] of subtitleFormData.entries()) {
        console.log(key, value);
    }

    try {
        const data = await api.uploadVideo(FILE_INPUT.files[0], subtitleFormData);

        if (data.detail !== undefined) {
            // Handle API validation errors
            if (Array.isArray(data.detail)) {
                const errorMessages = data.detail.map(error => error.msg || error.message || 'Unknown error').join(', ');
                showErrorNotification(`Upload failed: ${errorMessages}`);
            } else {
                showErrorNotification(`Upload failed: ${data.detail}`);
            }
            console.error(data);
            return;
        }

        JOB_INFO["job_id"] = data.job_id;
        PROGRESS_BAR.value = 0;
        JOB_INFO["interval_id"] = setInterval(updateStatus, 1000);

    } catch (error) {
        console.error("Error uploading:", error);
        
        // Handle different types of errors
        let errorMessage = "An unexpected error occurred during upload.";
        
        if (error.message) {
            errorMessage = error.message;
        } else if (error.response && error.response.data) {
            errorMessage = error.response.data.detail || error.response.data.message || errorMessage;
        } else if (typeof error === 'string') {
            errorMessage = error;
        }
        
        showErrorNotification(errorMessage);
    }
}

async function updateStatus() {
    if (JOB_INFO["job_id"] === undefined) {
        clearInterval(JOB_INFO["interval_id"]);
        return;
    }

    console.log("timer happening");

    try {
        const data = await api.getJobStatus(JOB_INFO['job_id']);

        console.log(data);
        PROGRESS_BAR.value = data.progress;

        if(data.status_id >= 4){
            clearInterval(JOB_INFO["interval_id"]);
        }

        if (data.progress >= 100) {
            clearJob();

            // Find the upload video div and add the download button there
            const uploadVideoDiv = document.querySelector('.bg-white.rounded-xl.shadow.p-6.mb-6');
            
            // Check if download button already exists to avoid duplicates
            if (!uploadVideoDiv.querySelector('.download-button')) {
                const downloadBtn = document.createElement('button');
                downloadBtn.textContent = 'Download Video';
                downloadBtn.className = 'download-button w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-lg text-lg flex items-center justify-center gap-2 transition mt-4';
                downloadBtn.innerHTML = `
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    Download Video
                `;
                downloadBtn.onclick = () => downloadVideo(data.job_id);
                uploadVideoDiv.appendChild(downloadBtn);
            }
        }
    } catch (error) {
        console.error('Status check failed', error);
        showErrorNotification('Failed to check video processing status. Please refresh the page.');
        clearInterval(JOB_INFO["interval_id"]);
    }
}

async function downloadVideo(jobId) {
    try {
        const downloadUrl = `${api.baseURL}api/v1/jobs/${jobId}/download`;

        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = '';
        link.style.display = 'none';

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    catch (error) {
        console.error('Download failed:', error);
        showErrorNotification(`Download failed: ${error.message || 'Unable to download video'}`);
    }
}

function clearJob() {
    clearInterval(JOB_INFO["interval_id"]);
    JOB_INFO["job_id"] = undefined;
    JOB_INFO["interval_id"] = undefined;
}

function showErrorNotification(message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'error-notification fixed top-4 right-4 bg-red-500 text-white px-6 py-4 rounded-lg shadow-lg z-50 max-w-sm';
    notification.innerHTML = `
        <div class="flex items-center gap-3">
            <svg class="w-6 h-6 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <div>
                <div class="font-semibold">Error</div>
                <div class="text-sm">${message}</div>
            </div>
            <button class="ml-auto text-white hover:text-gray-200" onclick="this.parentElement.parentElement.remove()">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        </div>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Show notification with animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        notification.classList.add('hide');
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 300);
    }, 5000);
}