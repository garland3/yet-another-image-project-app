import React, { useState, useRef, useEffect } from 'react';

/**
 * UserAnnotationTool
 * Interactive tool for users to draw bounding boxes on images and add labels.
 * Props:
 *  - imageId: UUID of the image
 *  - naturalSize: { width, height } original image dimensions
 *  - displaySize: { width, height } displayed image dimensions
 *  - userAnnotations: array of existing user annotations
 *  - onAnnotationsChange: callback when annotations change
 *  - enabled: boolean to enable/disable drawing
 */
export default function UserAnnotationTool({
  imageId,
  naturalSize,
  displaySize,
  userAnnotations = [],
  onAnnotationsChange,
  enabled = false
}) {
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentBox, setCurrentBox] = useState(null);
  const [editingAnnotation, setEditingAnnotation] = useState(null);
  const [labelInput, setLabelInput] = useState('');
  const canvasRef = useRef(null);

  // Reset state when disabled
  useEffect(() => {
    if (!enabled) {
      setIsDrawing(false);
      setCurrentBox(null);
      setEditingAnnotation(null);
      setLabelInput('');
    }
  }, [enabled]);

  const handleMouseDown = (e) => {
    if (!enabled) return;
    
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    setIsDrawing(true);
    setCurrentBox({ startX: x, startY: y, endX: x, endY: y });
  };

  const handleMouseMove = (e) => {
    if (!isDrawing || !currentBox) return;
    
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    setCurrentBox(prev => ({ ...prev, endX: x, endY: y }));
  };

  const handleMouseUp = async () => {
    if (!isDrawing || !currentBox) return;
    
    setIsDrawing(false);
    
    // Calculate bounding box in natural image coordinates
    const scaleX = naturalSize.width / displaySize.width;
    const scaleY = naturalSize.height / displaySize.height;
    
    const x1 = Math.min(currentBox.startX, currentBox.endX);
    const y1 = Math.min(currentBox.startY, currentBox.endY);
    const x2 = Math.max(currentBox.startX, currentBox.endX);
    const y2 = Math.max(currentBox.startY, currentBox.endY);
    
    const width = x2 - x1;
    const height = y2 - y1;
    
    // Ignore very small boxes (likely accidental clicks)
    if (width < 5 || height < 5) {
      setCurrentBox(null);
      return;
    }
    
    // Convert to natural coordinates
    const annotationData = {
      annotation_type: 'bounding_box',
      label: null,
      data: {
        x_min: Math.round(x1 * scaleX),
        y_min: Math.round(y1 * scaleY),
        x_max: Math.round(x2 * scaleX),
        y_max: Math.round(y2 * scaleY),
        image_width: naturalSize.width,
        image_height: naturalSize.height
      }
    };
    
    // Create annotation via API
    try {
      const response = await fetch(`/api/images/${imageId}/annotations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(annotationData)
      });
      
      if (!response.ok) {
        console.error('Failed to create annotation:', response.statusText);
        return;
      }
      
      const newAnnotation = await response.json();
      
      // Open label editor for the new annotation
      setEditingAnnotation(newAnnotation);
      setLabelInput('');
      
      // Notify parent
      if (onAnnotationsChange) {
        onAnnotationsChange([...userAnnotations, newAnnotation]);
      }
    } catch (error) {
      console.error('Error creating annotation:', error);
    } finally {
      setCurrentBox(null);
    }
  };

  const handleSaveLabel = async () => {
    if (!editingAnnotation) return;
    
    try {
      const response = await fetch(`/api/annotations/${editingAnnotation.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: labelInput || null })
      });
      
      if (!response.ok) {
        console.error('Failed to update label:', response.statusText);
        return;
      }
      
      const updatedAnnotation = await response.json();
      
      // Update annotations list
      const updatedList = userAnnotations.map(a => 
        a.id === updatedAnnotation.id ? updatedAnnotation : a
      );
      
      if (onAnnotationsChange) {
        onAnnotationsChange(updatedList);
      }
      
      setEditingAnnotation(null);
      setLabelInput('');
    } catch (error) {
      console.error('Error updating label:', error);
    }
  };

  const handleDeleteAnnotation = async (annotationId) => {
    try {
      const response = await fetch(`/api/annotations/${annotationId}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        console.error('Failed to delete annotation:', response.statusText);
        return;
      }
      
      // Remove from list
      const updatedList = userAnnotations.filter(a => a.id !== annotationId);
      
      if (onAnnotationsChange) {
        onAnnotationsChange(updatedList);
      }
      
      if (editingAnnotation?.id === annotationId) {
        setEditingAnnotation(null);
        setLabelInput('');
      }
    } catch (error) {
      console.error('Error deleting annotation:', error);
    }
  };

  // Render bounding boxes
  const renderBoxes = () => {
    const scaleX = displaySize.width / naturalSize.width;
    const scaleY = displaySize.height / naturalSize.height;
    
    return userAnnotations.map(annotation => {
      const data = annotation.data;
      const x = data.x_min * scaleX;
      const y = data.y_min * scaleY;
      const width = (data.x_max - data.x_min) * scaleX;
      const height = (data.y_max - data.y_min) * scaleY;
      
      return (
        <div key={annotation.id}>
          <div
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: width,
              height: height,
              border: '2px solid #00bcd4',
              boxSizing: 'border-box',
              background: 'rgba(0, 188, 212, 0.1)',
              cursor: 'pointer'
            }}
            onClick={(e) => {
              e.stopPropagation();
              setEditingAnnotation(annotation);
              setLabelInput(annotation.label || '');
            }}
          >
            {annotation.label && (
              <div style={{
                position: 'absolute',
                left: 0,
                top: -20,
                background: '#00bcd4',
                color: '#fff',
                fontSize: 12,
                padding: '2px 6px',
                borderRadius: 3,
                whiteSpace: 'nowrap',
                maxWidth: 200,
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {annotation.label}
              </div>
            )}
          </div>
        </div>
      );
    });
  };

  // Render current drawing box
  const renderCurrentBox = () => {
    if (!currentBox) return null;
    
    const x = Math.min(currentBox.startX, currentBox.endX);
    const y = Math.min(currentBox.startY, currentBox.endY);
    const width = Math.abs(currentBox.endX - currentBox.startX);
    const height = Math.abs(currentBox.endY - currentBox.startY);
    
    return (
      <div
        style={{
          position: 'absolute',
          left: x,
          top: y,
          width: width,
          height: height,
          border: '2px dashed #00bcd4',
          boxSizing: 'border-box',
          background: 'rgba(0, 188, 212, 0.2)',
          pointerEvents: 'none'
        }}
      />
    );
  };

  if (!enabled || displaySize.width === 0) return null;

  return (
    <>
      <div
        ref={canvasRef}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: displaySize.width,
          height: displaySize.height,
          cursor: enabled ? 'crosshair' : 'default',
          pointerEvents: enabled ? 'auto' : 'none'
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      >
        {renderBoxes()}
        {renderCurrentBox()}
      </div>
      
      {/* Label editor modal */}
      {editingAnnotation && (
        <div style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          background: 'white',
          padding: '20px',
          borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          zIndex: 1000,
          minWidth: '300px'
        }}>
          <h3 style={{ marginTop: 0 }}>Edit Annotation</h3>
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Label:
            </label>
            <input
              type="text"
              value={labelInput}
              onChange={(e) => setLabelInput(e.target.value)}
              placeholder="Enter label (optional)"
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '14px'
              }}
              autoFocus
            />
          </div>
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
            <button
              onClick={() => handleDeleteAnnotation(editingAnnotation.id)}
              style={{
                padding: '8px 16px',
                background: '#f44336',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Delete
            </button>
            <button
              onClick={() => {
                setEditingAnnotation(null);
                setLabelInput('');
              }}
              style={{
                padding: '8px 16px',
                background: '#757575',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSaveLabel}
              style={{
                padding: '8px 16px',
                background: '#00bcd4',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Save
            </button>
          </div>
        </div>
      )}
      
      {/* Backdrop for modal */}
      {editingAnnotation && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            zIndex: 999
          }}
          onClick={() => {
            setEditingAnnotation(null);
            setLabelInput('');
          }}
        />
      )}
    </>
  );
}
