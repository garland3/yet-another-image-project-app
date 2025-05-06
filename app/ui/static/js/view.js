// Global variables
let projectId = null;
let imageId = null;
let imageData = null;
let projectImages = [];
let currentImageIndex = -1;
let zoomLevel = 1;

// DOM Elements
document.addEventListener('DOMContentLoaded', () => {
  // Get image ID and project ID from URL
  const urlParams = new URLSearchParams(window.location.search);
  imageId = urlParams.get('id');
  projectId = urlParams.get('project');
  
  if (!imageId || !projectId) {
    showError('Image ID or Project ID is missing. Redirecting to projects page...');
    setTimeout(() => {
      window.location.href = '/ui';
    }, 3000);
    return;
  }
  
  // Initialize the UI
  initUI();
  
  // Load image data
  loadImageData();
  
  // Load all project images for navigation
  loadProjectImages();
});

function initUI() {
  // Setup event listeners
  const backButton = document.getElementById('back-button');
  const prevButton = document.getElementById('prev-button');
  const nextButton = document.getElementById('next-button');
  const zoomInButton = document.getElementById('zoom-in-button');
  const zoomOutButton = document.getElementById('zoom-out-button');
  const resetZoomButton = document.getElementById('reset-zoom-button');
  const downloadButton = document.getElementById('download-button');
  
  // Back button
  if (backButton) {
    backButton.addEventListener('click', () => {
      window.location.href = `/ui/project?id=${projectId}`;
    });
  }
  
  // Previous button
  if (prevButton) {
    prevButton.addEventListener('click', navigateToPreviousImage);
    // Initially disable until we know there's a previous image
    prevButton.disabled = true;
  }
  
  // Next button
  if (nextButton) {
    nextButton.addEventListener('click', navigateToNextImage);
    // Initially disable until we know there's a next image
    nextButton.disabled = true;
  }
  
  // Zoom controls
  if (zoomInButton) {
    zoomInButton.addEventListener('click', () => {
      zoomLevel += 0.25;
      applyZoom();
    });
  }
  
  if (zoomOutButton) {
    zoomOutButton.addEventListener('click', () => {
      zoomLevel = Math.max(0.25, zoomLevel - 0.25);
      applyZoom();
    });
  }
  
  if (resetZoomButton) {
    resetZoomButton.addEventListener('click', () => {
      zoomLevel = 1;
      applyZoom();
    });
  }
  
  // Download button
  if (downloadButton) {
    downloadButton.addEventListener('click', downloadImage);
  }
  
  // Keyboard navigation
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
      navigateToPreviousImage();
    } else if (e.key === 'ArrowRight') {
      navigateToNextImage();
    } else if (e.key === '+' || e.key === '=') {
      zoomLevel += 0.25;
      applyZoom();
    } else if (e.key === '-') {
      zoomLevel = Math.max(0.25, zoomLevel - 0.25);
      applyZoom();
    } else if (e.key === '0') {
      zoomLevel = 1;
      applyZoom();
    }
  });
}

