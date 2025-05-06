// Global variables
let projectData = null;
let images = [];

// DOM Elements
document.addEventListener('DOMContentLoaded', () => {
  // Initialize common variables
  const { projectId: urlProjectId } = common.initCommonVariables();
  
  // Set global projectId from common
  projectId = window.common.projectId;
  
  if (!projectId) {
    common.showError('Project ID is missing. Redirecting to projects page...');
    setTimeout(() => {
      window.location.href = '/ui';
    }, 3000);
    return;
  }
  
  // Initialize the UI
  initUI();
  
  // Load project data
  loadProject();
  
  // Load images
  loadImages();
});

function initUI() {
  // Setup event listeners
  const uploadForm = document.getElementById('upload-form');
  const uploadArea = document.getElementById('upload-area');
  const fileInput = document.getElementById('file-input');
  const backButton = document.getElementById('back-button');
  
  // Upload form submission
  if (uploadForm) {
    uploadForm.addEventListener('submit', (e) => {
      e.preventDefault();
      uploadImage();
    });
  }
  
  // Upload area click
  if (uploadArea && fileInput) {
    uploadArea.addEventListener('click', () => {
      fileInput.click();
    });
    
    // File input change
    fileInput.addEventListener('change', () => {
      const fileCount = fileInput.files.length;
      let fileName = 'No file selected';
      
      if (fileCount === 1) {
        fileName = fileInput.files[0].name;
      } else if (fileCount > 1) {
        fileName = `${fileCount} files selected`;
      }
      
      document.getElementById('file-name').textContent = fileName;
    });
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
      uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadArea.classList.remove('dragover');
      
      if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        const fileCount = fileInput.files.length;
        let fileName = 'No file selected';
        
        if (fileCount === 1) {
          fileName = fileInput.files[0].name;
        } else if (fileCount > 1) {
          fileName = `${fileCount} files selected`;
        }
        
        document.getElementById('file-name').textContent = fileName;
      }
    });
  }
  
  // Back button
  if (backButton) {
    backButton.addEventListener('click', () => {
      window.location.href = '/ui';
    });
  }
}

