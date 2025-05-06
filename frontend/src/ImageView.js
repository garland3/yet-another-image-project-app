import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import './App.css';

// Import components
import ImageDisplay from './components/ImageDisplay';
import ImageMetadata from './components/ImageMetadata';
import ImageClassifications from './components/ImageClassifications';
import ImageComments from './components/ImageComments';

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

  // Load image data
  const loadImageData = useCallback(async () => {
    try {
      setLoading(true);
      
      // Fetch image metadata
      const response = await fetch(`/images/${imageId}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      const imageData = await response.json();
      setImage(imageData);
      
      // Update document title
      document.title = `${imageData.filename || 'Image'} - Image Manager`;
      
    } catch (error) {
      console.error('Error loading image data:', error);
      setError('Failed to load image. Please try again later.');
    } finally {
      setLoading(false);
    }
  }, [imageId]);

  // Load project images for navigation
  const loadProjectImages = useCallback(async () => {
    try {
      console.log('Fetching images for project:', projectId);
      const response = await fetch(`/projects/${projectId}/images/`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      const images = await response.json();
      
      if (!Array.isArray(images)) {
        console.error('Server response is not an array:', images);
        throw new Error('Invalid server response: expected an array of images');
      }
      
      setProjectImages(images);
      
      // Find the index of the current image
      const index = images.findIndex(img => img.id === imageId);
      setCurrentImageIndex(index);
      
    } catch (error) {
      console.error('Error loading project images:', error);
      setError('Failed to load project images for navigation. Please try again later.');
    }
  }, [projectId, imageId]);

  // Load classes for the project
  const loadClasses = useCallback(async () => {
    try {
      const response = await fetch(`/projects/${projectId}/classes`);
      
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
    
    loadImageData();
    loadProjectImages();
    loadClasses();
  }, [imageId, projectId, loadImageData, loadProjectImages, loadClasses]);

  // Navigate to previous image with transition
  const navigateToPreviousImage = () => {
    if (currentImageIndex > 0) {
      setIsTransitioning(true);
      setTimeout(() => {
        const prevImage = projectImages[currentImageIndex - 1];
        navigate(`/view/${prevImage.id}?project=${projectId}`);
      }, 300);
    }
  };

  // Navigate to next image with transition
  const navigateToNextImage = () => {
    if (currentImageIndex < projectImages.length - 1) {
      setIsTransitioning(true);
      setTimeout(() => {
        const nextImage = projectImages[currentImageIndex + 1];
        navigate(`/view/${nextImage.id}?project=${projectId}`);
      }, 300);
    }
  };

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
  }, [currentImageIndex, projectImages.length]);

  return (
    <div className="App" style={{ maxWidth: '100%', padding: '10px' }}>
      <header className="App-header">
        <div id="view-header">
          <button 
            className="btn btn-secondary" 
            onClick={() => navigate(`/project/${projectId}`)}
          >
            ← Back to Project
          </button>
          <h1>{image ? image.filename : 'Loading image...'}</h1>
        </div>
      </header>

      <div className="container" style={{ maxWidth: '100%' }}>
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
          <div className="image-navigation">
            <button 
              className="btn btn-secondary navigation-btn"
              onClick={navigateToPreviousImage}
              disabled={currentImageIndex <= 0}
            >
              &lt; Previous
            </button>
            <button 
              className="btn btn-secondary navigation-btn"
              onClick={navigateToNextImage}
              disabled={currentImageIndex >= projectImages.length - 1 || currentImageIndex === -1}
            >
              Next &gt;
            </button>
          </div>
          
          <ImageDisplay 
            imageId={imageId} 
            image={image} 
            isTransitioning={isTransitioning} 
          />
          
          <ImageClassifications 
            imageId={imageId} 
            classes={classes} 
            loading={loading} 
            setLoading={setLoading} 
            setError={setError} 
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
        </div>
      </div>
    </div>
  );
}

export default ImageView;