async function loadImageData() {
  try {
    showLoader('image-display');
    
    // Fetch image metadata
    const response = await fetch(`/images/${imageId}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    imageData = await response.json();
    
    // Update image title
    updateImageTitle(imageData);
    
    // Get download URL
    const urlResponse = await fetch(`/images/${imageId}/download/`);
    
    if (!urlResponse.ok) {
      throw new Error(`HTTP error! Status: ${urlResponse.status}`);
    }
    
    const urlData = await urlResponse.json();
    
    if (!urlData || !urlData.url) {
      throw new Error('Invalid URL data received from server');
    }
    
    // Display the image
    displayImage(urlData.url);
    
    // Display metadata
    displayMetadata(imageData);
    
  } catch (error) {
    console.error('Error loading image data:', error);
    showError('Failed to load image. Please try again later.');
  } finally {
    hideLoader('image-display');
  }
}

function updateImageTitle(image) {
  const imageTitle = document.getElementById('image-title');
  
  if (imageTitle) {
    imageTitle.textContent = image.filename || 'Unnamed image';
  }
  
  // Update page title
  document.title = `${image.filename || 'Image'} - Image Manager`;
}

function displayImage(url) {
  const imageDisplay = document.getElementById('image-display');
  
  if (!imageDisplay) return;
  
  // Clear existing content
  imageDisplay.innerHTML = '';
  
  // Create image element
  const img = document.createElement('img');
  img.src = url;
  img.alt = imageData.filename || 'Image';
  img.id = 'main-image';
  img.className = 'view-image';
  
  // Add error handling for image loading
  img.onerror = () => {
    console.error('Error loading image from URL:', url);
    imageDisplay.innerHTML = '<div class="error-card">Failed to load image</div>';
  };
  
  // Append image to display
  imageDisplay.appendChild(img);
}

function displayMetadata(image) {
  const metadataContent = document.getElementById('metadata-content');
  
  if (!metadataContent) return;
  
  // Clear existing content
  metadataContent.innerHTML = '';
  
  // Create metadata table
  const table = document.createElement('table');
  table.className = 'metadata-table';
  
  // Add basic metadata
  const basicMetadata = [
    { label: 'Filename', value: image.filename || 'Unknown' },
    { label: 'Size', value: formatFileSize(image.size_bytes) },
    { label: 'Content Type', value: image.content_type || 'Unknown' },
    { label: 'Uploaded By', value: image.uploaded_by_user_id || 'Unknown' },
    { label: 'Upload Date', value: formatDate(image.created_at) }
  ];
  
  basicMetadata.forEach(item => {
    const row = table.insertRow();
    const labelCell = row.insertCell();
    const valueCell = row.insertCell();
    
    labelCell.textContent = item.label;
    labelCell.className = 'metadata-label';
    
    valueCell.textContent = item.value;
    valueCell.className = 'metadata-value';
  });
  
  // Add custom metadata if available
  if (image.metadata_ && Object.keys(image.metadata_).length > 0) {
    // Add a separator row
    const separatorRow = table.insertRow();
    const separatorCell = separatorRow.insertCell();
    separatorCell.colSpan = 2;
    separatorCell.className = 'metadata-separator';
    separatorCell.textContent = 'Custom Metadata';
    
    // Add each custom metadata field
    Object.entries(image.metadata_).forEach(([key, value]) => {
      const row = table.insertRow();
      const labelCell = row.insertCell();
      const valueCell = row.insertCell();
      
      labelCell.textContent = key;
      labelCell.className = 'metadata-label';
      
      // Format the value based on its type
      let formattedValue = value;
      if (typeof value === 'object') {
        formattedValue = JSON.stringify(value, null, 2);
      }
      
      valueCell.textContent = formattedValue;
      valueCell.className = 'metadata-value';
      
      // If it's a complex object, add a class for styling
      if (typeof value === 'object') {
        valueCell.classList.add('metadata-complex-value');
      }
    });
  } else {
    // No custom metadata
    const noMetadataRow = table.insertRow();
    const noMetadataCell = noMetadataRow.insertCell();
    noMetadataCell.colSpan = 2;
    noMetadataCell.className = 'metadata-empty';
    noMetadataCell.textContent = 'No custom metadata available';
  }
  
  metadataContent.appendChild(table);
}

async function loadProjectImages() {
  try {
    console.log('Fetching images for project:', projectId);
    const response = await fetch(`/projects/${projectId}/images/`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    projectImages = await response.json();
    
    if (!Array.isArray(projectImages)) {
      console.error('Server response is not an array:', projectImages);
      throw new Error('Invalid server response: expected an array of images');
    }
    
    // Find the index of the current image
    currentImageIndex = projectImages.findIndex(img => img.id === imageId);
    
    // Update navigation buttons
    updateNavigationButtons();
    
  } catch (error) {
    console.error('Error loading project images:', error);
    showError('Failed to load project images for navigation. Please try again later.');
  }
}

function updateNavigationButtons() {
  const prevButton = document.getElementById('prev-button');
  const nextButton = document.getElementById('next-button');
  
  if (prevButton) {
    prevButton.disabled = currentImageIndex <= 0;
  }
  
  if (nextButton) {
    nextButton.disabled = currentImageIndex >= projectImages.length - 1 || currentImageIndex === -1;
  }
}

function navigateToPreviousImage() {
  if (currentImageIndex > 0) {
    const prevImage = projectImages[currentImageIndex - 1];
    window.location.href = `/ui/view?id=${prevImage.id}&project=${projectId}`;
  }
}

function navigateToNextImage() {
  if (currentImageIndex < projectImages.length - 1) {
    const nextImage = projectImages[currentImageIndex + 1];
    window.location.href = `/ui/view?id=${nextImage.id}&project=${projectId}`;
  }
}

function applyZoom() {
  const image = document.getElementById('main-image');
  if (image) {
    image.style.transform = `scale(${zoomLevel})`;
  }
}

async function downloadImage() {
  if (!imageData) return;
  
  try {
    // Get the direct content URL
    const contentUrl = `/images/${imageId}/content`;
    
    // Create a temporary link element
    const link = document.createElement('a');
    link.href = contentUrl;
    link.download = imageData.filename || 'image';
    
    // Append to the document, click it, and remove it
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
  } catch (error) {
    console.error('Error downloading image:', error);
    showError('Failed to download image. Please try again later.');
  }
}

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

function formatDate(dateString) {
  if (!dateString) return 'Unknown';
  
  const date = new Date(dateString);
  return date.toLocaleString();
}

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
