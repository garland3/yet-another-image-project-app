/**
 * Image Class Manager
 * Handles CRUD operations for image classes
 */
function imageClassManager() {
  return {
    classes: [],
    showAddClassForm: false,
    editingClass: null,
    newClass: {
      name: '',
      description: ''
    },
    
    init() {
      this.loadClasses();
    },
    
    async loadClasses() {
      try {
        const projectId = new URLSearchParams(window.location.search).get('id');
        if (!projectId) return;
        
        const response = await fetch(`/projects/${projectId}/classes`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        this.classes = await response.json();
      } catch (error) {
        console.error('Error loading image classes:', error);
        showError('Failed to load image classes. Please try again later.');
      }
    },
    
    async addClass() {
      try {
        const projectId = new URLSearchParams(window.location.search).get('id');
        if (!projectId) return;
        
        const response = await fetch(`/projects/${projectId}/classes`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            name: this.newClass.name,
            description: this.newClass.description
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }
        
        const newClass = await response.json();
        this.classes.push(newClass);
        
        // Reset form
        this.newClass = { name: '', description: '' };
        this.showAddClassForm = false;
        
        showSuccess('Class added successfully!');
      } catch (error) {
        console.error('Error adding class:', error);
        showError(`Failed to add class: ${error.message}`);
      }
    },
    
    editClass(cls) {
      this.editingClass = { ...cls };
    },
    
    cancelEdit() {
      this.editingClass = null;
    },
    
    async updateClass() {
      try {
        const projectId = new URLSearchParams(window.location.search).get('id');
        if (!projectId || !this.editingClass) return;
        
        const response = await fetch(`/projects/${projectId}/classes/${this.editingClass.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            name: this.editingClass.name,
            description: this.editingClass.description
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }
        
        const updatedClass = await response.json();
        
        // Update the class in the list
        const index = this.classes.findIndex(cls => cls.id === updatedClass.id);
        if (index !== -1) {
          this.classes[index] = updatedClass;
        }
        
        this.editingClass = null;
        
        showSuccess('Class updated successfully!');
      } catch (error) {
        console.error('Error updating class:', error);
        showError(`Failed to update class: ${error.message}`);
      }
    },
    
    async deleteClass(id) {
      if (!confirm('Are you sure you want to delete this class? This will affect any bounding boxes using this class.')) return;
      
      try {
        const projectId = new URLSearchParams(window.location.search).get('id');
        if (!projectId) return;
        
        const response = await fetch(`/projects/${projectId}/classes/${id}`, {
          method: 'DELETE'
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Remove the class from the list
        this.classes = this.classes.filter(cls => cls.id !== id);
        
        showSuccess('Class deleted successfully!');
      } catch (error) {
        console.error('Error deleting class:', error);
        showError(`Failed to delete class: ${error.message}`);
      }
    }
  };
}
