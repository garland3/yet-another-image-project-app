// Global variables
let projects = [];

// DOM Elements
document.addEventListener('DOMContentLoaded', () => {
  // Initialize common variables
  common.initCommonVariables();
  
  // Initialize the UI
  initUI();
  
  // Load projects
  loadProjects();
});

function initUI() {
  // Setup event listeners
  const newProjectBtn = document.getElementById('new-project-btn');
  const createProjectForm = document.getElementById('create-project-form');
  const closeModalBtn = document.getElementById('close-modal');
  const modal = document.getElementById('create-project-modal');
  
  console.log('Modal element:', modal);
  console.log('Modal classes on init:', modal.className);
  console.log('Modal display style on init:', modal.style.display);
  
  // New project button
  if (newProjectBtn) {
    newProjectBtn.addEventListener('click', () => {
      console.log('New project button clicked');
      modal.classList.remove('hidden');
      modal.style.display = 'flex';
    });
  }
  
  // Close modal button
  if (closeModalBtn) {
    closeModalBtn.addEventListener('click', () => {
      console.log('Close modal button clicked');
      modal.classList.add('hidden');
      modal.style.display = 'none';
    });
  }
  
  // Close modal when clicking outside
  window.addEventListener('click', (e) => {
    if (e.target === modal) {
      console.log('Clicked outside modal');
      modal.classList.add('hidden');
      modal.style.display = 'none';
    }
  });
  
  // Create project form submission
  if (createProjectForm) {
    createProjectForm.addEventListener('submit', (e) => {
      e.preventDefault();
      createProject();
    });
  }
}

async function loadProjects() {
  try {
    showLoader('projects-container');
    
    projects = await common.fetchWithErrorHandling('/projects/');
    
    // Display projects
    displayProjects(projects);
    
  } catch (error) {
    console.error('Error loading projects:', error);
    showError('Failed to load projects. Please try again later.');
  } finally {
    hideLoader('projects-container');
  }
}

function displayProjects(projects) {
  const projectsContainer = document.getElementById('projects-container');
  
  if (!projectsContainer) return;
  
  // Clear existing content
  projectsContainer.innerHTML = '';
  
  if (projects.length === 0) {
    projectsContainer.innerHTML = '<p>No projects found. Create a new project to get started.</p>';
    return;
  }
  
  // Create project cards
  const projectGrid = document.createElement('div');
  projectGrid.className = 'grid project-list';
  
  projects.forEach(project => {
    const projectCard = createProjectCard(project);
    projectGrid.appendChild(projectCard);
  });
  
  projectsContainer.appendChild(projectGrid);
}

function createProjectCard(project) {
  const card = document.createElement('div');
  card.className = 'card';
  
  const cardHeader = document.createElement('div');
  cardHeader.className = 'card-header';
  
  const title = document.createElement('h3');
  title.textContent = project.name;
  
  const date = document.createElement('small');
  date.textContent = new Date(project.created_at).toLocaleDateString();
  
  cardHeader.appendChild(title);
  cardHeader.appendChild(date);
  
  const cardContent = document.createElement('div');
  cardContent.className = 'card-content';
  
  const description = document.createElement('p');
  description.textContent = project.description || 'No description provided.';
  
  cardContent.appendChild(description);
  
  const cardFooter = document.createElement('div');
  cardFooter.className = 'card-footer';
  
  const viewBtn = document.createElement('a');
  viewBtn.href = `/ui/project?id=${project.id}`;
  viewBtn.className = 'btn';
  viewBtn.textContent = 'View Project';
  
  cardFooter.appendChild(viewBtn);
  
  card.appendChild(cardHeader);
  card.appendChild(cardContent);
  card.appendChild(cardFooter);
  
  return card;
}

async function createProject() {
  const nameInput = document.getElementById('project-name');
  const descriptionInput = document.getElementById('project-description');
  const groupInput = document.getElementById('project-group');
  const modal = document.getElementById('create-project-modal');
  
  if (!nameInput || !groupInput) return;
  
  const name = nameInput.value.trim();
  const description = descriptionInput ? descriptionInput.value.trim() : '';
  const meta_group_id = groupInput.value.trim();
  
  if (!name) {
    showError('Project name is required.');
    return;
  }
  
  if (!meta_group_id) {
    showError('Group ID is required.');
    return;
  }
  
  try {
    showLoader('modal-body');
    
    const newProject = await common.fetchWithErrorHandling('/projects/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name,
        description,
        meta_group_id
      })
    });
    
    // Add new project to the list and refresh display
    projects.push(newProject);
    displayProjects(projects);
    
    // Reset form and close modal
    nameInput.value = '';
    if (descriptionInput) descriptionInput.value = '';
    groupInput.value = '';
    modal.classList.add('hidden');
    modal.style.display = 'none';
    
    showSuccess('Project created successfully!');
    
  } catch (error) {
    console.error('Error creating project:', error);
    showError(`Failed to create project: ${error.message}`);
  } finally {
    hideLoader('modal-body');
  }
}

// Use common utility functions
const showLoader = common.showLoader;
const hideLoader = common.hideLoader;
const showError = common.showError;
const showSuccess = common.showSuccess;
