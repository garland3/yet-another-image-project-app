/**
 * Image Gallery Manager
 * Handles image display and upload operations
 */
function imageGalleryManager() {
  return {
    projectId: null,
    images: [],
    isLoading: false,
    isUploading: false,
    selectedFiles: null,
    fileCount: 0,
    fileName: 'No file selected',
    metadataInput: '',
    dragActive: false,
    
    init() {
      // Get project ID from URL
      const urlParams = new URLSearchParams(window.location.search);
      this.projectId = urlParams.get('id');
      
      if (!this.projectId) {
        showError('Project ID is missing. Redirecting to projects page...');
        setTimeout(() => {
          window.location.href = '/ui';
        }, 3000);
        return;
      }
      
      // Load images
      this.loadImages();
    },
    
    async loadImages() {
      try {
        this.isLoading = true;
        
        console.log('Fetching images for project:', this.projectId);
        const response = await fetch(`/projects/${this.projectId}/images/`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Clone the response to log it without consuming it
        const responseClone = response.clone();
        const responseText = await responseClone.text();
        console.log('Raw response from server:', responseText);
        
        try {
          // Parse the original response
          this.images = await response.json();
          console.log('Parsed images:', this.images);
          
          if (!Array.isArray(this.images)) {
            console.error('Server response is not an array:', this.images);
            throw new Error('Invalid server response: expected an array of images');
          }
        } catch (parseError) {
          console.error('Error parsing JSON response:', parseError);
          console.error('Response text was:', responseText);
          throw new Error(`Failed to parse server response: ${parseError.message}`);
        }
        
      } catch (error) {
        console.error('Error loading images:', error);
        showError('Failed to load images. Please try again later.');
      } finally {
        this.isLoading = false;
      }
    },
    
    handleFileSelect(event) {
      const fileInput = event.target;
      this.selectedFiles = fileInput.files;
      this.updateFileInfo();
    },
    
    handleDrop(event) {
      event.preventDefault();
      this.dragActive = false;
      
      if (event.dataTransfer.files.length) {
        const fileInput = document.getElementById('file-input');
        fileInput.files = event.dataTransfer.files;
        this.selectedFiles = fileInput.files;
        this.updateFileInfo();
      }
    },
    
    updateFileInfo() {
      this.fileCount = this.selectedFiles ? this.selectedFiles.length : 0;
      
      if (this.fileCount === 1) {
        this.fileName = this.selectedFiles[0].name;
      } else if (this.fileCount > 1) {
        this.fileName = `${this.fileCount} files selected`;
      } else {
        this.fileName = 'No file selected';
      }
    },
    
    async uploadImages() {
      if (!this.selectedFiles || this.selectedFiles.length === 0) {
        showError('Please select at least one file to upload.');
        return;
      }
      
      let metadata = this.metadataInput.trim();
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
        this.isUploading = true;
        
        const uploadPromises = [];
        const newImages = [];
        
        // Upload each file
        for (let i = 0; i < this.selectedFiles.length; i++) {
          const file = this.selectedFiles[i];
          const formData = new FormData();
          formData.append('file', file);
          
          // Add metadata if available
          if (metadata) {
            formData.append('metadata', metadata);
          }
          
          const uploadPromise = fetch(`/projects/${this.projectId}/images/`, {
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
          // Add new images to the list
          this.images = [...this.images, ...successfulUploads];
          
          // Reset form
          const fileInput = document.getElementById('file-input');
          fileInput.value = '';
          this.selectedFiles = null;
          this.fileCount = 0;
          this.fileName = 'No file selected';
          this.metadataInput = '';
          
          if (successfulUploads.length === this.selectedFiles.length) {
            showSuccess(`${this.selectedFiles.length} ${this.selectedFiles.length === 1 ? 'image' : 'images'} uploaded successfully!`);
          } else {
            showSuccess(`${successfulUploads.length} of ${this.selectedFiles.length} images uploaded successfully.`);
          }
        }
        
      } catch (error) {
        console.error('Error in upload process:', error);
        showError(`Upload process failed: ${error.message}`);
      } finally {
        this.isUploading = false;
      }
    },
    
    getThumbnailUrl(imageId) {
      return `/images/${imageId}/thumbnail/`;
    },
    
    getContentUrl(imageId) {
      return `/images/${imageId}/content`;
    },
    
    formatFileSize(bytes) {
      if (!bytes) return 'Unknown size';
      
      const units = ['B', 'KB', 'MB', 'GB'];
      let size = bytes;
      let unitIndex = 0;
      
      while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
      }
      
      return `${size.toFixed(1)} ${units[unitIndex]}`;
    },
    
    viewImage(imageId) {
      window.location.href = `/ui/view?id=${imageId}&project=${this.projectId}`;
    }
  };
}
