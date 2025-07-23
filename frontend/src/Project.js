import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './App.css';

// Import components
import ImageUploader from './components/ImageUploader';
import MetadataManager from './components/MetadataManager';
import ClassManager from './components/ClassManager';
import ImageGallery from './components/ImageGallery';

function Project() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [images, setImages] = useState([]);
  const [metadata, setMetadata] = useState({});
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);

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

    // Load project data, metadata, classes, and images
    const fetchProjectData = async () => {
      try {
        setLoading(true);
        
        // Fetch project details
        const projectResponse = await fetch(`/api/projects/${id}`);
        if (!projectResponse.ok) {
          throw new Error(`HTTP error! status: ${projectResponse.status}`);
        }
        const projectData = await projectResponse.json();
        setProject(projectData);
        
        // Fetch project metadata
        const metadataResponse = await fetch(`/api/projects/${id}/metadata-dict`);
        if (metadataResponse.ok) {
          const metadataData = await metadataResponse.json();
          setMetadata(metadataData);
        }
        
        // Fetch project classes
        const classesResponse = await fetch(`/api/projects/${id}/classes`);
        if (classesResponse.ok) {
          const classesData = await classesResponse.json();
          setClasses(classesData);
        }
        
        // Fetch project images
        console.log(`Fetching images for project ${id}...`);
        const imagesResponse = await fetch(`/api/projects/${id}/images`);
        if (imagesResponse.ok) {
          const imagesData = await imagesResponse.json();
          console.log(`Received ${imagesData.length} images for project ${id}`);
          console.log('Image data sample:', imagesData.length > 0 ? imagesData[0] : 'No images');
          setImages(imagesData);
        } else {
          console.error(`Failed to fetch images: ${imagesResponse.status} ${imagesResponse.statusText}`);
        }
        
        setLoading(false);
      } catch (err) {
        console.error("Failed to fetch project data:", err);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchProjectData();
  }, [id]);

  // Handle image upload completion
  const handleUploadComplete = (newImages) => {
    setImages(prevImages => [...prevImages, ...newImages]);
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <div className="header-title">
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', marginBottom: 'var(--space-2)' }}>
              <button 
                className="btn btn-secondary" 
                onClick={() => navigate('/')}
                style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}
              >
                &lt; Back to Dashboard
              </button>
              <div>
                <h1 style={{ margin: 0 }}>{project ? project.name : 'Loading project...'}</h1>
              </div>
            </div>
            <p style={{ margin: 0, color: 'var(--gray-300)', fontSize: '0.875rem' }}>
              {project ? (project.description || 'No description provided') : ''}
            </p>
            {currentUser && (
              <div className="user-info">
                <span>{currentUser.email}</span>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="container">
        {/* Breadcrumb Navigation */}
        <div className="nav-breadcrumb">
          <div className="breadcrumb">
            <div className="breadcrumb-item">
              <a href="/" onClick={(e) => { e.preventDefault(); navigate('/'); }}>
                Dashboard
              </a>
            </div>
            <span className="breadcrumb-separator">/</span>
            <div className="breadcrumb-item">
              <span>Projects</span>
            </div>
            <span className="breadcrumb-separator">/</span>
            <div className="breadcrumb-item">
              <span>{project ? project.name : 'Loading...'}</span>
            </div>
          </div>
        </div>

        {error && (
          <div className="alert alert-error">
            <strong>Error:</strong> {error}
          </div>
        )}
        
        {loading && (
          <div className="loading-container">
            <div className="spinner"></div>
            <div className="loading-text">Loading project data...</div>
          </div>
        )}
        
        {!loading && (
          <>
            <MetadataManager 
              projectId={id} 
              metadata={metadata} 
              setMetadata={setMetadata} 
              loading={loading} 
              setLoading={setLoading} 
              setError={setError} 
            />
            
            <ImageGallery 
              projectId={id} 
              images={images} 
              loading={loading} 
            />
            
            <ClassManager 
              projectId={id} 
              classes={classes} 
              setClasses={setClasses} 
              loading={loading} 
              setLoading={setLoading} 
              setError={setError} 
            />
            
            <ImageUploader 
              projectId={id} 
              onUploadComplete={handleUploadComplete} 
              loading={loading} 
              setLoading={setLoading} 
              setError={setError} 
            />
          </>
        )}
      </div>
    </div>
  );
}

export default Project;
