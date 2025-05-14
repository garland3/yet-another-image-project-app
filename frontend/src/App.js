import React, { useState, useEffect, lazy, Suspense, memo } from 'react';
import { Routes, Route, useNavigate, Link } from 'react-router-dom';
import './App.css';

// Lazy load components
const Project = lazy(() => import('./Project'));
const ImageView = lazy(() => import('./ImageView'));

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
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    meta_group_id: ''
  });

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
    fetch('/api/projects')
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
        setError(err.message);
        setLoading(false);
      });
  }, []); // Empty dependency array means this effect runs once on mount

  const handleInputChange = (e) => {
    const { id, value } = e.target;
    setNewProject(prev => ({
      ...prev,
      [id]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setLoading(true);
    
    fetch('/api/projects', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(newProject),
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        // Add the new project to the projects list
        setProjects(prev => [...prev, data]);
        // Reset form and close modal
        setNewProject({ name: '', description: '', meta_group_id: '' });
        setShowModal(false);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to create project:", err);
        setError(err.message);
        setLoading(false);
      });
  };

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
        <div id="alerts-container">
          {error && <div className="alert alert-error">Error: {error}</div>}
        </div>
        
        <div className="card">
          <div className="card-header">
            <h2>Projects</h2>
          </div>
          <div id="projects-container" className="card-content">
            {loading && <p>Loading projects...</p>}
            {!loading && !error && projects.length === 0 && <p>No projects found.</p>}
            {!loading && !error && projects.length > 0 && (
              <ul>
                {projects.map(project => (
                  <ProjectItem key={project.id} project={project} />
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Create Project Modal */}
      {showModal && (
        <div className="modal">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Create New Project</h3>
              <span className="close" onClick={() => setShowModal(false)}>&times;</span>
            </div>
            <div className="modal-body">
              <form id="create-project-form" onSubmit={handleSubmit}>
                <div className="form-group">
                  <label htmlFor="name">Project Name</label>
                  <input 
                    type="text" 
                    id="name" 
                    value={newProject.name}
                    onChange={handleInputChange}
                    required 
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="description">Description (Optional)</label>
                  <textarea 
                    id="description" 
                    rows="3"
                    value={newProject.description}
                    onChange={handleInputChange}
                  ></textarea>
                </div>
                <div className="form-group">
                  <label htmlFor="meta_group_id">Group ID</label>
                  <input 
                    type="text" 
                    id="meta_group_id" 
                    value={newProject.meta_group_id}
                    onChange={handleInputChange}
                    required 
                  />
                </div>
                <div className="modal-footer">
                  <button 
                    type="button" 
                    className="btn btn-secondary"
                    onClick={() => setShowModal(false)}
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
