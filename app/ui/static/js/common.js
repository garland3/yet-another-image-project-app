// Common utility functions and patterns for the Image Manager application

// Global variables that might be used across multiple files
let projectId = null;
let imageId = null;

// Initialize common variables from URL parameters
function initCommonVariables() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Get project ID and image ID from URL if available
    const urlProjectId = urlParams.get('id') || urlParams.get('project');
    const urlImageId = urlParams.get('id');
    
    // Check if we're on the project page or view page
    const isProjectPage = window.location.pathname.includes('/project');
    const isViewPage = window.location.pathname.includes('/view');
    
    // Set projectId based on context
    if (isProjectPage) {
        // On project page, the project ID is in the 'id' parameter
        projectId = urlParams.get('id');
    } else if (isViewPage) {
        // On view page, the project ID is in the 'project' parameter and image ID is in the 'id' parameter
        projectId = urlParams.get('project');
        imageId = urlParams.get('id');
    } else {
        // On index page or other pages, try to get project ID from 'id' parameter
        projectId = urlProjectId;
    }
    
    return {
        projectId,
        imageId,
        isProjectPage,
        isViewPage
    };
}

// UI Helper Functions

// Show a loading indicator in a container
function showLoader(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const loader = document.createElement('div');
    loader.className = 'loader';
    loader.innerHTML = '<div class="loading"></div>';
    
    container.appendChild(loader);
}

// Hide the loading indicator in a container
function hideLoader(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const loader = container.querySelector('.loader');
    if (loader) {
        container.removeChild(loader);
    }
}

// Show an error message
function showError(message) {
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    const alert = document.createElement('div');
    alert.className = 'alert alert-error';
    alert.textContent = message;
    
    alertsContainer.appendChild(alert);
    
    // Remove after 5 seconds
    setTimeout(() => {
        alertsContainer.removeChild(alert);
    }, 5000);
}

// Show a success message
function showSuccess(message) {
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    const alert = document.createElement('div');
    alert.className = 'alert alert-success';
    alert.textContent = message;
    
    alertsContainer.appendChild(alert);
    
    // Remove after 5 seconds
    setTimeout(() => {
        alertsContainer.removeChild(alert);
    }, 5000);
}

// Format a date string for display
function formatDate(dateString) {
    if (!dateString) return 'Unknown date';
    
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Format file size for display
function formatFileSize(bytes) {
    if (!bytes) return 'Unknown size';
    
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
}

// Parse metadata value to appropriate type
function parseMetadataValue(value) {
    // If it's empty, return null
    if (value.trim() === '') {
        return null;
    }
    
    // Try to parse as JSON
    try {
        return JSON.parse(value);
    } catch (e) {
        // If it's not valid JSON, return as string
        return value;
    }
}

// API Helper Functions

// Fetch data with error handling
async function fetchWithErrorHandling(url, options = {}) {
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            // Try to parse error response as JSON
            try {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
            } catch (jsonError) {
                // If response is not valid JSON, use status text
                throw new Error(`HTTP error! Status: ${response.status} ${response.statusText}`);
            }
        }
        
        // Try to parse response as JSON
        try {
            return await response.json();
        } catch (jsonError) {
            console.warn("Response was not valid JSON:", jsonError);
            return { status: "success", raw: await response.text() };
        }
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

// Export functions and variables for use in other files
window.common = {
    initCommonVariables,
    showLoader,
    hideLoader,
    showError,
    showSuccess,
    formatDate,
    formatFileSize,
    parseMetadataValue,
    fetchWithErrorHandling
};
