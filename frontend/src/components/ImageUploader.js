import React, { useState } from 'react';

function ImageUploader({ projectId, onUploadComplete, loading, setLoading, setError }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadMetadata, setUploadMetadata] = useState('');

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
        // log the url being called for upload. 
        console.log(`Uploading ${file.name} to /projects/${projectId}/images`);
        const response = await fetch(`/projects/${projectId}/images`, {
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
      onUploadComplete(results);
      setSelectedFiles([]);
      setUploadMetadata('');
      setError(null);
    } catch (err) {
      setError(`Upload failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
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
  );
}

export default ImageUploader;
