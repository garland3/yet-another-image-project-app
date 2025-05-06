// Global variables
// projectId is already declared in project.js
let projectMetadata = {};

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Get project ID from URL if available
    const urlParams = new URLSearchParams(window.location.search);
    projectId = urlParams.get('id');
    
    // Initialize event listeners
    initEventListeners();
    
    // If we have a project ID, load the metadata for that project
    if (projectId) {
        loadProjectMetadata(projectId);
    }
});

// Initialize event listeners
function initEventListeners() {
    // Add metadata form submission
    const addMetadataForm = document.getElementById('add-metadata-form');
    if (addMetadataForm) {
        addMetadataForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const metadataKey = document.getElementById('metadata-key').value;
            const metadataValue = document.getElementById('metadata-value').value;
            
            if (metadataKey.trim() === '') {
                showError('Metadata key cannot be empty');
                return;
            }
            
            createOrUpdateMetadata(metadataKey, parseMetadataValue(metadataValue));
        });
    }
    
    // Bulk update metadata form submission
    const bulkUpdateForm = document.getElementById('bulk-update-metadata-form');
    if (bulkUpdateForm) {
        bulkUpdateForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const metadataJson = document.getElementById('metadata-json').value;
            
            try {
                const metadataObj = JSON.parse(metadataJson);
                bulkUpdateMetadata(metadataObj);
            } catch (error) {
                showError('Invalid JSON format for metadata');
            }
        });
    }
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

