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
      console.log(`Starting download for image ${imageId}...`);
      
      // Try multiple endpoints to find the working one
      const endpoints = [
        `/api/images/${imageId}/content`,
        `/api/images/${imageId}/download`,
      ];
      
      let imageBlob = null;
      let filename = image.filename || `image-${imageId}`;
      
      for (const endpoint of endpoints) {
        try {
          console.log(`Trying endpoint: ${endpoint}`);
          const response = await fetch(endpoint);
          
          if (!response.ok) {
            console.log(`Endpoint ${endpoint} failed: ${response.status} ${response.statusText}`);
            continue;
          }
          
          const contentType = response.headers.get('content-type');
          console.log(`Endpoint ${endpoint} - Content-Type: ${contentType}`);
          
          if (contentType && contentType.includes('application/json')) {
            // This might be a redirect URL response
            const jsonData = await response.json();
            console.log('Got JSON response:', jsonData);
            
            if (jsonData.url) {
              // Try to fetch from the provided URL
              console.log(`Fetching from provided URL: ${jsonData.url}`);
              const imageResponse = await fetch(jsonData.url);
              
              if (imageResponse.ok) {
                const blobContentType = imageResponse.headers.get('content-type');
                if (blobContentType && blobContentType.startsWith('image/')) {
                  imageBlob = await imageResponse.blob();
                  break;
                }
              }
            }
          } else if (contentType && contentType.startsWith('image/')) {
            // Direct image response
            imageBlob = await response.blob();
            break;
          } else {
            console.log(`Unexpected content type: ${contentType}`);
          }
        } catch (endpointError) {
          console.error('Error with endpoint %s:', endpoint, endpointError);
          continue;
        }
      }
      
      if (!imageBlob) {
        throw new Error('Unable to download image from any available endpoint');
      }
      
      console.log('Successfully got image blob:', {
        size: imageBlob.size,
        type: imageBlob.type
      });
      
      // Ensure we have the right file extension
      if (!filename.includes('.') && imageBlob.type) {
        const extension = imageBlob.type.split('/')[1];
        if (extension && extension !== 'jpeg') {
          filename = `${filename}.${extension}`;
        } else if (extension === 'jpeg') {
          filename = `${filename}.jpg`;
        }
      }
      
      // Create a URL for the blob and trigger download
      const blobUrl = window.URL.createObjectURL(imageBlob);
      
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      
      // Append to the document, click it, and remove it
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clean up the blob URL
      window.URL.revokeObjectURL(blobUrl);
      
      console.log(`Download completed successfully: ${filename}`);
      
    } catch (error) {
      console.error('Error downloading image:', error);
      alert(`Download failed: ${error.message}`);
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
            src={`/api/images/${imageId}/content`}
            alt={image.filename || 'Image'} 
            id="main-image"
            className="view-image"
            style={{ transform: `scale(${zoomLevel})` }}
            onError={(e) => {
              console.error('Failed to load image with ID: %s', imageId, e);
              // Try the thumbnail endpoint as fallback
              if (!e.target.src.includes('thumbnail')) {
                e.target.src = `/api/images/${imageId}/thumbnail?width=800&height=600`;
              }
            }}
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
        <button 
          className="btn btn-secondary control-btn"
          onClick={() => {
            console.log('Debug info for image:', {
              imageId,
              image,
              contentUrl: `/api/images/${imageId}/content`,
              downloadUrl: `/api/images/${imageId}/download`
            });
            // Test the endpoints directly
            fetch(`/api/images/${imageId}/content`)
              .then(response => {
                console.log('Content endpoint response:', {
                  status: response.status,
                  contentType: response.headers.get('content-type'),
                  size: response.headers.get('content-length')
                });
              })
              .catch(err => console.error('Content endpoint error:', err));
            
            fetch(`/api/images/${imageId}/download`)
              .then(response => response.json())
              .then(data => console.log('Download endpoint response:', data))
              .catch(err => console.error('Download endpoint error:', err));
          }}
        >
          Debug
        </button>
      </div>
    </>
  );
}

export default ImageDisplay;
