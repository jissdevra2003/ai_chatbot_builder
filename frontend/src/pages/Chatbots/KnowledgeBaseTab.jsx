import { useState, useEffect, useCallback, useRef } from 'react';
import { documentsAPI } from '../../api/client';
import FileUploadZone from './FileUploadZone';
import DocumentTable from './DocumentTable';
import DocumentChunksModal from './DocumentChunksModal';
import DeleteDocumentDialog from './DeleteDocumentDialog';

/** Polling interval for documents with non-terminal status (ms) */
const POLL_INTERVAL_MS = 5000;

/** Terminal statuses that don't need further polling */
const TERMINAL_STATUSES = new Set(['completed', 'failed']);

/**
 * KnowledgeBaseTab — Orchestrator component for the Knowledge Base tab.
 * Fetches documents, manages upload state, auto-polls for status updates,
 * and coordinates sub-components (upload zone, table, modals).
 *
 * Props:
 *  - chatbotId: string
 */
export default function KnowledgeBaseTab({ chatbotId }) {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal targets
  const [chunksTarget, setChunksTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  // Polling ref (so we can clear it on unmount without stale closures)
  const pollTimerRef = useRef(null);
  const isMountedRef = useRef(true);

  /**
   * Fetches the full document list for this chatbot.
   * Used for initial load and polling refresh.
   */
  const fetchDocuments = useCallback(async () => {
    try {
      const response = await documentsAPI.list(chatbotId);
      if (isMountedRef.current) {
        setDocuments(response.data);
        setError(null);
      }
    } catch (err) {
      if (isMountedRef.current) {
        // Only set error on initial load, not on poll failures
        if (documents.length === 0) {
          const message =
            err.response?.data?.detail || 'Failed to load documents.';
          setError(typeof message === 'string' ? message : JSON.stringify(message));
        }
        console.error('Failed to fetch documents:', err);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [chatbotId]); // intentionally exclude `documents` to avoid loop

  /**
   * Initial fetch on mount.
   */
  useEffect(() => {
    isMountedRef.current = true;
    fetchDocuments();
    return () => {
      isMountedRef.current = false;
    };
  }, [fetchDocuments]);

  /**
   * Auto-poll when there are documents in non-terminal states.
   * Stops polling automatically when all documents reach a terminal state.
   */
  useEffect(() => {
    const hasActiveDocuments = documents.some(
      (doc) => !TERMINAL_STATUSES.has(doc.status)
    );

    // Clear any existing poll timer
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    if (hasActiveDocuments) {
      pollTimerRef.current = setInterval(() => {
        fetchDocuments();
      }, POLL_INTERVAL_MS);
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [documents, fetchDocuments]);

  /**
   * Called when a file upload completes. Adds the new document to the list
   * (or refreshes to get the latest state).
   */
  const handleUploadComplete = useCallback(
    (newDocument) => {
      setDocuments((prev) => {
        // Avoid duplicates (in case of race with polling)
        const exists = prev.some((doc) => doc.id === newDocument.id);
        if (exists) {
          return prev.map((doc) =>
            doc.id === newDocument.id ? newDocument : doc
          );
        }
        return [newDocument, ...prev];
      });
    },
    []
  );

  /**
   * Called when an upload fails. Just log it — the FileUploadZone
   * already shows the error inline.
   */
  const handleUploadError = useCallback((filename, errorMessage) => {
    console.error(`Upload failed for ${filename}: ${errorMessage}`);
  }, []);

  /**
   * Opens the chunks preview modal for a document.
   */
  const handleViewChunks = useCallback((document) => {
    setChunksTarget(document);
  }, []);

  /**
   * Opens the delete confirmation dialog for a document.
   */
  const handleDeleteRequest = useCallback((document) => {
    setDeleteTarget(document);
  }, []);

  /**
   * Called after successful document deletion.
   * Removes the document from the local list.
   */
  const handleDeleteSuccess = useCallback((deletedDocId) => {
    setDocuments((prev) => prev.filter((doc) => doc.id !== deletedDocId));
    setDeleteTarget(null);
  }, []);

  // Compute list of existing filenames for duplicate detection in upload zone
  const existingFilenames = documents.map((doc) => doc.filename);

  return (
    <div className="knowledge-base-tab animate-fade-in">
      {/* Header */}
      <div className="settings-panel">
        <div className="settings-panel-header">
          <h3>Knowledge Base</h3>
          <p>
            Upload documents to build your chatbot's knowledge. Files are parsed,
            chunked, and embedded for RAG-powered responses.
          </p>
        </div>

        {/* Upload zone */}
        <FileUploadZone
          chatbotId={chatbotId}
          existingFilenames={existingFilenames}
          onUploadComplete={handleUploadComplete}
          onUploadError={handleUploadError}
        />
      </div>

      {/* Document list */}
      <div className="settings-panel" style={{ marginTop: 'var(--space-6)' }}>
        <div className="settings-panel-header">
          <h3 style={{ display: 'flex', alignItems: 'center' }}>
            Documents
            {documents.length > 0 && (
              <span className="doc-count-badge">{documents.length}</span>
            )}
          </h3>
          <p>Track upload status and manage your chatbot's knowledge documents.</p>
        </div>

        {error && (
          <div className="toast toast-error" style={{ marginBottom: 'var(--space-4)' }}>
            {error}
            <button
              className="btn btn-sm btn-secondary"
              onClick={fetchDocuments}
              style={{ marginLeft: 'auto' }}
            >
              Retry
            </button>
          </div>
        )}

        <DocumentTable
          documents={documents}
          onViewChunks={handleViewChunks}
          onDelete={handleDeleteRequest}
          isLoading={isLoading}
        />
      </div>

      {/* Chunks Preview Modal */}
      {chunksTarget && (
        <DocumentChunksModal
          chatbotId={chatbotId}
          document={chunksTarget}
          onClose={() => setChunksTarget(null)}
        />
      )}

      {/* Delete Confirmation Dialog */}
      {deleteTarget && (
        <DeleteDocumentDialog
          chatbotId={chatbotId}
          document={deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onSuccess={handleDeleteSuccess}
        />
      )}
    </div>
  );
}
