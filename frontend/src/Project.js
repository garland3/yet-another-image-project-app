import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './App.css';

function Project() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [images, setImages] = useState([]);
  const [metadata, setMetadata] = useState({});
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [imageLoadStatus, setImageLoadStatus] = useState({});
  
  // Form states
  const [newMetadata, setNewMetadata] = useState({ key: '', value: '' });
  const [bulkMetadata, setBulkMetadata] = useState('');
  const [newClass, setNewClass] = useState({ name: '', description: '' });
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadMetadata, setUploadMetadata] = useState('');

  // Modal states
  const [showEditMetadataModal, setShowEditMetadataModal] = useState(false);
  const [showEditClassModal, setShowEditClassModal] = useState(false);
  const [editingMetadata, setEditingMetadata] = useState({ key: '', value: '' });
  const [editingClass, setEditingClass] = useState({ id: '', name: '', description: '' });

  useEffect(() => {
    // Load project data, metadata, classes, and images
    const fetchProjectData = async () => {
      try {
        setLoading(true);
        
        // Fetch project details
        const projectResponse = await fetch(`/projects/${id}/`);
        if (!projectResponse.ok) {
          throw new Error(`HTTP error! status: ${projectResponse.status}`);
        }
        const projectData = await projectResponse.json();
        setProject(projectData);
        
        // Fetch project metadata
        const metadataResponse = await fetch(`/projects/${id}/metadata-dict`);
        if (metadataResponse.ok) {
          const metadataData = await metadataResponse.json();
          setMetadata(metadataData);
          setBulkMetadata(JSON.stringify(metadataData, null, 2));
        }
        
        // Fetch project classes
        const classesResponse = await fetch(`/projects/${id}/classes`);
        if (classesResponse.ok) {
          const classesData = await classesResponse.json();
          setClasses(classesData);
        }
        
        // Fetch project images
        console.log(`Fetching images for project ${id}...`);
        const imagesResponse = await fetch(`/projects/${id}/images/`);
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

  // Handle file input change
  const handleFileChange = (e) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  // Handle drag and drop
  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      setSelectedFiles(Array.from(e.dataTransfer.files));
    }
  };

  // Handle file upload
  const handleUpload = async (e) => {
    e.preventDefault();
    
    if (selectedFiles.length === 0) {
      setError('Please select at least one file to upload.');
      return;
    }
    
    let parsedMetadata = null;
    if (uploadMetadata.trim()) {
      try {
        parsedMetadata = JSON.parse(uploadMetadata);
      } catch (err) {
        setError('Invalid JSON format for metadata.');
        return;
      }
    }
    
    setLoading(true);
    
    const uploadPromises = selectedFiles.map(async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      
      if (uploadMetadata.trim()) {
        formData.append('metadata', uploadMetadata);
      }
      
      try {
        const response = await fetch(`/projects/${id}/images/`, {
          method: 'POST',
          body: formData
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
      } catch (err) {
        console.error(`Error uploading ${file.name}:`, err);
        throw err;
      }
    });
    
    try {
      const results = await Promise.all(uploadPromises);
      setImages(prevImages => [...prevImages, ...results]);
      setSelectedFiles([]);
      setUploadMetadata('');
      setError(null);
    } catch (err) {
      setError(`Upload failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle metadata form submission
  const handleAddMetadata = async (e) => {
    e.preventDefault();
    
    if (newMetadata.key.trim() === '') {
      setError('Metadata key cannot be empty');
      return;
    }
    
    try {
      setLoading(true);
      
      const response = await fetch(`/projects/${id}/metadata/${newMetadata.key}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          key: newMetadata.key,
          value: parseMetadataValue(newMetadata.value),
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // Update the metadata state
      setMetadata(prevMetadata => ({
        ...prevMetadata,
        [newMetadata.key]: parseMetadataValue(newMetadata.value)
      }));
      
      // Update bulk metadata
      setBulkMetadata(JSON.stringify({
        ...metadata,
        [newMetadata.key]: parseMetadataValue(newMetadata.value)
      }, null, 2));
      
      // Reset form
      setNewMetadata({ key: '', value: '' });
      setError(null);
    } catch (err) {
      setError(`Failed to add metadata: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle bulk metadata update
  const handleBulkUpdateMetadata = async (e) => {
    e.preventDefault();
    
    try {
      const metadataObj = JSON.parse(bulkMetadata);
      
      setLoading(true);
      
      const response = await fetch(`/projects/${id}/metadata-dict`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: bulkMetadata,
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const updatedMetadata = await response.json();
      setMetadata(updatedMetadata);
      setError(null);
    } catch (err) {
      setError(`Failed to update metadata: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle edit metadata
  const handleEditMetadata = async () => {
    try {
      setLoading(true);
      
      const response = await fetch(`/projects/${id}/metadata/${editingMetadata.key}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          key: editingMetadata.key,
          value: parseMetadataValue(editingMetadata.value),
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // Update the metadata state
      setMetadata(prevMetadata => ({
        ...prevMetadata,
        [editingMetadata.key]: parseMetadataValue(editingMetadata.value)
      }));
      
      // Update bulk metadata
      setBulkMetadata(JSON.stringify({
        ...metadata,
        [editingMetadata.key]: parseMetadataValue(editingMetadata.value)
      }, null, 2));
      
      // Close modal
      setShowEditMetadataModal(false);
      setError(null);
    } catch (err) {
      setError(`Failed to update metadata: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle delete metadata
  const handleDeleteMetadata = async (key) => {
    if (!window.confirm(`Are you sure you want to delete the metadata key "${key}"?`)) {
      return;
    }
    
    try {
      setLoading(true);
      
      const response = await fetch(`/projects/${id}/metadata/${key}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // Update the metadata state
      const newMetadata = { ...metadata };
      delete newMetadata[key];
      setMetadata(newMetadata);
      
      // Update bulk metadata
      setBulkMetadata(JSON.stringify(newMetadata, null, 2));
      
      setError(null);
    } catch (err) {
      setError(`Failed to delete metadata: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle add class
  const handleAddClass = async (e) => {
    e.preventDefault();
    
    if (newClass.name.trim() === '') {
      setError('Class name cannot be empty');
      return;
    }
    
    try {
      setLoading(true);
      
      const response = await fetch(`/projects/${id}/classes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: id,
          name: newClass.name,
          description: newClass.description,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const newClassData = await response.json();
      
      // Update the classes state
      setClasses(prevClasses => [...prevClasses, newClassData]);
      
      // Reset form
      setNewClass({ name: '', description: '' });
      setError(null);
    } catch (err) {
      setError(`Failed to add class: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle edit class
  const handleEditClass = async () => {
    try {
      setLoading(true);
      
      const response = await fetch(`/classes/${editingClass.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: editingClass.name,
          description: editingClass.description,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const updatedClass = await response.json();
      
      // Update the classes state
      setClasses(prevClasses => 
        prevClasses.map(cls => 
          cls.id === editingClass.id ? updatedClass : cls
        )
      );
      
      // Close modal
      setShowEditClassModal(false);
      setError(null);
    } catch (err) {
      setError(`Failed to update class: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle delete class
  const handleDeleteClass = async (id, name) => {
    if (!window.confirm(`Are you sure you want to delete the class "${name}"?`)) {
      return;
    }
    
    try {
      setLoading(true);
      
      const response = await fetch(`/classes/${id}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // Update the classes state
      setClasses(prevClasses => prevClasses.filter(cls => cls.id !== id));
      
      setError(null);
    } catch (err) {
      setError(`Failed to delete class: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Helper function to parse metadata value
  const parseMetadataValue = (value) => {
    if (value.trim() === '') {
      return null;
    }
    
    try {
      return JSON.parse(value);
    } catch (e) {
      return value;
    }
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
    <div className="App">
      <header className="App-header">
        <div id="project-header">
          <button 
            className="btn btn-secondary" 
            onClick={() => navigate('/')}
          >
            ← Back to Projects
          </button>
          <h1>{project ? project.name : 'Loading project...'}</h1>
          <p>{project ? (project.description || 'No description') : ''}</p>
        </div>
      </header>

      <div className="container">
        {error && <div className="alert alert-error">Error: {error}</div>}
        
        <div className="card">
          <div className="card-header">
            <h2>Upload Images</h2>
          </div>
          <div className="card-content">
            <form onSubmit={handleUpload}>
              <div 
                className="upload-area"
                onDragOver={(e) => e.preventDefault()}
                onDragLeave={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-input').click()}
              >
                <p>Drag and drop images here, or click to select files</p>
                <p>{selectedFiles.length > 0 
                  ? `${selectedFiles.length} ${selectedFiles.length === 1 ? 'file' : 'files'} selected` 
                  : 'No file selected'}</p>
                <input 
                  type="file" 
                  id="file-input" 
                  accept="image/*" 
                  multiple 
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="metadata-input">Metadata (Optional JSON)</label>
                <textarea 
                  id="metadata-input" 
                  rows="3" 
                  placeholder='{"key": "value"}'
                  value={uploadMetadata}
                  onChange={(e) => setUploadMetadata(e.target.value)}
                ></textarea>
              </div>
              
              <div className="form-group">
                <button 
                  type="submit" 
                  className="btn btn-success"
                  disabled={loading}
                >
                  {loading ? 'Uploading...' : 'Upload Images'}
                </button>
              </div>
            </form>
          </div>
        </div>
        
        <div className="card">
          <div className="card-header">
            <h2>Project Metadata</h2>
          </div>
          <div className="card-content">
            <div id="metadata-container">
              {loading && <p>Loading metadata...</p>}
              
              {!loading && Object.keys(metadata).length === 0 && (
                <p>No metadata defined for this project. Add metadata to get started.</p>
              )}
              
              {!loading && Object.keys(metadata).length > 0 && (
                <table className="metadata-table">
                  <thead>
                    <tr>
                      <th>Key</th>
                      <th>Value</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(metadata).map(([key, value]) => (
                      <tr key={key}>
                        <td>{key}</td>
                        <td className="metadata-value">
                          {value === null ? (
                            <span className="metadata-null">null</span>
                          ) : typeof value === 'object' ? (
                            <pre>{JSON.stringify(value, null, 2)}</pre>
                          ) : (
                            value.toString()
                          )}
                        </td>
                        <td className="metadata-actions">
                          <button 
                            className="btn btn-small"
                            onClick={() => {
                              setEditingMetadata({
                                key,
                                value: typeof value === 'object' 
                                  ? JSON.stringify(value, null, 2) 
                                  : (value === null ? '' : value)
                              });
                              setShowEditMetadataModal(true);
                            }}
                          >
                            Edit
                          </button>
                          <button 
                            className="btn btn-small btn-danger"
                            onClick={() => handleDeleteMetadata(key)}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            
            <form id="add-metadata-form" className="form" onSubmit={handleAddMetadata}>
              <h3>Add Metadata</h3>
              <div className="form-group">
                <label htmlFor="metadata-key">Key:</label>
                <input 
                  type="text" 
                  id="metadata-key" 
                  name="metadata-key" 
                  value={newMetadata.key}
                  onChange={(e) => setNewMetadata({...newMetadata, key: e.target.value})}
                  required 
                />
              </div>
              <div className="form-group">
                <label htmlFor="metadata-value">Value:</label>
                <textarea 
                  id="metadata-value" 
                  name="metadata-value" 
                  rows="3"
                  value={newMetadata.value}
                  onChange={(e) => setNewMetadata({...newMetadata, value: e.target.value})}
                ></textarea>
                <small>You can enter a simple value or valid JSON</small>
              </div>
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={loading}
              >
                Add Metadata
              </button>
            </form>
            
            <hr />
            
            <form id="bulk-update-metadata-form" className="form" onSubmit={handleBulkUpdateMetadata}>
              <h3>Bulk Update Metadata</h3>
              <div className="form-group">
                <label htmlFor="metadata-json">Metadata JSON:</label>
                <textarea 
                  id="metadata-json" 
                  name="metadata-json" 
                  rows="5" 
                  value={bulkMetadata}
                  onChange={(e) => setBulkMetadata(e.target.value)}
                  required
                ></textarea>
              </div>
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={loading}
              >
                Update Metadata
              </button>
            </form>
          </div>
        </div>
        
        <div className="card">
          <div className="card-header">
            <h2>Image Classes</h2>
          </div>
          <div className="card-content">
            <div id="classes-container">
              {loading && <p>Loading classes...</p>}
              
              {!loading && classes.length === 0 && (
                <p>No classes defined for this project. Add a class to get started.</p>
              )}
              
              {!loading && classes.length > 0 && (
                <ul className="class-list">
                  {classes.map(cls => (
                    <li key={cls.id} className="class-item">
                      <div className="class-info">
                        <h4>{cls.name}</h4>
                        <p>{cls.description || 'No description'}</p>
                      </div>
                      <div className="class-actions">
                        <button 
                          className="btn btn-small"
                          onClick={() => {
                            setEditingClass({
                              id: cls.id,
                              name: cls.name,
                              description: cls.description || ''
                            });
                            setShowEditClassModal(true);
                          }}
                        >
                          Edit
                        </button>
                        <button 
                          className="btn btn-small btn-danger"
                          onClick={() => handleDeleteClass(cls.id, cls.name)}
                        >
                          Delete
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            
            <form id="add-class-form" className="form" onSubmit={handleAddClass}>
              <h3>Add Class</h3>
              <div className="form-group">
                <label htmlFor="class-name">Name:</label>
                <input 
                  type="text" 
                  id="class-name" 
                  name="class-name" 
                  value={newClass.name}
                  onChange={(e) => setNewClass({...newClass, name: e.target.value})}
                  required 
                />
              </div>
              <div className="form-group">
                <label htmlFor="class-description">Description:</label>
                <textarea 
                  id="class-description" 
                  name="class-description" 
                  rows="2"
                  value={newClass.description}
                  onChange={(e) => setNewClass({...newClass, description: e.target.value})}
                ></textarea>
              </div>
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={loading}
              >
                Add Class
              </button>
            </form>
          </div>
        </div>
        
        <div className="card">
          <div className="card-header">
            <h2>Images</h2>
          </div>
          <div id="images-container" className="card-content">
            {/* Debug information section */}
            <div style={{ marginBottom: '20px', padding: '10px', border: '1px solid #ddd', borderRadius: '4px', backgroundColor: '#f9f9f9' }}>
              <h3 style={{ marginTop: '0' }}>Debug Information</h3>
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
                  onClick={() => {
                    console.log('Current image load status:', imageLoadStatus);
                    console.log('Images data:', images);
                  }}
                  style={{ padding: '5px 10px', fontSize: '12px' }}
                >
                  Log Debug Info to Console
                </button>
                
                <button 
                  onClick={() => {
                    if (images.length === 0) {
                      console.log('No images to test');
                      return;
                    }
                    
                    // Test the first image
                    const testImage = images[0];
                    console.log(`Testing image loading for ${testImage.id}...`);
                    
                    // Test the download URL endpoint
                    fetch(`/images/${testImage.id}/download`)
                      .then(response => {
                        console.log(`Download URL response: ${response.status} ${response.statusText}`);
                        return response.json();
                      })
                      .then(data => {
                        console.log('Download URL data:', data);
                        
                        // Test the content URL endpoint
                        return fetch(`/images/${testImage.id}/content`);
                      })
                      .then(response => {
                        console.log(`Content URL response: ${response.status} ${response.statusText}`);
                        console.log('Content-Type:', response.headers.get('content-type'));
                        
                        // Create a test image element
                        const img = new Image();
                        img.onload = () => console.log('Test image loaded successfully');
                        img.onerror = (e) => console.error('Test image failed to load:', e);
                        img.src = `/images/${testImage.id}/content`;
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
                  onClick={() => {
                    if (images.length === 0) {
                      console.log('No images to test');
                      return;
                    }
                    
                    // Test the first image
                    const testImage = images[0];
                    console.log(`Testing direct URL loading for ${testImage.id}...`);
                    
                    // Get the URL from the download endpoint
                    fetch(`/images/${testImage.id}/download`)
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
                        
                        // Create three test images with different URLs
                        const img1 = document.createElement('img');
                        img1.src = `/images/${testImage.id}/content`;
                        img1.style.maxWidth = '200px';
                        img1.style.display = 'block';
                        img1.style.marginBottom = '10px';
                        img1.onload = () => console.log('Image loaded with /content URL');
                        img1.onerror = (e) => console.error('Error loading with /content URL:', e);
                        
                        const img2 = document.createElement('img');
                        img2.src = `/images/${testImage.id}/download`;
                        img2.style.maxWidth = '200px';
                        img2.style.display = 'block';
                        img2.style.marginBottom = '10px';
                        img2.onload = () => console.log('Image loaded with /download URL');
                        img2.onerror = (e) => console.error('Error loading with /download URL:', e);
                        
                        const img3 = document.createElement('img');
                        img3.src = data.url; // Use the URL from the response
                        img3.style.maxWidth = '200px';
                        img3.style.display = 'block';
                        img3.onload = () => console.log('Image loaded with response URL');
                        img3.onerror = (e) => console.error('Error loading with response URL:', e);
                        
                        // Add labels and images
                        const label1 = document.createElement('div');
                        label1.innerText = '/content URL:';
                        testDiv.appendChild(label1);
                        testDiv.appendChild(img1);
                        
                        const label2 = document.createElement('div');
                        label2.innerText = '/download URL:';
                        testDiv.appendChild(label2);
                        testDiv.appendChild(img2);
                        
                        const label3 = document.createElement('div');
                        label3.innerText = 'Response URL:';
                        testDiv.appendChild(label3);
                        testDiv.appendChild(img3);
                        
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
            </div>
            {loading && <p>Loading images...</p>}
            
            {!loading && images.length === 0 && (
              <p>No images found. Upload an image to get started.</p>
            )}
            
            {!loading && images.length > 0 && (
              <div className="image-gallery">
                {images.map(image => (
                  <div 
                    key={image.id} 
                    className="image-card"
                    onClick={() => navigate(`/view/${image.id}?project=${id}`)}
                  >
                    <img 
                      src={`/images/${image.id}/content`} 
                      alt={image.filename || 'Image'} 
                      onLoad={() => {
                        console.log(`Image ${image.id} loaded successfully`);
                        setImageLoadStatus(prev => ({
                          ...prev,
                          [image.id]: { status: 'loaded', timestamp: new Date().toISOString() }
                        }));
                      }}
                      onError={(e) => {
                        console.error(`Error loading image ${image.id}:`, e);
                        // Try to fetch the image URL to see if we get a more detailed error
                        fetch(`/images/${image.id}/download`)
                          .then(response => {
                            console.log(`Download URL response for ${image.id}:`, response.status, response.statusText);
                            return response.json();
                          })
                          .then(data => {
                            console.log(`Download URL data for ${image.id}:`, data);
                            // Try to fetch the content URL directly
                            return fetch(`/images/${image.id}/content`);
                          })
                          .then(response => {
                            console.log(`Content URL response for ${image.id}:`, response.status, response.statusText);
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
            )}
          </div>
        </div>
      </div>

      {/* Edit metadata modal */}
      {showEditMetadataModal && (
        <div className="modal">
          <div className="modal-content">
            <span 
              className="close-modal" 
              onClick={() => setShowEditMetadataModal(false)}
            >
              &times;
            </span>
            <h2>Edit Metadata</h2>
            <form id="edit-metadata-form" className="form">
              <input type="hidden" value={editingMetadata.key} />
              <div className="form-group">
                <label htmlFor="edit-metadata-value">Value:</label>
                <textarea 
                  id="edit-metadata-value" 
                  name="edit-metadata-value" 
                  rows="3"
                  value={editingMetadata.value}
                  onChange={(e) => setEditingMetadata({...editingMetadata, value: e.target.value})}
                ></textarea>
                <small>You can enter a simple value or valid JSON</small>
              </div>
              <button 
                type="button" 
                className="btn btn-primary"
                onClick={handleEditMetadata}
                disabled={loading}
              >
                Update Metadata
              </button>
            </form>
          </div>
        </div>
      )}
      
      {/* Edit class modal */}
      {showEditClassModal && (
        <div className="modal">
          <div className="modal-content">
            <span 
              className="close-modal" 
              onClick={() => setShowEditClassModal(false)}
            >
              &times;
            </span>
            <h2>Edit Class</h2>
            <form id="edit-class-form" className="form">
              <input type="hidden" value={editingClass.id} />
              <div className="form-group">
                <label htmlFor="edit-class-name">Name:</label>
                <input 
                  type="text" 
                  id="edit-class-name" 
                  name="edit-class-name" 
                  value={editingClass.name}
                  onChange={(e) => setEditingClass({...editingClass, name: e.target.value})}
                  required 
                />
              </div>
              <div className="form-group">
                <label htmlFor="edit-class-description">Description:</label>
                <textarea 
                  id="edit-class-description" 
                  name="edit-class-description" 
                  rows="2"
                  value={editingClass.description}
                  onChange={(e) => setEditingClass({...editingClass, description: e.target.value})}
                ></textarea>
              </div>
              <button 
                type="button" 
                className="btn btn-primary"
                onClick={handleEditClass}
                disabled={loading}
              >
                Update Class
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Project;
