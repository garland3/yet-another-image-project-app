import React, { useEffect, useState, useCallback } from 'react';

/**
 * MLAnalysisPanel
 * Phase 3 minimal implementation: lists analyses for an image, lets user create a new one,
 * and view annotation counts. Focuses on surfacing existing backend functionality only.
 */
export default function MLAnalysisPanel({ imageId, onSelect, onAnalysesLoaded }) {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // Using fixed model parameters for now (hidden until first analysis exists); could be elevated to a config dialog later.
  const modelName = 'resnet50_classifier';
  const modelVersion = '1';
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState(null);
  const [annotations, setAnnotations] = useState([]);
  const [annLoading, setAnnLoading] = useState(false);

  const fetchAnalyses = useCallback(async () => {
    if (!imageId) return;
    setLoading(true);
    try {
      const resp = await fetch(`/api/images/${imageId}/analyses`);
      if (!resp.ok) throw new Error(`List analyses failed: ${resp.status}`);
      const data = await resp.json();
      const list = data.analyses || [];
      setAnalyses(list);
      if (onAnalysesLoaded) {
        try { onAnalysesLoaded(list.length); } catch (_) { /* noop */ }
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [imageId, onAnalysesLoaded]);

  const createAnalysis = async () => {
    if (creating) return;
    setCreating(true);
    setError(null);
    try {
      const payload = {
        image_id: imageId,
        model_name: modelName,
        model_version: modelVersion,
        parameters: {}
      };
      const resp = await fetch(`/api/images/${imageId}/analyses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!resp.ok) throw new Error(`Create failed: ${resp.status}`);
      await fetchAnalyses();
    } catch (e) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  const selectAnalysis = useCallback(async (id) => {
    setSelected(id);
    setAnnLoading(true);
    setAnnotations([]);
    try {
      const resp = await fetch(`/api/analyses/${id}`);
      if (!resp.ok) throw new Error(`Detail fetch failed: ${resp.status}`);
      const data = await resp.json();
      const anns = data.annotations || [];
      setAnnotations(anns);
      if (onSelect) {
        onSelect({ analysis: data, annotations: anns });
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setAnnLoading(false);
    }
  }, [onSelect]);

  // Poll while there are non-terminal analyses
  useEffect(() => {
    const active = analyses.some(a => ['queued','processing'].includes(a.status));
    if (!active) return;
    const t = setInterval(() => {
      fetchAnalyses();
      if (selected) {
        // Refresh annotations for selected analysis if still selected
        selectAnalysis(selected);
      }
    }, 8000); // 8s cadence
    return () => clearInterval(t);
  }, [analyses, fetchAnalyses, selected, selectAnalysis]);

  useEffect(() => { fetchAnalyses(); }, [fetchAnalyses]);

  const hasAnalyses = analyses.length > 0;

  if (!hasAnalyses) {
    // Show only a minimal unobtrusive launcher button (hide all ML info until user chooses to run)
    return (
      <div style={{ marginTop: '1rem' }}>
        <button
          className="btn btn-outline btn-small"
          disabled={creating || loading}
          onClick={createAnalysis}
          title="Run an ML analysis on this image"
          style={{ width: '100%' }}
        >
          {creating ? 'Starting…' : 'Run ML Analysis'}
        </button>
        {error && <div className="alert alert-error" style={{ marginTop: '0.5rem' }}>{error}</div>}
      </div>
    );
  }

  return (
    <div className="ml-analysis-panel" style={{ border: '1px solid var(--border-color)', borderRadius: 6, padding: '0.75rem', marginTop: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>ML Analyses</h3>
        <button className="btn btn-primary btn-tiny" onClick={createAnalysis} disabled={creating}>New</button>
      </div>
      {error && <div className="alert alert-error" style={{ margin: '0.5rem 0' }}>{error}</div>}
      {loading ? <div>Loading analyses…</div> : (
        <ul style={{ listStyle: 'none', padding: 0, margin: '0.5rem 0', maxHeight: 160, overflowY: 'auto' }}>
          {analyses.map(a => (
            <li key={a.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 2px', cursor: 'pointer', background: selected === a.id ? 'var(--bg-accent, #f3f6fa)' : 'transparent' }} onClick={()=>selectAnalysis(a.id)}>
              <span style={{ fontSize: 12, display: 'flex', flexDirection: 'column' }}>
                <span><strong>{a.model_name}</strong> <span style={{ opacity: 0.7 }}>v{a.model_version}</span></span>
                <span style={{ fontSize: 10, opacity: 0.6 }}>{a.status}</span>
              </span>
              <StatusBadge status={a.status} />
            </li>
          ))}
        </ul>
      )}
      <hr style={{ margin: '0.5rem 0' }} />
      <h4 style={{ margin: '0 0 0.5rem 0', fontSize: 13 }}>Annotations</h4>
      {annLoading ? <div>Loading…</div> : (
        <div style={{ maxHeight: 160, overflowY: 'auto', fontSize: 12 }}>
          {annotations.length === 0 && <div style={{ opacity: 0.7 }}>None.</div>}
          {annotations.map(ann => (
            <div key={ann.id} style={{ borderBottom: '1px solid #eee', padding: '2px 0' }}>
              <code>{ann.annotation_type}</code>{ann.class_name ? `: ${ann.class_name}` : ''} {ann.confidence != null && `( ${(ann.confidence*100).toFixed(1)}% )`}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }) {
  const colorMap = {
    queued: '#888',
    processing: '#0d6efd',
    completed: '#198754',
    failed: '#dc3545',
    canceled: '#6c757d'
  };
  const bg = colorMap[status] || '#444';
  return <span style={{ background: bg, color: 'white', borderRadius: 4, padding: '2px 6px', fontSize: 11, textTransform: 'uppercase' }}>{status}</span>;
}
