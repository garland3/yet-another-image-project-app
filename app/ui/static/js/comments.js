// Global variables
// Check if imageId is already defined (by view.js) before declaring it
if (typeof imageId === 'undefined') {
    var imageId = null; // Use var instead of let to avoid redeclaration errors
}
let comments = [];

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Get image ID from URL if available
    const urlParams = new URLSearchParams(window.location.search);
    imageId = urlParams.get('id');
    
    // Initialize event listeners
    initEventListeners();
    
    // If we have an image ID, load the comments for that image
    if (imageId) {
        loadCommentsForImage(imageId);
    }
});

// Initialize event listeners
function initEventListeners() {
    // Add comment form submission
    const addCommentForm = document.getElementById('add-comment-form');
    if (addCommentForm) {
        addCommentForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const commentText = document.getElementById('comment-text').value;
            
            if (commentText.trim() === '') {
                showError('Comment text cannot be empty');
                return;
            }
            
            createComment(commentText);
        });
    }
}

// Load comments for an image
async function loadCommentsForImage(imageId) {
    try {
        showLoader('comments-container');
        
        const response = await fetch(`/images/${imageId}/comments`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        comments = await response.json();
        
        // Display the comments
        displayComments(comments);
        
    } catch (error) {
        console.error('Error loading comments:', error);
        showError('Failed to load comments. Please try again later.');
    } finally {
        hideLoader('comments-container');
    }
}

// Display comments in the UI
function displayComments(comments) {
    const commentsContainer = document.getElementById('comments-container');
    if (!commentsContainer) return;
    
    // Clear existing content
    commentsContainer.innerHTML = '';
    
    if (!comments || comments.length === 0) {
        commentsContainer.innerHTML = '<p>No comments for this image. Add a comment to get started.</p>';
        return;
    }
    
    // Create a list of comments
    const commentsList = document.createElement('ul');
    commentsList.className = 'comments-list';
    
    comments.forEach(comment => {
        const commentItem = document.createElement('li');
        commentItem.className = 'comment-item';
        
        const commentHeader = document.createElement('div');
        commentHeader.className = 'comment-header';
        
        const authorName = document.createElement('span');
        authorName.className = 'comment-author';
        authorName.textContent = comment.author ? comment.author.email : 'Unknown user';
        
        const commentDate = document.createElement('span');
        commentDate.className = 'comment-date';
        commentDate.textContent = formatDate(comment.created_at);
        
        commentHeader.appendChild(authorName);
        commentHeader.appendChild(commentDate);
        
        const commentContent = document.createElement('div');
        commentContent.className = 'comment-content';
        commentContent.textContent = comment.text;
        
        const commentActions = document.createElement('div');
        commentActions.className = 'comment-actions';
        
        const editButton = document.createElement('button');
        editButton.className = 'btn btn-small';
        editButton.textContent = 'Edit';
        editButton.addEventListener('click', () => {
            // Populate the edit form
            document.getElementById('edit-comment-id').value = comment.id;
            document.getElementById('edit-comment-text').value = comment.text;
            
            // Show the edit form
            document.getElementById('edit-comment-modal').style.display = 'block';
        });
        
        const deleteButton = document.createElement('button');
        deleteButton.className = 'btn btn-small btn-danger';
        deleteButton.textContent = 'Delete';
        deleteButton.addEventListener('click', () => {
            if (confirm('Are you sure you want to delete this comment?')) {
                deleteComment(comment.id);
            }
        });
        
        commentActions.appendChild(editButton);
        commentActions.appendChild(deleteButton);
        
        commentItem.appendChild(commentHeader);
        commentItem.appendChild(commentContent);
        commentItem.appendChild(commentActions);
        
        commentsList.appendChild(commentItem);
    });
    
    commentsContainer.appendChild(commentsList);
}

// Create a new comment
async function createComment(text) {
    try {
        showLoader('add-comment-form');
        
        const response = await fetch(`/images/${imageId}/comments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
            }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const newComment = await response.json();
        
        // Add the new comment to the list
        comments.push(newComment);
        
        // Update the UI
        displayComments(comments);
        
        // Reset the form
        document.getElementById('comment-text').value = '';
        
        showSuccess('Comment added successfully!');
        
    } catch (error) {
        console.error('Error creating comment:', error);
        showError('Failed to add comment. Please try again later.');
    } finally {
        hideLoader('add-comment-form');
    }
}

// Update an existing comment
async function updateComment(id, text) {
    try {
        showLoader('edit-comment-form');
        
        const response = await fetch(`/comments/${id}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
            }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const updatedComment = await response.json();
        
        // Update the comment in the list
        const index = comments.findIndex(comment => comment.id === id);
        if (index !== -1) {
            comments[index] = updatedComment;
        }
        
        // Update the UI
        displayComments(comments);
        
        // Hide the edit form
        document.getElementById('edit-comment-modal').style.display = 'none';
        
        showSuccess('Comment updated successfully!');
        
    } catch (error) {
        console.error('Error updating comment:', error);
        showError('Failed to update comment. Please try again later.');
    } finally {
        hideLoader('edit-comment-form');
    }
}

// Delete a comment
async function deleteComment(id) {
    try {
        showLoader('comments-container');
        
        const response = await fetch(`/comments/${id}`, {
            method: 'DELETE',
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Remove the comment from the list
        comments = comments.filter(comment => comment.id !== id);
        
        // Update the UI
        displayComments(comments);
        
        showSuccess('Comment deleted successfully!');
        
    } catch (error) {
        console.error('Error deleting comment:', error);
        showError('Failed to delete comment. Please try again later.');
    } finally {
        hideLoader('comments-container');
    }
}

// Format date for display
function formatDate(dateString) {
    if (!dateString) return 'Unknown date';
    
    const date = new Date(dateString);
    return date.toLocaleString();
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
