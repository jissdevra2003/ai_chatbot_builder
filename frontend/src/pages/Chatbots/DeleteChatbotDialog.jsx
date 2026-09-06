import { useState } from 'react';
import { X, AlertTriangle } from 'lucide-react';
import { chatbotsAPI } from '../../api/client';

export default function DeleteChatbotDialog({ chatbot, onClose, onSuccess }) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState(null);

  const handleDelete = async () => {
    setIsDeleting(true);
    setError(null);

    try {
      await chatbotsAPI.delete(chatbot.id);
      onSuccess(chatbot.id);
    } catch (err) {
      const message =
        err.response?.data?.detail || 'Failed to delete chatbot. Please try again.';
      setError(typeof message === 'string' ? message : JSON.stringify(message));
      setIsDeleting(false);
    }
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal" role="alertdialog" aria-labelledby="delete-chatbot-title">
        <div className="modal-header">
          <h2 id="delete-chatbot-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={20} style={{ color: 'var(--color-error)' }} />
            Delete chatbot
          </h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
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
            Are you sure you want to delete <strong>{chatbot.name}</strong>? This action will
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
              'The chatbot and all its configuration',
              'All uploaded documents and processed chunks',
              'All vector embeddings in the knowledge base',
              'All conversation history and messages',
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
            id="confirm-delete-chatbot"
          >
            {isDeleting ? (
              <>
                <span className="spinner spinner-sm" />
                Deleting…
              </>
            ) : (
              'Yes, delete chatbot'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
