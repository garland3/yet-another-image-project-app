// Global variables
let classes = [];
let imageClassifications = [];

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize common variables
    const { projectId: urlProjectId, imageId: urlImageId, isProjectPage, isViewPage } = common.initCommonVariables();
    
    // Set global variables from common
    projectId = window.common.projectId;
    imageId = window.common.imageId;
    
    // Initialize event listeners
    initEventListeners();
    
    // If we have a project ID, load the classes for that project
    if (projectId) {
        loadClassesForProject(projectId);
    }
    
    // If we have an image ID and we're on the view page, load the classifications for that image
    if (imageId && isViewPage) {
        loadClassificationsForImage(imageId);
    }
});

// Initialize event listeners
function initEventListeners() {
    // Add class form submission
    const addClassForm = document.getElementById('add-class-form');
    if (addClassForm) {
        // Remove any existing event listeners to prevent duplicates
        const newAddClassForm = addClassForm.cloneNode(true);
        addClassForm.parentNode.replaceChild(newAddClassForm, addClassForm);
        
        newAddClassForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const className = document.getElementById('class-name').value;
            const classDescription = document.getElementById('class-description').value;
            
            if (className.trim() === '') {
                showError('Class name cannot be empty');
                return;
            }
            
            createImageClass(className, classDescription);
        });
    }
    
    // Classify image form submission
    const classifyImageForm = document.getElementById('classify-image-form');
    if (classifyImageForm) {
        // Remove any existing event listeners to prevent duplicates
        const newClassifyImageForm = classifyImageForm.cloneNode(true);
        classifyImageForm.parentNode.replaceChild(newClassifyImageForm, classifyImageForm);
        
        newClassifyImageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const classId = document.getElementById('selected-class-id').value;
            
            if (!classId) {
                showError('Please select a class');
                return;
            }
            
            classifyImage(classId);
        });
    }
}

// Load classes for a project
async function loadClassesForProject(projectId) {
    try {
        showLoader('classes-container');
        
        classes = await common.fetchWithErrorHandling(`/projects/${projectId}/classes`);
        
        // Display the classes
        displayClasses(classes);
        
        // Update the class select dropdown if it exists
        updateClassSelect(classes);
        
    } catch (error) {
        console.error('Error loading classes:', error);
        showError('Failed to load classes. Please try again later.');
    } finally {
        hideLoader('classes-container');
    }
}

// Display classes in the UI
function displayClasses(classes) {
    const classesContainer = document.getElementById('classes-container');
    if (!classesContainer) return;
    
    // Clear existing content
    classesContainer.innerHTML = '';
    
    if (!classes || classes.length === 0) {
        classesContainer.innerHTML = '<p>No classes defined for this project. Add a class to get started.</p>';
        return;
    }
    
    // Create a list of classes
    const classList = document.createElement('ul');
    classList.className = 'class-list';
    
    classes.forEach(cls => {
        const classItem = document.createElement('li');
        classItem.className = 'class-item';
        
        const classInfo = document.createElement('div');
        classInfo.className = 'class-info';
        
        const className = document.createElement('h4');
        className.textContent = cls.name;
        
        const classDescription = document.createElement('p');
        classDescription.textContent = cls.description || 'No description';
        
        classInfo.appendChild(className);
        classInfo.appendChild(classDescription);
        
        const classActions = document.createElement('div');
        classActions.className = 'class-actions';
        
        const editButton = document.createElement('button');
        editButton.className = 'btn btn-small';
        editButton.textContent = 'Edit';
        editButton.addEventListener('click', () => {
            // Populate the edit form
            document.getElementById('edit-class-id').value = cls.id;
            document.getElementById('edit-class-name').value = cls.name;
            document.getElementById('edit-class-description').value = cls.description || '';
            
            // Show the edit form
            document.getElementById('edit-class-modal').style.display = 'block';
        });
        
        const deleteButton = document.createElement('button');
        deleteButton.className = 'btn btn-small btn-danger';
        deleteButton.textContent = 'Delete';
        deleteButton.addEventListener('click', () => {
            if (confirm(`Are you sure you want to delete the class "${cls.name}"?`)) {
                deleteImageClass(cls.id);
            }
        });
        
        classActions.appendChild(editButton);
        classActions.appendChild(deleteButton);
        
        classItem.appendChild(classInfo);
        classItem.appendChild(classActions);
        
        classList.appendChild(classItem);
    });
    
    classesContainer.appendChild(classList);
}

