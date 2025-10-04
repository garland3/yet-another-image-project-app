import React, { useState, useEffect } from 'react';

/**
 * HeatmapOverlay
 * Renders heatmap/segmentation mask images from storage_path.
 * Lazy-loads the image using presigned URLs from the backend.
 * Props:
 *  - annotations: array of annotations (filters for heatmap/segmentation/mask types)
 *  - containerSize: { width, height } displayed size
 *  - opacity: overlay opacity
 */
export default function HeatmapOverlay({ annotations, containerSize, opacity }) {
  const [heatmapUrl, setHeatmapUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Find first heatmap/segmentation/mask annotation with storage_path
    const heatmapAnnotation = (annotations || []).find(a =>
      ['heatmap', 'segmentation', 'mask'].includes(a.annotation_type) && a.storage_path
    );

    if (!heatmapAnnotation) {
      setHeatmapUrl(null);
      return;
    }

    // Fetch presigned URL for the heatmap from the backend
    const fetchHeatmap = async () => {
      setLoading(true);
      setError(null);
      try {
        // Request presigned download URL from backend
        const response = await fetch(`/api/ml/artifacts/download?path=${encodeURIComponent(heatmapAnnotation.storage_path)}`);
        if (!response.ok) {
          throw new Error(`Failed to get heatmap URL: ${response.status}`);
        }
        const data = await response.json();
        setHeatmapUrl(data.url || null);
      } catch (err) {
        console.error('Error fetching heatmap:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchHeatmap();
  }, [annotations]);

  if (loading) {
    return (
      <div style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: containerSize.width,
        height: containerSize.height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.1)',
        pointerEvents: 'none'
      }}>
        <span style={{ color: '#fff', fontSize: 12 }}>Loading heatmap...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: containerSize.width,
        height: containerSize.height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(255,0,0,0.1)',
        pointerEvents: 'none'
      }}>
        <span style={{ color: '#c00', fontSize: 11 }}>Heatmap load failed</span>
      </div>
    );
  }

  if (!heatmapUrl) {
    return null;
  }

  return (
    <div
      className="heatmap-overlay"
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: containerSize.width,
        height: containerSize.height,
        pointerEvents: 'none',
        opacity
      }}
    >
      <img
        src={heatmapUrl}
        alt="ML Heatmap"
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain'
        }}
        onError={() => setError('Failed to load heatmap image')}
      />
    </div>
  );
}
