/**
 * Image Metadata Manager
 * Handles CRUD operations for image metadata
 */
function imageMetadataManager() {
  return {
    metadata: [],
    showAddMetadataForm: false,
    editingMetadata: null,
    newMetadata: {
      key: '',
      value: ''
    },
    
    init() {
      this.loadMetadata();
    },
    
    async loadMetadata() {
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId) return;
        
        const response = await fetch(`/images/${imageId}/metadata`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        this.metadata = await response.json();
      } catch (error) {
        console.error('Error loading image metadata:', error);
        showError('Failed to load image metadata. Please try again later.');
      }
    },
    
    async addMetadata() {
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId) return;
        
        const response = await fetch(`/images/${imageId}/metadata`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            key: this.newMetadata.key,
            value: this.newMetadata.value
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }
        
        const newMetadataItem = await response.json();
        this.metadata.push(newMetadataItem);
        
        // Reset form
        this.newMetadata = { key: '', value: '' };
        this.showAddMetadataForm = false;
        
        showSuccess('Metadata added successfully!');
      } catch (error) {
        console.error('Error adding metadata:', error);
        showError(`Failed to add metadata: ${error.message}`);
      }
    },
    
    editMetadata(item) {
      this.editingMetadata = { ...item };
    },
    
    cancelEdit() {
      this.editingMetadata = null;
    },
    
    async updateMetadata() {
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId || !this.editingMetadata) return;
        
        const response = await fetch(`/images/${imageId}/metadata/${this.editingMetadata.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            value: this.editingMetadata.value
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }
        
        const updatedMetadata = await response.json();
        
        // Update the metadata in the list
        const index = this.metadata.findIndex(item => item.id === updatedMetadata.id);
        if (index !== -1) {
          this.metadata[index] = updatedMetadata;
        }
        
        this.editingMetadata = null;
        
        showSuccess('Metadata updated successfully!');
      } catch (error) {
        console.error('Error updating metadata:', error);
        showError(`Failed to update metadata: ${error.message}`);
      }
    },
    
    async deleteMetadata(id) {
      if (!confirm('Are you sure you want to delete this metadata?')) return;
      
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId) return;
        
        const response = await fetch(`/images/${imageId}/metadata/${id}`, {
          method: 'DELETE'
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Remove the metadata from the list
        this.metadata = this.metadata.filter(item => item.id !== id);
        
        showSuccess('Metadata deleted successfully!');
      } catch (error) {
        console.error('Error deleting metadata:', error);
        showError(`Failed to delete metadata: ${error.message}`);
      }
    }
  };
}
