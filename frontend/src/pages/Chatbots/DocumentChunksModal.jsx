import { useState, useEffect, useCallback, useRef } from 'react';
import { X, FileText, ChevronDown, ChevronRight, Hash } from 'lucide-react';
import { documentsAPI } from '../../api/client';

/** Number of chunks to show per page / "Load more" batch */
const CHUNKS_PER_PAGE = 20;

/** Maximum characters to show in a collapsed chunk preview */
const PREVIEW_CHAR_LIMIT = 300;

/**
 * DocumentChunksModal — Displays a document's text chunks in a paginated,
 * expandable list. Chunks are fetched on-demand when the modal opens.
 *
 * Props:
 *  - chatbotId: string
 *  - document: DocumentResponse — the document whose chunks to display
 *  - onClose: () => void
 */
export default function DocumentChunksModal({ chatbotId, document, onClose }) {
  const [chunks, setChunks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [visibleCount, setVisibleCount] = useState(CHUNKS_PER_PAGE);
  const [expandedChunks, setExpandedChunks] = useState(new Set());
  const modalContentRef = useRef(null);

  // Fetch chunks on mount
  useEffect(() => {
    let cancelled = false;

    const fetchChunks = async () => {
      try {
        setError(null);
        const response = await documentsAPI.getChunks(chatbotId, document.id);
        if (!cancelled) {
          setChunks(response.data);
        }
      } catch (err) {
        if (!cancelled) {
          const message =
            err.response?.data?.detail || 'Failed to load document chunks.';
          setError(typeof message === 'string' ? message : JSON.stringify(message));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchChunks();

    return () => {
      cancelled = true;
    };
  }, [chatbotId, document.id]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Close on overlay click
  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Toggle expand/collapse for a chunk
  const toggleChunkExpand = useCallback((chunkId) => {
    setExpandedChunks((prev) => {
      const next = new Set(prev);
      if (next.has(chunkId)) {
        next.delete(chunkId);
      } else {
        next.add(chunkId);
      }
      return next;
    });
  }, []);

  // Load more chunks
  const handleLoadMore = useCallback(() => {
    setVisibleCount((prev) => prev + CHUNKS_PER_PAGE);
  }, []);

  const visibleChunks = chunks.slice(0, visibleCount);
  const hasMore = visibleCount < chunks.length;

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div
        className="modal chunks-modal"
        role="dialog"
        aria-labelledby="chunks-modal-title"
        aria-describedby="chunks-modal-desc"
      >
        {/* Header */}
        <div className="modal-header">
          <div>
            <h2 id="chunks-modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={20} />
              Document Chunks
            </h2>
            <p
              id="chunks-modal-desc"
              style={{
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text-secondary)',
                marginTop: 'var(--space-1)',
              }}
            >
              {document.filename} — {document.chunk_count} chunks
            </p>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body chunks-modal-body" ref={modalContentRef}>
          {/* Loading state */}
          {isLoading && (
            <div className="chunks-loading">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="skeleton chunks-skeleton" />
              ))}
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="toast toast-error" style={{ marginBottom: 'var(--space-4)' }}>
              {error}
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && chunks.length === 0 && (
            <div className="chunks-empty">
              <FileText size={20} style={{ color: 'var(--color-text-tertiary)' }} />
              <span>No chunks found for this document.</span>
            </div>
          )}

          {/* Chunk list */}
          {!isLoading && !error && chunks.length > 0 && (
            <div className="chunks-list" role="list">
              {visibleChunks.map((chunk) => {
                const isExpanded = expandedChunks.has(chunk.id);
                const isLong = chunk.content.length > PREVIEW_CHAR_LIMIT;
                const displayContent =
                  isExpanded || !isLong
                    ? chunk.content
                    : chunk.content.slice(0, PREVIEW_CHAR_LIMIT) + '…';

                return (
                  <div
                    key={chunk.id}
                    className={`chunk-card ${isExpanded ? 'expanded' : ''}`}
                    role="listitem"
                  >
                    <div
                      className="chunk-card-header"
                      onClick={() => isLong && toggleChunkExpand(chunk.id)}
                      role={isLong ? 'button' : undefined}
                      tabIndex={isLong ? 0 : undefined}
                      onKeyDown={(e) => {
                        if (isLong && (e.key === 'Enter' || e.key === ' ')) {
                          e.preventDefault();
                          toggleChunkExpand(chunk.id);
                        }
                      }}
                      aria-expanded={isLong ? isExpanded : undefined}
                    >
                      <div className="chunk-card-meta">
                        {isLong && (
                          isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />
                        )}
                        <Hash size={12} />
                        <span className="chunk-index">{chunk.chunk_index + 1}</span>
                        <span className="chunk-chars">{chunk.char_count.toLocaleString()} chars</span>
                      </div>
                    </div>
                    <div className="chunk-card-content">
                      <pre className="chunk-text">{displayContent}</pre>
                    </div>
                  </div>
                );
              })}

              {/* Load more button */}
              {hasMore && (
                <button
                  className="btn btn-secondary btn-sm chunks-load-more"
                  onClick={handleLoadMore}
                  id="load-more-chunks"
                >
                  Load more ({chunks.length - visibleCount} remaining)
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
