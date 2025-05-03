/**
 * Comments Manager
 * Handles CRUD operations for image comments
 */
function commentsManager() {
  return {
    comments: [],
    editingComment: null,
    newComment: {
      text: ''
    },
    currentUser: null, // Will be populated with the current user's email
    
    init() {
      this.loadComments();
      // In a real app, you would get the current user from a session or auth service
      // For now, we'll use the email from the query string or a default value
      const urlParams = new URLSearchParams(window.location.search);
      this.currentUser = urlParams.get('user') || 'current.user@example.com';
    },
    
    async loadComments() {
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId) return;
        
        const response = await fetch(`/images/${imageId}/comments`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        this.comments = await response.json();
        
        // Sort comments by creation date (newest first)
        this.comments.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      } catch (error) {
        console.error('Error loading comments:', error);
        showError('Failed to load comments. Please try again later.');
      }
    },
    
    async addComment() {
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId || !this.newComment.text.trim()) return;
        
        const response = await fetch(`/images/${imageId}/comments`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            text: this.newComment.text
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }
        
        const newComment = await response.json();
        
        // Add the new comment to the list and sort
        this.comments.unshift(newComment);
        
        // Reset form
        this.newComment.text = '';
        
        showSuccess('Comment added successfully!');
      } catch (error) {
        console.error('Error adding comment:', error);
        showError(`Failed to add comment: ${error.message}`);
      }
    },
    
    canEditComment(comment) {
      // In a real app, you would check if the current user is the author of the comment
      // For now, we'll just check if the user_id matches the current user
      return comment.user_id === this.currentUser;
    },
    
    editComment(comment) {
      this.editingComment = { ...comment };
    },
    
    cancelEdit() {
      this.editingComment = null;
    },
    
    async updateComment() {
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId || !this.editingComment) return;
        
        const response = await fetch(`/images/${imageId}/comments/${this.editingComment.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            text: this.editingComment.text
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }
        
        const updatedComment = await response.json();
        
        // Update the comment in the list
        const index = this.comments.findIndex(comment => comment.id === updatedComment.id);
        if (index !== -1) {
          this.comments[index] = updatedComment;
        }
        
        this.editingComment = null;
        
        showSuccess('Comment updated successfully!');
      } catch (error) {
        console.error('Error updating comment:', error);
        showError(`Failed to update comment: ${error.message}`);
      }
    },
    
    async deleteComment(id) {
      if (!confirm('Are you sure you want to delete this comment?')) return;
      
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId) return;
        
        const response = await fetch(`/images/${imageId}/comments/${id}`, {
          method: 'DELETE'
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Remove the comment from the list
        this.comments = this.comments.filter(comment => comment.id !== id);
        
        showSuccess('Comment deleted successfully!');
      } catch (error) {
        console.error('Error deleting comment:', error);
        showError(`Failed to delete comment: ${error.message}`);
      }
    },
    
    formatDate(dateString) {
      if (!dateString) return '';
      
      const date = new Date(dateString);
      
      // Check if the date is valid
      if (isNaN(date.getTime())) return 'Invalid date';
      
      // Format the date
      return date.toLocaleString();
    }
  };
}