// Update the class selection UI with buttons instead of dropdown
function updateClassSelect(classes) {
    const classButtonsContainer = document.getElementById('class-buttons-container');
    if (!classButtonsContainer) return;
    
    // Clear existing content
    classButtonsContainer.innerHTML = '';
    
    if (!classes || classes.length === 0) {
        classButtonsContainer.innerHTML = '<p>No classes available. Please add classes to the project first.</p>';
        return;
    }
    
    // Create a container for the buttons
    const buttonsContainer = document.createElement('div');
    buttonsContainer.className = 'class-buttons';
    
    // Add buttons for each class
    classes.forEach(cls => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn class-button';
        button.dataset.classId = cls.id;
        button.textContent = cls.name;
        
        // Add click event to select this class
        button.addEventListener('click', () => {
            // Remove selected class from all buttons
            document.querySelectorAll('.class-button').forEach(btn => {
                btn.classList.remove('selected');
            });
            
            // Add selected class to this button
            button.classList.add('selected');
            
            // Store the selected class ID
            document.getElementById('selected-class-id').value = cls.id;
        });
        
        buttonsContainer.appendChild(button);
    });
    
    classButtonsContainer.appendChild(buttonsContainer);
}

// Create a new image class
async function createImageClass(name, description) {
    try {
        showLoader('add-class-form');
        
        const newClass = await common.fetchWithErrorHandling(`/projects/${projectId}/classes`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                project_id: projectId,
                name: name,
                description: description,
            }),
        });
        
        // Add the new class to the list
        classes.push(newClass);
        
        // Update the UI
        displayClasses(classes);
        updateClassSelect(classes);
        
        // Reset the form
        document.getElementById('class-name').value = '';
        document.getElementById('class-description').value = '';
        
        showSuccess(`Class "${name}" created successfully!`);
        
    } catch (error) {
        console.error('Error creating class:', error);
        showError('Failed to create class. Please try again later.');
    } finally {
        hideLoader('add-class-form');
    }
}

