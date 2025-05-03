/**
 * Project Page Functionality
 * Handles project header and navigation
 */

// DOM Elements
document.addEventListener('DOMContentLoaded', () => {
  // Initialize the UI
  initUI();
  
  // Load project data
  loadProject();
});

function initUI() {
  // Setup event listeners
  const backButton = document.getElementById('back-button');
  
  // Back button
  if (backButton) {
    backButton.addEventListener('click', () => {
      window.location.href = '/ui';
    });
  }
}

async function loadProject() {
  try {
    // Get project ID from URL
    const urlParams = new URLSearchParams(window.location.search);
    const projectId = urlParams.get('id');
    
    if (!projectId) {
      showError('Project ID is missing. Redirecting to projects page...');
      setTimeout(() => {
        window.location.href = '/ui';
      }, 3000);
      return;
    }
    
    showLoader('project-header');
    
    const response = await fetch(`/projects/${projectId}/`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    const projectData = await response.json();
    
    // Update project header
    updateProjectHeader(projectData);
    
  } catch (error) {
    console.error('Error loading project:', error);
    showError('Failed to load project details. Please try again later.');
  } finally {
    hideLoader('project-header');
  }
}

function updateProjectHeader(project) {
  const projectTitle = document.getElementById('project-title');
  const projectDescription = document.getElementById('project-description');
  
  if (projectTitle) {
    projectTitle.textContent = project.name;
  }
  
  if (projectDescription) {
    projectDescription.textContent = project.description || 'No description provided.';
  }
  
  // Update page title
  document.title = `${project.name} - Image Manager`;
}

// Utility functions for UI feedback
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
