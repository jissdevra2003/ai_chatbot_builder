import { useState, useEffect } from 'react';
import { X, AlertTriangle } from 'lucide-react';
import { documentsAPI } from '../../api/client';

/**
 * DeleteDocumentDialog — Confirmation dialog for deleting a document.
 * Follows the same pattern as DeleteChatbotDialog for consistency.
 *
 * Props:
 *  - chatbotId: string
 *  - document: DocumentResponse — the document to delete
 *  - onClose: () => void
 *  - onSuccess: (documentId: string) => void — called after successful deletion
 */
export default function DeleteDocumentDialog({ chatbotId, document, onClose, onSuccess }) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState(null);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && !isDeleting) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, isDeleting]);

  const handleDelete = async () => {
    setIsDeleting(true);
    setError(null);

    try {
      await documentsAPI.delete(chatbotId, document.id);
      onSuccess(document.id);
    } catch (err) {
      const message =
        err.response?.data?.detail || 'Failed to delete document. Please try again.';
      setError(typeof message === 'string' ? message : JSON.stringify(message));
      setIsDeleting(false);
    }
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget && !isDeleting) {
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal" role="alertdialog" aria-labelledby="delete-doc-title">
        <div className="modal-header">
          <h2 id="delete-doc-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={20} style={{ color: 'var(--color-error)' }} />
            Delete document
          </h2>
          <button className="modal-close" onClick={onClose} aria-label="Close" disabled={isDeleting}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {error && (
            <div className="toast toast-error" style={{ marginBottom: 'var(--space-4)' }}>
              {error}
            </div>
          )}

          <div className="confirm-dialog-text">
            Are you sure you want to delete <strong>{document.filename}</strong>? This will
            permanently remove:
          </div>

          <ul style={{
            listStyle: 'none',
            padding: 0,
            margin: '0 0 var(--space-4) 0',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
          }}>
            {[
              'The uploaded document file',
              `All ${document.chunk_count} processed text chunks`,
              'All associated vector embeddings',
            ].map((item, i) => (
              <li
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-2)',
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-text-secondary)',
                }}
              >
                <span style={{ color: 'var(--color-error)', fontWeight: 600 }}>•</span>
                {item}
              </li>
            ))}
          </ul>

          <div style={{
            background: '#FEF2F2',
            border: '1px solid #FECACA',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-3) var(--space-4)',
            fontSize: 'var(--font-size-sm)',
            color: '#991B1B',
            fontWeight: 'var(--font-weight-medium)',
          }}>
            ⚠️ This action cannot be undone.
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={isDeleting}>
            Cancel
          </button>
          <button
            className="btn btn-danger"
            onClick={handleDelete}
            disabled={isDeleting}
            id="confirm-delete-document"
          >
            {isDeleting ? (
              <>
                <span className="spinner spinner-sm" />
                Deleting…
              </>
            ) : (
              'Yes, delete document'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
