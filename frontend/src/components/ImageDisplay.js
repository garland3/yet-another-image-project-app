import React, { useState, useEffect } from 'react';

function ImageDisplay({ imageId, image, isTransitioning }) {
  const [zoomLevel, setZoomLevel] = useState(1);

  // Apply zoom
  const handleZoomIn = () => {
    setZoomLevel(prev => prev + 0.25);
  };

  // Handle zoom out
  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(0.25, prev - 0.25));
  };

  // Handle reset zoom
  const handleResetZoom = () => {
    setZoomLevel(1);
  };

  // Handle download
  const handleDownload = async () => {
    if (!image) return;
    
    try {
      // Get the direct content URL
      const contentUrl = `/images/${imageId}/content`;
      
      // Create a temporary link element
      const link = document.createElement('a');
      link.href = contentUrl;
      link.download = image.filename || 'image';
      
      // Append to the document, click it, and remove it
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
    } catch (error) {
      console.error('Error downloading image:', error);
    }
  };

  // Keyboard navigation for zoom
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === '+' || e.key === '=') {
        handleZoomIn();
      } else if (e.key === '-') {
        handleZoomOut();
      } else if (e.key === '0') {
        handleResetZoom();
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  return (
    <>
      <div 
        id="image-display" 
        className={isTransitioning ? 'transitioning' : ''}
      >
        {!image ? (
          <div className="loading-container">
            <div className="loading"></div>
            <p>Loading image...</p>
          </div>
        ) : (
          <img 
            src={`/images/${imageId}/content`}
            alt={image.filename || 'Image'} 
            id="main-image"
            className="view-image"
            style={{ transform: `scale(${zoomLevel})` }}
          />
        )}
      </div>
      
      <div className="image-controls">
        <button 
          className="btn btn-secondary control-btn"
          onClick={handleZoomIn}
        >
          Zoom In
        </button>
        <button 
          className="btn btn-secondary control-btn"
          onClick={handleZoomOut}
        >
          Zoom Out
        </button>
        <button 
          className="btn btn-secondary control-btn"
          onClick={handleResetZoom}
        >
          Reset
        </button>
        <button 
          className="btn btn-success control-btn"
          onClick={handleDownload}
        >
          Download
        </button>
      </div>
    </>
  );
}

export default ImageDisplay;
