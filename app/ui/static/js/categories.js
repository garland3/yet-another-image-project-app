/**
 * Categories Manager
 * Handles CRUD operations for categories and assigning categories to images
 */
function categoriesManager() {
  return {
    allCategories: [],
    assignedCategories: [],
    availableCategories: [],
    selectedCategoryId: '',
    editingCategory: null,
    showAddCategoryForm: false,
    newCategory: {
      name: '',
      description: ''
    },
    canManageCategories: true, // In a real app, this would be based on user permissions
    
    init() {
      this.loadAllCategories();
      this.loadAssignedCategories();
    },
    
    async loadAllCategories() {
      try {
        const response = await fetch('/categories');
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        this.allCategories = await response.json();
        this.updateAvailableCategories();
      } catch (error) {
        console.error('Error loading categories:', error);
        showError('Failed to load categories. Please try again later.');
      }
    },
    
    async loadAssignedCategories() {
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId) return;
        
        const response = await fetch(`/images/${imageId}/categories`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        this.assignedCategories = await response.json();
        this.updateAvailableCategories();
      } catch (error) {
        console.error('Error loading assigned categories:', error);
        showError('Failed to load assigned categories. Please try again later.');
      }
    },
    
    updateAvailableCategories() {
      // Filter out categories that are already assigned
      const assignedIds = this.assignedCategories.map(cat => cat.id);
      this.availableCategories = this.allCategories.filter(cat => !assignedIds.includes(cat.id));
    },
    
    async addCategory() {
      try {
        if (!this.selectedCategoryId) return;
        
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId) return;
        
        const response = await fetch(`/images/${imageId}/categories/${this.selectedCategoryId}`, {
          method: 'POST'
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Find the category in the available categories
        const category = this.availableCategories.find(cat => cat.id === this.selectedCategoryId);
        
        if (category) {
          // Add to assigned categories
          this.assignedCategories.push(category);
          
          // Update available categories
          this.updateAvailableCategories();
          
          // Reset selected category
          this.selectedCategoryId = '';
          
          showSuccess('Category assigned successfully!');
        }
      } catch (error) {
        console.error('Error assigning category:', error);
        showError(`Failed to assign category: ${error.message}`);
      }
    },
    
    async removeCategory(categoryId) {
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId) return;
        
        const response = await fetch(`/images/${imageId}/categories/${categoryId}`, {
          method: 'DELETE'
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Remove from assigned categories
        this.assignedCategories = this.assignedCategories.filter(cat => cat.id !== categoryId);
        
        // Update available categories
        this.updateAvailableCategories();
        
        showSuccess('Category removed successfully!');
      } catch (error) {
        console.error('Error removing category:', error);
        showError(`Failed to remove category: ${error.message}`);
      }
    },
    
    async createCategory() {
      try {
        if (!this.newCategory.name.trim()) {
          showError('Category name is required.');
          return;
        }
        
        const response = await fetch('/categories', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            name: this.newCategory.name,
            description: this.newCategory.description
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }
        
        const newCategory = await response.json();
        
        // Add to all categories
        this.allCategories.push(newCategory);
        
        // Update available categories
        this.updateAvailableCategories();
        
        // Reset form
        this.newCategory = { name: '', description: '' };
        this.showAddCategoryForm = false;
        
        showSuccess('Category created successfully!');
      } catch (error) {
        console.error('Error creating category:', error);
        showError(`Failed to create category: ${error.message}`);
      }
    },
    
    editCategory(category) {
      this.editingCategory = { ...category };
    },
    
    cancelEdit() {
      this.editingCategory = null;
    },
    
    async updateCategory() {
      try {
        if (!this.editingCategory || !this.editingCategory.name.trim()) {
          showError('Category name is required.');
          return;
        }
        
        const response = await fetch(`/categories/${this.editingCategory.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            name: this.editingCategory.name,
            description: this.editingCategory.description
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }
        
        const updatedCategory = await response.json();
        
        // Update in all categories
        const allIndex = this.allCategories.findIndex(cat => cat.id === updatedCategory.id);
        if (allIndex !== -1) {
          this.allCategories[allIndex] = updatedCategory;
        }
        
        // Update in assigned categories if present
        const assignedIndex = this.assignedCategories.findIndex(cat => cat.id === updatedCategory.id);
        if (assignedIndex !== -1) {
          this.assignedCategories[assignedIndex] = updatedCategory;
        }
        
        // Update available categories
        this.updateAvailableCategories();
        
        this.editingCategory = null;
        
        showSuccess('Category updated successfully!');
      } catch (error) {
        console.error('Error updating category:', error);
        showError(`Failed to update category: ${error.message}`);
      }
    },
    
    async deleteCategory(categoryId) {
      if (!confirm('Are you sure you want to delete this category? This will remove it from all images.')) return;
      
      try {
        const response = await fetch(`/categories/${categoryId}`, {
          method: 'DELETE'
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Remove from all categories
        this.allCategories = this.allCategories.filter(cat => cat.id !== categoryId);
        
        // Remove from assigned categories if present
        this.assignedCategories = this.assignedCategories.filter(cat => cat.id !== categoryId);
        
        // Update available categories
        this.updateAvailableCategories();
        
        // If we were editing this category, cancel the edit
        if (this.editingCategory && this.editingCategory.id === categoryId) {
          this.editingCategory = null;
        }
        
        showSuccess('Category deleted successfully!');
      } catch (error) {
        console.error('Error deleting category:', error);
        showError(`Failed to delete category: ${error.message}`);
      }
    }
  };
}