// Load metadata for a project
async function loadProjectMetadata(projectId) {
    try {
        showLoader('metadata-container');
        
        const response = await fetch(`/projects/${projectId}/metadata-dict`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        projectMetadata = await response.json();
        
        // Display the metadata
        displayMetadata(projectMetadata);
        
        // Update the bulk update form if it exists
        updateBulkUpdateForm(projectMetadata);
        
    } catch (error) {
        console.error('Error loading metadata:', error);
        showError('Failed to load metadata. Please try again later.');
    } finally {
        hideLoader('metadata-container');
    }
}

// Display metadata in the UI
function displayMetadata(metadata) {
    const metadataContainer = document.getElementById('metadata-container');
    if (!metadataContainer) return;
    
    // Clear existing content
    metadataContainer.innerHTML = '';
    
    if (!metadata || Object.keys(metadata).length === 0) {
        metadataContainer.innerHTML = '<p>No metadata defined for this project. Add metadata to get started.</p>';
        return;
    }
    
    // Create a table for metadata
    const metadataTable = document.createElement('table');
    metadataTable.className = 'metadata-table';
    
    // Create table header
    const tableHeader = document.createElement('thead');
    const headerRow = document.createElement('tr');
    
    const keyHeader = document.createElement('th');
    keyHeader.textContent = 'Key';
    
    const valueHeader = document.createElement('th');
    valueHeader.textContent = 'Value';
    
    const actionsHeader = document.createElement('th');
    actionsHeader.textContent = 'Actions';
    
    headerRow.appendChild(keyHeader);
    headerRow.appendChild(valueHeader);
    headerRow.appendChild(actionsHeader);
    tableHeader.appendChild(headerRow);
    metadataTable.appendChild(tableHeader);
    
    // Create table body
    const tableBody = document.createElement('tbody');
    
    Object.entries(metadata).forEach(([key, value]) => {
        const row = document.createElement('tr');
        
        const keyCell = document.createElement('td');
        keyCell.textContent = key;
        
        const valueCell = document.createElement('td');
        valueCell.className = 'metadata-value';
        
        // Format the value based on its type
        if (value === null) {
            valueCell.textContent = 'null';
            valueCell.classList.add('metadata-null');
        } else if (typeof value === 'object') {
            const pre = document.createElement('pre');
            pre.textContent = JSON.stringify(value, null, 2);
            valueCell.appendChild(pre);
            valueCell.classList.add('metadata-object');
        } else {
            valueCell.textContent = value.toString();
        }
        
        const actionsCell = document.createElement('td');
        actionsCell.className = 'metadata-actions';
        
        const editButton = document.createElement('button');
        editButton.className = 'btn btn-small';
        editButton.textContent = 'Edit';
        editButton.addEventListener('click', () => {
            // Populate the edit form
            document.getElementById('edit-metadata-key').value = key;
            document.getElementById('edit-metadata-value').value = 
                typeof value === 'object' ? JSON.stringify(value, null, 2) : (value === null ? '' : value);
            
            // Show the edit form
            document.getElementById('edit-metadata-modal').style.display = 'block';
        });
        
        const deleteButton = document.createElement('button');
        deleteButton.className = 'btn btn-small btn-danger';
        deleteButton.textContent = 'Delete';
        deleteButton.addEventListener('click', () => {
            if (confirm(`Are you sure you want to delete the metadata key "${key}"?`)) {
                deleteMetadata(key);
            }
        });
        
        actionsCell.appendChild(editButton);
        actionsCell.appendChild(deleteButton);
        
        row.appendChild(keyCell);
        row.appendChild(valueCell);
        row.appendChild(actionsCell);
        
        tableBody.appendChild(row);
    });
    
    metadataTable.appendChild(tableBody);
    metadataContainer.appendChild(metadataTable);
}

// Update the bulk update form
function updateBulkUpdateForm(metadata) {
    const metadataJson = document.getElementById('metadata-json');
    if (!metadataJson) return;
    
    metadataJson.value = JSON.stringify(metadata, null, 2);
}

// Create or update metadata
async function createOrUpdateMetadata(key, value) {
    try {
        showLoader('add-metadata-form');
        
        const response = await fetch(`/projects/${projectId}/metadata/${key}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                key: key,
                value: value,
            }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Update the metadata
        projectMetadata[key] = value;
        
        // Update the UI
        displayMetadata(projectMetadata);
        updateBulkUpdateForm(projectMetadata);
        
        // Reset the form
        document.getElementById('metadata-key').value = '';
        document.getElementById('metadata-value').value = '';
        
        showSuccess(`Metadata key "${key}" ${projectMetadata[key] !== undefined ? 'updated' : 'created'} successfully!`);
        
    } catch (error) {
        console.error('Error creating/updating metadata:', error);
        showError('Failed to create/update metadata. Please try again later.');
    } finally {
        hideLoader('add-metadata-form');
    }
}

// Bulk update metadata
async function bulkUpdateMetadata(metadata) {
    try {
        showLoader('bulk-update-metadata-form');
        
        const response = await fetch(`/projects/${projectId}/metadata-dict`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(metadata),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Update the metadata
        projectMetadata = await response.json();
        
        // Update the UI
        displayMetadata(projectMetadata);
        updateBulkUpdateForm(projectMetadata);
        
        showSuccess('Metadata updated successfully!');
        
    } catch (error) {
        console.error('Error bulk updating metadata:', error);
        showError('Failed to update metadata. Please try again later.');
    } finally {
        hideLoader('bulk-update-metadata-form');
    }
}

// Delete metadata
async function deleteMetadata(key) {
    try {
        showLoader('metadata-container');
        
        const response = await fetch(`/projects/${projectId}/metadata/${key}`, {
            method: 'DELETE',
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Remove the metadata
        delete projectMetadata[key];
        
        // Update the UI
        displayMetadata(projectMetadata);
        updateBulkUpdateForm(projectMetadata);
        
        showSuccess(`Metadata key "${key}" deleted successfully!`);
        
    } catch (error) {
        console.error('Error deleting metadata:', error);
        showError('Failed to delete metadata. Please try again later.');
    } finally {
        hideLoader('metadata-container');
    }
}

// Utility functions
function showLoader(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const loader = document.createElement('div');
    loader.className = 'loader';
    loader.innerHTML = '<div class="loading"></div>';
    
    container.appendChild(loader);
}

function hideLoader(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const loader = container.querySelector('.loader');
    if (loader) {
        container.removeChild(loader);
    }
}

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
