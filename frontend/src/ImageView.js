import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import './App.css';

// Import components
import ImageDisplay from './components/ImageDisplay';
import ImageMetadata from './components/ImageMetadata';
import ImageClassifications from './components/ImageClassifications';
import CompactImageClassifications from './components/CompactImageClassifications';
import ImageComments from './components/ImageComments';
import ImageDeletionControls from './components/ImageDeletionControls';

function ImageView() {
  const { imageId } = useParams();
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get('project');
  const navigate = useNavigate();

  // State variables
  const [image, setImage] = useState(null);
  const [projectImages, setProjectImages] = useState([]);
  const [currentImageIndex, setCurrentImageIndex] = useState(-1);
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);

  // Load image data
  const loadImageData = useCallback(async () => {
    try {
      setLoading(true);
      
      // Try to fetch image metadata directly first
      let response = await fetch(`/api/images/${imageId}`);
      
      if (!response.ok) {
        // If direct fetch fails (likely because image is deleted), 
        // try to find it through the project endpoint with deleted images included
        console.log('Direct image fetch failed, trying project endpoint with deleted images...');
        const projectResponse = await fetch(`/api/projects/${projectId}/images?include_deleted=true`);
        
        if (!projectResponse.ok) {
          throw new Error(`Failed to fetch project images: ${projectResponse.status}`);
        }
        
        const projectImages = await projectResponse.json();
        const imageData = projectImages.find(img => img.id === imageId);
        
        if (!imageData) {
          throw new Error('Image not found in project');
        }
        
        setImage(imageData);
        // Update document title
        document.title = `${imageData.filename || 'Image'} - Image Manager`;
      } else {
        const imageData = await response.json();
        setImage(imageData);
        // Update document title
        document.title = `${imageData.filename || 'Image'} - Image Manager`;
      }
      
    } catch (error) {
      console.error('Error loading image data:', error);
      setError('Failed to load image. Please try again later.');
    } finally {
      setLoading(false);
    }
  }, [imageId, projectId]);

  // Load project images for navigation
  const loadProjectImages = useCallback(async () => {
    try {
      console.log('Fetching images for project:', projectId);
      const response = await fetch(`/api/projects/${projectId}/images?include_deleted=true`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      const images = await response.json();
      
      if (!Array.isArray(images)) {
        console.error('Server response is not an array:', images);
        throw new Error('Invalid server response: expected an array of images');
      }
      
      // Sort images by date (newest first) to match the gallery default sorting
      // Use spread operator to avoid mutating the original array
      const sortedImages = [...images].sort((a, b) => {
        return new Date(b.created_at || 0) - new Date(a.created_at || 0);
      });

      setProjectImages(sortedImages);

      // Find the index of the current image in the sorted array
      const index = sortedImages.findIndex(img => img.id === imageId);
      setCurrentImageIndex(index);
      
    } catch (error) {
      console.error('Error loading project images:', error);
      setError('Failed to load project images for navigation. Please try again later.');
    }
  }, [projectId, imageId]);

  // Load classes for the project
  const loadClasses = useCallback(async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}/classes`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      const classesData = await response.json();
      setClasses(classesData);
      
    } catch (error) {
      console.error('Error loading classes:', error);
      setError('Failed to load classes. Please try again later.');
    }
  }, [projectId]);

  // Initialize data on component mount
  useEffect(() => {
    if (!imageId || !projectId) {
      setError('Image ID or Project ID is missing.');
      return;
    }
    
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
    
    loadImageData();
    loadProjectImages();
    loadClasses();
  }, [imageId, projectId, loadImageData, loadProjectImages, loadClasses]);

  // Navigate to previous image with transition
  const navigateToPreviousImage = useCallback(() => {
    if (currentImageIndex > 0) {
      setIsTransitioning(true);
      setTimeout(() => {
        const prevImage = projectImages[currentImageIndex - 1];
        navigate(`/view/${prevImage.id}?project=${projectId}`);
      }, 300);
    }
  }, [currentImageIndex, projectImages, navigate, projectId]);

  // Navigate to next image with transition
  const navigateToNextImage = useCallback(() => {
    if (currentImageIndex < projectImages.length - 1) {
      setIsTransitioning(true);
      setTimeout(() => {
        const nextImage = projectImages[currentImageIndex + 1];
        navigate(`/view/${nextImage.id}?project=${projectId}`);
      }, 300);
    }
  }, [currentImageIndex, projectImages, navigate, projectId]);

  // Reset transition state when image changes
  useEffect(() => {
    setIsTransitioning(false);
  }, [imageId]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowLeft') {
        navigateToPreviousImage();
      } else if (e.key === 'ArrowRight') {
        navigateToNextImage();
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [currentImageIndex, projectImages.length, navigateToNextImage, navigateToPreviousImage]);

  return (
    <div className="App" style={{ maxWidth: '100%', padding: '0' }}>
      <header className="view-header-compact">
        <div className="view-header-content">
          <button
            className="btn btn-secondary btn-small"
            onClick={() => navigate(`/project/${projectId}`)}
          >
            ← Back
          </button>
          <span className="view-filename">{image ? image.filename : 'Loading...'}</span>
          {currentUser && (
            <span className="view-user-info">{currentUser.email}</span>
          )}
        </div>
      </header>

      <div className="container" style={{ maxWidth: '100%', padding: 'var(--space-4)' }}>
        {error && (
          <div className="alert alert-error">
            {error}
            <button 
              className="close-alert"
              onClick={() => setError(null)}
            >
              &times;
            </button>
          </div>
        )}
        
        <div className="image-view-container">
          {/* Compact classification buttons above image */}
          <CompactImageClassifications
            imageId={imageId}
            classes={classes}
            loading={loading}
            setLoading={setLoading}
            setError={setError}
          />

          <ImageDisplay
            imageId={imageId}
            image={image}
            isTransitioning={isTransitioning}
            projectId={projectId}
            setImage={setImage}
            refreshProjectImages={loadProjectImages}
            navigateToPreviousImage={navigateToPreviousImage}
            navigateToNextImage={navigateToNextImage}
            currentImageIndex={currentImageIndex}
            projectImages={projectImages}
          />
          
          <ImageComments 
            imageId={imageId} 
            loading={loading} 
            setLoading={setLoading} 
            setError={setError} 
          />
          
          <ImageMetadata 
            imageId={imageId} 
            image={image} 
            setImage={setImage} 
            loading={loading} 
            setLoading={setLoading} 
            setError={setError} 
          />

          <ImageDeletionControls 
            projectId={projectId} 
            image={image} 
            setImage={setImage} 
            refreshProjectImages={loadProjectImages} 
          />
          
          {/* Original classifications component for reference/additional details */}
          <ImageClassifications 
            imageId={imageId} 
            classes={classes} 
            loading={loading} 
            setLoading={setLoading} 
            setError={setError} 
          />
        </div>
      </div>
    </div>
  );
}

export default ImageView;
