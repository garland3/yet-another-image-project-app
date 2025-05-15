import React, { useState, useEffect, lazy, Suspense, memo, useRef, useCallback } from 'react';
import { Routes, Route, useNavigate, Link } from 'react-router-dom';
import './App.css';
import Toast from './components/Toast';

// Lazy load components
const Project = lazy(() => import('./Project'));
const ImageView = lazy(() => import('./ImageView'));

// Debug counter to track renders
let renderCount = 0;

// Create a separate component for the modal form
const CreateProjectModal = memo(function CreateProjectModal({ onClose, onSubmit, currentUser }) {
  console.log("Modal render count:", ++renderCount);
  
  // Use refs for uncontrolled inputs
  const nameInputRef = useRef(null);
  const descriptionInputRef = useRef(null);
  const groupIdInputRef = useRef(null);
  
  // Track focus state for debugging
  const [focusState, setFocusState] = useState('none');
  const [availableGroups, setAvailableGroups] = useState([]);
  const [loadingGroups, setLoadingGroups] = useState(true);
  const [groupError, setGroupError] = useState(null);
  
  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    console.log("Form submitted");
    
    // Get values directly from refs
    const newProject = {
      name: nameInputRef.current.value,
      description: descriptionInputRef.current.value,
      meta_group_id: groupIdInputRef.current.value
    };
    
    onSubmit(newProject);
  };
  
  // Debug focus events
  const handleFocus = (fieldName) => {
    console.log(`Focus on: ${fieldName}`);
    setFocusState(fieldName);
  };
  
  const handleBlur = (fieldName) => {
    console.log(`Blur from: ${fieldName}`);
    if (focusState === fieldName) {
      setFocusState('none');
    }
  };
  
  // Fetch available groups when component mounts
  useEffect(() => {
    console.log("Modal component mounted");
    
    // Focus the name input when modal opens
    if (nameInputRef.current) {
      nameInputRef.current.focus();
    }
    
    // If we have a current user, try to get their groups
    if (currentUser && currentUser.groups) {
      setAvailableGroups(currentUser.groups);
      setLoadingGroups(false);
    } else {
      // Fetch available groups from the API
      fetch('/api/users/me/groups')
        .then(response => {
          if (!response.ok) {
            if (response.status === 401) {
              // If unauthorized, just use some default groups from the mock data
              setAvailableGroups(['admin', 'project1', 'admin-group', 'data-scientists', 'project-alpha-group']);
              return null;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          if (data) {
            setAvailableGroups(data);
          }
          setLoadingGroups(false);
        })
        .catch(err => {
          console.error("Failed to fetch available groups:", err);
          setGroupError(err.message);
          setLoadingGroups(false);
        });
    }
    
    return () => {
      console.log("Modal component unmounted");
    };
  }, [currentUser]);
  
  return (
    <div className="modal">
      <div className="modal-content">
        <div className="modal-header">
          <h3>Create New Project</h3>
          <span className="close" onClick={onClose}>&times;</span>
        </div>
        <div className="modal-body">
          <form id="create-project-form" onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="name">Project Name (Current focus: {focusState})</label>
              <input 
                type="text" 
                id="name" 
                ref={nameInputRef}
                onFocus={() => handleFocus('name')}
                onBlur={() => handleBlur('name')}
                required 
              />
            </div>
            <div className="form-group">
              <label htmlFor="description">Description (Optional)</label>
              <textarea 
                id="description" 
                rows="3"
                ref={descriptionInputRef}
                onFocus={() => handleFocus('description')}
                onBlur={() => handleBlur('description')}
              ></textarea>
            </div>
            <div className="form-group">
              <label htmlFor="meta_group_id">Group ID</label>
              {loadingGroups ? (
                <div>Loading available groups...</div>
              ) : groupError ? (
                <div className="error-text">{groupError}</div>
              ) : (
                <>
                  <select 
                    id="meta_group_id" 
                    ref={groupIdInputRef}
                    onFocus={() => handleFocus('groupId')}
                    onBlur={() => handleBlur('groupId')}
                    required
                    className="form-control"
                  >
                    <option value="">-- Select a group --</option>
                    {availableGroups.map(group => (
                      <option key={group} value={group}>{group}</option>
                    ))}
                  </select>
                  <small className="form-text text-muted">
                    Select a group you have access to
                  </small>
                </>
              )}
            </div>
            <div className="modal-footer">
              <button 
                type="button" 
                className="btn btn-secondary"
                onClick={onClose}
              >
                Cancel
              </button>
              <button type="submit" className="btn btn-success">
                Create Project
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
});

// Memoized ProjectItem component to prevent unnecessary re-renders
const ProjectItem = memo(function ProjectItem({ project }) {
  return (
    <li style={{ cursor: 'pointer' }}>
      <Link 
        to={`/project/${project.id}`} 
        style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}
      >
        <h3>{project.name}</h3>
        <p>{project.description || 'No description'}</p>
        <small>Group ID: {project.meta_group_id}</small>
      </Link>
    </li>
  );
});

function App() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    meta_group_id: ''
  });
  
  // Function to show a toast notification
  const showToast = (message, type = 'error') => {
    setToast({ message, type });
  };
  
  // Function to hide the toast
  const hideToast = () => {
    setToast(null);
  };

  useEffect(() => {
    // Fetch the current user
    fetch('/api/users/me')
      .then(response => {
        if (!response.ok) {
          // If we get a 401, it's expected when authentication is disabled
          if (response.status === 401) {
            console.log("Authentication is disabled or user is not logged in");
            return null;
          }
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(userData => {
        if (userData) {
          setCurrentUser(userData);
        }
      })
      .catch(err => {
        console.error("Failed to fetch current user:", err);
      });

    // Fetch projects from the API
    fetch('/api/projects/')
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        setProjects(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch projects:", err);
        showToast(`Failed to fetch projects: ${err.message}`, 'error');
        setLoading(false);
      });
  }, []); // Empty dependency array means this effect runs once on mount

  // Log component renders for debugging
  console.log("App render count:", ++renderCount);
  
  // Handle project creation form submission
  const handleCreateProject = useCallback((projectData) => {
    console.log("Creating project:", projectData);
    setLoading(true);
    
    fetch('/api/projects/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(projectData),
    })
      .then(response => {
        if (!response.ok) {
          // Parse the error response
          return response.json().then(errorData => {
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
          }).catch(jsonError => {
            // If parsing JSON fails, use a generic error message
            throw new Error(`HTTP error! status: ${response.status}`);
          });
        }
        return response.json();
      })
      .then(data => {
        console.log("Project created successfully:", data);
        // Add the new project to the projects list
        setProjects(prev => [...prev, data]);
        // Close modal
        setShowModal(false);
        setLoading(false);
        // Show success toast
        showToast(`Project "${data.name}" created successfully!`, 'success');
      })
      .catch(err => {
        console.error("Failed to create project:", err);
        showToast(err.message, 'error');
        setLoading(false);
      });
  }, []);


  const HomePage = () => (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <h1>Image Manager</h1>
          {currentUser && (
            <div className="user-info">
              <span>Logged in as: {currentUser.email}</span>
            </div>
          )}
        </div>
        <button 
          className="btn" 
          onClick={() => setShowModal(true)}
        >
          New Project
        </button>
      </header>
      <div className="container">
        {/* Toast notification */}
        {toast && (
          <Toast 
            message={toast.message}
            type={toast.type}
            onClose={hideToast}
            duration={5000}
          />
        )}
        
        <div className="card">
          <div className="card-header">
            <h2>Projects</h2>
          </div>
          <div id="projects-container" className="card-content">
            {loading && <p>Loading projects...</p>}
            {!loading && projects.length === 0 && <p>No projects found.</p>}
            {!loading && projects.length > 0 && (
              <ul>
                {projects.map(project => (
                  <ProjectItem key={project.id} project={project} />
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Create Project Modal - Now using a separate component */}
      {showModal && (
        <CreateProjectModal 
          onClose={() => setShowModal(false)} 
          onSubmit={handleCreateProject}
          currentUser={currentUser}
        />
      )}
    </div>
  );

  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route 
        path="/project/:id" 
        element={
          <Suspense fallback={<div className="loading-container">Loading project...</div>}>
            <Project />
          </Suspense>
        } 
      />
      <Route 
        path="/view/:imageId" 
        element={
          <Suspense fallback={<div className="loading-container">Loading image...</div>}>
            <ImageView />
          </Suspense>
        } 
      />
    </Routes>
  );
}

export default App;
