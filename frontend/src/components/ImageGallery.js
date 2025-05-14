import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function ImageGallery({ projectId, images, loading }) {
  const navigate = useNavigate();
  const [imageLoadStatus, setImageLoadStatus] = useState({});
  const [currentPage, setCurrentPage] = useState(1);
  const [debugExpanded, setDebugExpanded] = useState(false); // Debug section collapsed by default
  const imagesPerPage = 50; // Limit to 50 thumbnails per page
  
  // Calculate total pages
  const totalPages = Math.ceil(images.length / imagesPerPage);
  
  // Get current images for the page
  const indexOfLastImage = currentPage * imagesPerPage;
  const indexOfFirstImage = indexOfLastImage - imagesPerPage;
  const currentImages = images.slice(indexOfFirstImage, indexOfLastImage);
  
  // Reset to first page when images array changes
  useEffect(() => {
    setCurrentPage(1);
  }, [images.length]);
  
  // Page change handler
  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    // Scroll to top of gallery
    document.getElementById('images-container')?.scrollIntoView({ behavior: 'smooth' });
  };

  // Helper function to format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2>Images</h2>
      </div>
      <div id="images-container" className="card-content">
        {loading && <p>Loading images...</p>}
        
        {!loading && images.length === 0 && (
          <p>No images found. Upload an image to get started.</p>
        )}
        
        {!loading && images.length > 0 && (
          <>
            <div className="pagination-info">
              <p>Showing {indexOfFirstImage + 1}-{Math.min(indexOfLastImage, images.length)} of {images.length} images</p>
            </div>
            
            <div className="image-gallery">
              {currentImages.map(image => (
              <div 
                key={image.id} 
                className="image-card"
                onClick={() => navigate(`/view/${image.id}?project=${projectId}`)}
              >
                <img 
                  src={`/api/images/${image.id}/thumbnail?width=200&height=200`} 
                  alt={image.filename || 'Image'} 
                  onLoad={() => {
                    console.log(`Thumbnail for image ${image.id} loaded successfully`);
                    setImageLoadStatus(prev => ({
                      ...prev,
                      [image.id]: { status: 'loaded', timestamp: new Date().toISOString() }
                    }));
                  }}
                  onError={(e) => {
                    console.error(`Error loading thumbnail for image ${image.id}:`, e);
                    // Try to fetch the image URL to see if we get a more detailed error
                    fetch(`/api/images/${image.id}/download`)
                      .then(response => {
                        console.log(`Download URL response for ${image.id}:`, response.status, response.statusText);
                        return response.json();
                      })
                      .then(data => {
                        console.log(`Download URL data for ${image.id}:`, data);
                        // Try to fetch the content URL directly
                        return fetch(`/api/images/${image.id}/thumbnail?width=200&height=200`);
                      })
                      .then(response => {
                        console.log(`Thumbnail URL response for ${image.id}:`, response.status, response.statusText);
                      })
                      .catch(err => {
                        console.error(`Error checking image URLs for ${image.id}:`, err);
                      });
                    
                    setImageLoadStatus(prev => ({
                      ...prev,
                      [image.id]: { status: 'error', timestamp: new Date().toISOString(), error: e.message }
                    }));
                    
                    e.target.onerror = null;
                    e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIiBmaWxsPSIjYWFhIj5JbWFnZSBsb2FkIGVycm9yPC90ZXh0Pjwvc3ZnPg==';
                  }}
                />
                <div className="image-info">
                  <p>{image.filename || 'Unnamed image'}</p>
                  <small>{formatFileSize(image.size_bytes)}</small>
                </div>
              </div>
              ))}
            </div>
            
            {totalPages > 1 && (
              <div className="pagination-controls">
                <button 
                  onClick={() => handlePageChange(1)} 
                  disabled={currentPage === 1}
                  className="pagination-button"
                >
                  First
                </button>
                
                <button 
                  onClick={() => handlePageChange(currentPage - 1)} 
                  disabled={currentPage === 1}
                  className="pagination-button"
                >
                  Previous
                </button>
                
                <span className="pagination-info">
                  Page {currentPage} of {totalPages}
                </span>
                
                <button 
                  onClick={() => handlePageChange(currentPage + 1)} 
                  disabled={currentPage === totalPages}
                  className="pagination-button"
                >
                  Next
                </button>
                
                <button 
                  onClick={() => handlePageChange(totalPages)} 
                  disabled={currentPage === totalPages}
                  className="pagination-button"
                >
                  Last
                </button>
              </div>
            )}
          </>
        )}

        {/* Debug information section */}
        <div style={{ marginBottom: '20px', padding: '10px', border: '1px solid #ddd', borderRadius: '4px', backgroundColor: '#f9f9f9' }}>
          <div 
            style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              cursor: 'pointer' 
            }}
            onClick={() => setDebugExpanded(!debugExpanded)}
          >
            <h3 style={{ marginTop: '0', marginBottom: debugExpanded ? '15px' : '0' }}>
              Debug Information
            </h3>
            <span style={{ fontSize: '18px', fontWeight: 'bold' }}>
              {debugExpanded ? '▼' : '►'}
            </span>
          </div>
          
          {debugExpanded && (
            <>
              <p>Image loading status: {Object.keys(imageLoadStatus).length} / {images.length} images tracked</p>
              <ul style={{ maxHeight: '150px', overflowY: 'auto', fontSize: '12px', fontFamily: 'monospace' }}>
                {Object.entries(imageLoadStatus).map(([imageId, status]) => (
                  <li key={imageId} style={{ 
                    color: status.status === 'loaded' ? 'green' : 'red',
                    marginBottom: '5px'
                  }}>
                    {imageId}: {status.status} at {status.timestamp}
                    {status.error && <div>Error: {status.error}</div>}
                  </li>
                ))}
              </ul>
              <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                <button 
                  onClick={(e) => {
                    e.stopPropagation(); // Prevent toggling the debug section
                    console.log('Current image load status:', imageLoadStatus);
                    console.log('Images data:', images);
                  }}
                  style={{ padding: '5px 10px', fontSize: '12px' }}
                >
                  Log Debug Info to Console
                </button>
                
                <button 
                  onClick={(e) => {
                    e.stopPropagation(); // Prevent toggling the debug section
                if (images.length === 0) {
                  console.log('No images to test');
                  return;
                }
                
                // Test the first image
                const testImage = images[0];
                console.log(`Testing image loading for ${testImage.id}...`);
                
                // Test the download URL endpoint
                fetch(`/api/images/${testImage.id}/download`)
                  .then(response => {
                    console.log(`Download URL response: ${response.status} ${response.statusText}`);
                    return response.json();
                  })
                  .then(data => {
                    console.log('Download URL data:', data);
                    
                    // Test the content URL endpoint
                    return fetch(`/api/images/${testImage.id}/content`);
                  })
                  .then(response => {
                    console.log(`Content URL response: ${response.status} ${response.statusText}`);
                    console.log('Content-Type:', response.headers.get('content-type'));
                    
                    // Test the thumbnail URL endpoint
                    return fetch(`/api/images/${testImage.id}/thumbnail?width=200&height=200`);
                  })
                  .then(response => {
                    console.log(`Thumbnail URL response: ${response.status} ${response.statusText}`);
                    console.log('Thumbnail Content-Type:', response.headers.get('content-type'));
                    
                    // Create test image elements
                    const img1 = new Image();
                    img1.onload = () => console.log('Full image loaded successfully');
                    img1.onerror = (e) => console.error('Full image failed to load:', e);
                    img1.src = `/api/images/${testImage.id}/content`;
                    
                    const img2 = new Image();
                    img2.onload = () => console.log('Thumbnail loaded successfully');
                    img2.onerror = (e) => console.error('Thumbnail failed to load:', e);
                    img2.src = `/api/images/${testImage.id}/thumbnail?width=200&height=200`;
                  })
                  .catch(err => {
                    console.error('Error testing image URLs:', err);
                  });
                  }}
                  style={{ padding: '5px 10px', fontSize: '12px' }}
                >
                  Test Image Loading
                </button>
                
                <button 
                  onClick={(e) => {
                    e.stopPropagation(); // Prevent toggling the debug section
                if (images.length === 0) {
                  console.log('No images to test');
                  return;
                }
                
                // Test the first image
                const testImage = images[0];
                console.log(`Testing direct URL loading for ${testImage.id}...`);
                
                // Get the URL from the download endpoint
                fetch(`/api/images/${testImage.id}/download`)
                  .then(response => response.json())
                  .then(data => {
                    console.log('Download URL data:', data);
                    
                    // Create a test div to show the image
                    const testDiv = document.createElement('div');
                    testDiv.style.position = 'fixed';
                    testDiv.style.top = '20px';
                    testDiv.style.right = '20px';
                    testDiv.style.zIndex = '9999';
                    testDiv.style.padding = '10px';
                    testDiv.style.background = 'white';
                    testDiv.style.border = '1px solid black';
                    testDiv.style.boxShadow = '0 0 10px rgba(0,0,0,0.5)';
                    
                    // Add a close button
                    const closeBtn = document.createElement('button');
                    closeBtn.innerText = 'Close';
                    closeBtn.onclick = () => document.body.removeChild(testDiv);
                    testDiv.appendChild(closeBtn);
                    
                    // Add a title
                    const title = document.createElement('p');
                    title.innerText = 'Testing direct URL loading';
                    testDiv.appendChild(title);
                    
                    // Create four test images with different URLs
                    const img1 = document.createElement('img');
                    img1.src = `/api/images/${testImage.id}/content`;
                    img1.style.maxWidth = '200px';
                    img1.style.display = 'block';
                    img1.style.marginBottom = '10px';
                    img1.onload = () => console.log('Image loaded with /content URL');
                    img1.onerror = (e) => console.error('Error loading with /content URL:', e);
                    
                    const img2 = document.createElement('img');
                    img2.src = `/api/images/${testImage.id}/download`;
                    img2.style.maxWidth = '200px';
                    img2.style.display = 'block';
                    img2.style.marginBottom = '10px';
                    img2.onload = () => console.log('Image loaded with /download URL');
                    img2.onerror = (e) => console.error('Error loading with /download URL:', e);
                    
                    const img3 = document.createElement('img');
                    img3.src = data.url; // Use the URL from the response
                    img3.style.maxWidth = '200px';
                    img3.style.display = 'block';
                    img3.style.marginBottom = '10px';
                    img3.onload = () => console.log('Image loaded with response URL');
                    img3.onerror = (e) => console.error('Error loading with response URL:', e);
                    
                    const img4 = document.createElement('img');
                    img4.src = `/api/images/${testImage.id}/thumbnail?width=200&height=200`;
                    img4.style.maxWidth = '200px';
                    img4.style.display = 'block';
                    img4.style.marginBottom = '10px';
                    img4.onload = () => console.log('Image loaded with /thumbnail URL');
                    img4.onerror = (e) => console.error('Error loading with /thumbnail URL:', e);
                    
                    // Add labels and images
                    const label1 = document.createElement('div');
                    label1.innerText = '/api/content URL:';
                    testDiv.appendChild(label1);
                    testDiv.appendChild(img1);
                    
                    const label2 = document.createElement('div');
                    label2.innerText = '/api/download URL:';
                    testDiv.appendChild(label2);
                    testDiv.appendChild(img2);
                    
                    const label3 = document.createElement('div');
                    label3.innerText = 'Response URL:';
                    testDiv.appendChild(label3);
                    testDiv.appendChild(img3);
                    
                    const label4 = document.createElement('div');
                    label4.innerText = '/api/thumbnail URL:';
                    testDiv.appendChild(label4);
                    testDiv.appendChild(img4);
                    
                    document.body.appendChild(testDiv);
                  })
                  .catch(err => {
                    console.error('Error testing direct URL loading:', err);
                  });
                  }}
                  style={{ padding: '5px 10px', fontSize: '12px' }}
                >
                  Test Direct URLs
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default ImageGallery;