async function loadProject() {
  try {
    showLoader('project-header');
    
    projectData = await common.fetchWithErrorHandling(`/projects/${projectId}/`);
    
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

async function loadImages() {
  try {
    showLoader('images-container');
    
    console.log('Fetching images for project:', projectId);
    
    images = await common.fetchWithErrorHandling(`/projects/${projectId}/images/`);
    console.log('Parsed images:', images);
    
    if (!Array.isArray(images)) {
      console.error('Server response is not an array:', images);
      throw new Error('Invalid server response: expected an array of images');
    }
    
    // Display images - await since displayImages is now async
    await displayImages(images);
    
  } catch (error) {
    console.error('Error loading images:', error);
    showError('Failed to load images. Please try again later.');
  } finally {
    hideLoader('images-container');
  }
}

async function displayImages(images) {
  const imagesContainer = document.getElementById('images-container');
  
  if (!imagesContainer) return;
  
  // Clear existing content
  imagesContainer.innerHTML = '';
  
  if (!images || images.length === 0) {
    imagesContainer.innerHTML = '<p>No images found. Upload an image to get started.</p>';
    return;
  }
  
  console.log('Displaying images:', images);
  
  // Validate images array
  const validImages = images.filter(image => {
    if (!image || !image.id) {
      console.error('Invalid image object in array:', image);
      return false;
    }
    return true;
  });
  
  console.log(`Found ${validImages.length} valid images out of ${images.length} total`);
  
  if (validImages.length === 0) {
    imagesContainer.innerHTML = '<p>No valid images found. The images data may be corrupted.</p>';
    return;
  }
  
  // Create image gallery
  const gallery = document.createElement('div');
  gallery.className = 'image-gallery';
  
  try {
    // Use Promise.all to wait for all image cards to be created
    console.log('Creating image cards...');
    const imageCardsPromises = validImages.map(image => {
      return createImageCard(image).catch(error => {
        console.error(`Error creating card for image ${image.id}:`, error);
        // Return a fallback card on error
        const fallbackCard = document.createElement('div');
        fallbackCard.className = 'error-card';
        fallbackCard.textContent = `Error: ${error.message}`;
        return fallbackCard;
      });
    });
    
    const imageCards = await Promise.all(imageCardsPromises);
    console.log(`Created ${imageCards.length} image cards`);
    
    // Append each image card to the gallery
    imageCards.forEach((imageCard, index) => {
      if (imageCard && imageCard instanceof Node) {
        gallery.appendChild(imageCard);
      } else {
        console.error(`Image card at index ${index} is not a valid DOM node:`, imageCard);
      }
    });
    
    imagesContainer.appendChild(gallery);
  } catch (error) {
    console.error('Error in displayImages:', error);
    imagesContainer.innerHTML = `<p>Error displaying images: ${error.message}</p>`;
  }
}

async function createImageCard(image) {
  // Create a card element that will be returned
  const card = document.createElement('div');
  card.className = 'image-card';
  
  try {
    // Validate image object
    if (!image || !image.id) {
      throw new Error('Invalid image data');
    }
    
    console.log('Creating card for image:', image.id);
    
    // Get download URL
    const urlData = await common.fetchWithErrorHandling(`/images/${image.id}/download/`);
    console.log('URL data received:', urlData);
    
    if (!urlData || !urlData.url) {
      throw new Error('Invalid URL data received from server');
    }
    
    // Create image element
    const img = document.createElement('img');
    img.src = urlData.url;
    img.alt = image.filename || 'Image';
    img.loading = 'lazy';
    
    // Add error handling for image loading
    img.onerror = () => {
      console.error('Error loading image from URL:', urlData.url);
      card.querySelector('.image-info')?.remove();
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-card';
      errorDiv.textContent = 'Failed to load image';
      card.appendChild(errorDiv);
    };
    
    // Create image info
    const info = document.createElement('div');
    info.className = 'image-info';
    
    const filename = document.createElement('p');
    filename.textContent = image.filename || 'Unnamed image';
    
    const size = document.createElement('small');
    size.textContent = formatFileSize(image.size_bytes);
    
    info.appendChild(filename);
    info.appendChild(size);
    
    // Add click event to open image in view page
    card.addEventListener('click', () => {
      window.location.href = `/ui/view?id=${image.id}&project=${projectId}`;
    });
    
    // Append elements to card
    card.appendChild(img);
    card.appendChild(info);
    
  } catch (error) {
    console.error('Error creating image card:', error);
    
    // Create fallback card
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-card';
    errorDiv.textContent = 'Failed to load image: ' + error.message;
    
    card.appendChild(errorDiv);
  }
  
  // Ensure we're returning a DOM node
  if (!(card instanceof Node)) {
    console.error('Card is not a DOM Node:', card);
    const fallbackCard = document.createElement('div');
    fallbackCard.className = 'error-card';
    fallbackCard.textContent = 'Error creating image card';
    return fallbackCard;
  }
  
  return card;
}

async function uploadImage() {
  const fileInput = document.getElementById('file-input');
  const metadataInput = document.getElementById('metadata-input');
  
  if (!fileInput || !fileInput.files.length) {
    showError('Please select at least one file to upload.');
    return;
  }
  
  const files = fileInput.files;
  let metadata = metadataInput?.value.trim() || '';
  let parsedMetadata = null;
  
  // Validate metadata JSON if provided
  if (metadata) {
    try {
      parsedMetadata = JSON.parse(metadata);
    } catch (error) {
      showError('Invalid JSON format for metadata.');
      return;
    }
  }
  
  try {
    showLoader('upload-form');
    
    const uploadPromises = [];
    const newImages = [];
    
    // Upload each file
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append('file', file);
      
      // Add metadata if available
      if (metadata) {
        formData.append('metadata', metadata);
      }
      
      const uploadPromise = fetch(`/projects/${projectId}/images/`, {
        method: 'POST',
        body: formData
      })
      .then(async response => {
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
        
        try {
          return await response.json();
        } catch (jsonError) {
          // Handle case where response is not valid JSON
          console.warn("Response was not valid JSON:", jsonError);
          return { filename: file.name, status: "uploaded" };
        }
      })
      .then(newImage => {
        newImages.push(newImage);
        return newImage;
      })
      .catch(error => {
        console.error(`Error uploading ${file.name}:`, error);
        showError(`Failed to upload ${file.name}: ${error.message}`);
        return null;
      });
      
      uploadPromises.push(uploadPromise);
    }
    
    // Wait for all uploads to complete
    const results = await Promise.all(uploadPromises);
    const successfulUploads = results.filter(result => result !== null);
    
    if (successfulUploads.length > 0) {
      // Add new images to the list and refresh display
      images = [...images, ...successfulUploads];
      await displayImages(images);
      
      // Reset form
      fileInput.value = '';
      if (metadataInput) metadataInput.value = '';
      document.getElementById('file-name').textContent = 'No file selected';
      
      if (successfulUploads.length === files.length) {
        showSuccess(`${files.length} ${files.length === 1 ? 'image' : 'images'} uploaded successfully!`);
      } else {
        showSuccess(`${successfulUploads.length} of ${files.length} images uploaded successfully.`);
      }
    }
    
  } catch (error) {
    console.error('Error in upload process:', error);
    showError(`Upload process failed: ${error.message}`);
  } finally {
    hideLoader('upload-form');
  }
}

// Use common utility functions
const formatFileSize = common.formatFileSize;
const showLoader = common.showLoader;
const hideLoader = common.hideLoader;
const showError = common.showError;
const showSuccess = common.showSuccess;