// Update an existing image class
async function updateImageClass(id, name, description) {
    try {
        showLoader('edit-class-form');
        
        const updatedClass = await common.fetchWithErrorHandling(`/classes/${id}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                description: description,
            }),
        });
        
        // Update the class in the list
        const index = classes.findIndex(cls => cls.id === id);
        if (index !== -1) {
            classes[index] = updatedClass;
        }
        
        // Update the UI
        displayClasses(classes);
        updateClassSelect(classes);
        
        // Hide the edit form
        document.getElementById('edit-class-modal').style.display = 'none';
        
        showSuccess(`Class "${name}" updated successfully!`);
        
    } catch (error) {
        console.error('Error updating class:', error);
        showError('Failed to update class. Please try again later.');
    } finally {
        hideLoader('edit-class-form');
    }
}

// Delete an image class
async function deleteImageClass(id) {
    try {
        showLoader('classes-container');
        
        await common.fetchWithErrorHandling(`/classes/${id}`, {
            method: 'DELETE',
        });
        
        // Remove the class from the list
        classes = classes.filter(cls => cls.id !== id);
        
        // Update the UI
        displayClasses(classes);
        updateClassSelect(classes);
        
        showSuccess('Class deleted successfully!');
        
    } catch (error) {
        console.error('Error deleting class:', error);
        showError('Failed to delete class. Please try again later.');
    } finally {
        hideLoader('classes-container');
    }
}

// Load classifications for an image
async function loadClassificationsForImage(imageId) {
    try {
        showLoader('classifications-container');
        
        imageClassifications = await common.fetchWithErrorHandling(`/images/${imageId}/classifications`);
        
        // Display the classifications
        displayClassifications(imageClassifications);
        
    } catch (error) {
        console.error('Error loading classifications:', error);
        showError('Failed to load classifications. Please try again later.');
    } finally {
        hideLoader('classifications-container');
    }
}

// Display classifications in the UI
function displayClassifications(classifications) {
    const classificationsContainer = document.getElementById('classifications-container');
    if (!classificationsContainer) return;
    
    // Clear existing content
    classificationsContainer.innerHTML = '';
    
    if (!classifications || classifications.length === 0) {
        classificationsContainer.innerHTML = '<p>No classifications for this image. Add a classification to get started.</p>';
        return;
    }
    
    // Create a list of classifications
    const classificationsList = document.createElement('ul');
    classificationsList.className = 'classifications-list';
    
    classifications.forEach(classification => {
        const classificationItem = document.createElement('li');
        classificationItem.className = 'classification-item';
        
        const classificationInfo = document.createElement('div');
        classificationInfo.className = 'classification-info';
        
        const className = document.createElement('h4');
        className.textContent = classification.image_class ? classification.image_class.name : 'Unknown class';
        
        classificationInfo.appendChild(className);
        
        const classificationActions = document.createElement('div');
        classificationActions.className = 'classification-actions';
        
        const deleteButton = document.createElement('button');
        deleteButton.className = 'btn btn-small btn-danger';
        deleteButton.textContent = 'Remove';
        deleteButton.addEventListener('click', () => {
            if (confirm('Are you sure you want to remove this classification?')) {
                deleteClassification(classification.id);
            }
        });
        
        classificationActions.appendChild(deleteButton);
        
        classificationItem.appendChild(classificationInfo);
        classificationItem.appendChild(classificationActions);
        
        classificationsList.appendChild(classificationItem);
    });
    
    classificationsContainer.appendChild(classificationsList);
}

// Classify an image
async function classifyImage(classId) {
    try {
        // Check if imageId is available
        if (!imageId) {
            console.error('Image ID is missing');
            showError('Image ID is missing. Please try refreshing the page.');
            return;
        }
        
        showLoader('classify-image-form');
        
        console.log(`Classifying image ${imageId} with class ${classId}`);
        
        const newClassification = await common.fetchWithErrorHandling(`/images/${imageId}/classifications`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                image_id: imageId,
                class_id: classId,
            }),
        });
        
        // Add the new classification to the list
        imageClassifications.push(newClassification);
        
        // Update the UI
        displayClassifications(imageClassifications);
        
        // Reset the form by clearing the selected class
        document.getElementById('selected-class-id').value = '';
        
        // Remove selected class from all buttons
        document.querySelectorAll('.class-button').forEach(btn => {
            btn.classList.remove('selected');
        });
        
        showSuccess('Image classified successfully!');
        
    } catch (error) {
        console.error('Error classifying image:', error);
        showError('Failed to classify image. Please try again later.');
    } finally {
        hideLoader('classify-image-form');
    }
}

// Delete a classification
async function deleteClassification(id) {
    try {
        showLoader('classifications-container');
        
        await common.fetchWithErrorHandling(`/classifications/${id}`, {
            method: 'DELETE',
        });
        
        // Remove the classification from the list
        imageClassifications = imageClassifications.filter(classification => classification.id !== id);
        
        // Update the UI
        displayClassifications(imageClassifications);
        
        showSuccess('Classification removed successfully!');
        
    } catch (error) {
        console.error('Error removing classification:', error);
        showError('Failed to remove classification. Please try again later.');
    } finally {
        hideLoader('classifications-container');
    }
}

// Use common utility functions
const showLoader = common.showLoader;
const hideLoader = common.hideLoader;
const showError = common.showError;
const showSuccess = common.showSuccess;
