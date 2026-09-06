import { memo, useCallback } from 'react';
import {
  FileText,
  File,
  FileSpreadsheet,
  Trash2,
  Eye,
  AlertCircle,
  Loader,
} from 'lucide-react';

/**
 * Maps file extension to a display icon.
 */
const FILE_TYPE_ICONS = {
  pdf: FileText,
  docx: File,
  txt: FileText,
  csv: FileSpreadsheet,
};

/**
 * Status configuration for badge rendering.
 * Each status maps to a CSS class and display label.
 */
const STATUS_CONFIG = {
  queued: { className: 'badge-neutral', label: 'Queued', active: true },
  pending: { className: 'badge-neutral', label: 'Pending', active: true },
  processing: { className: 'badge-info', label: 'Processing', active: true },
  extracting: { className: 'badge-info', label: 'Extracting', active: true },
  chunking: { className: 'badge-info', label: 'Chunking', active: true },
  embedding: { className: 'badge-info', label: 'Embedding', active: true },
  indexing: { className: 'badge-info', label: 'Indexing', active: true },
  completed: { className: 'badge-success', label: 'Completed', active: false },
  failed: { className: 'badge-error', label: 'Failed', active: false },
};

/**
 * Formats bytes into a human-readable string.
 */
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Formats a date string into a short readable format.
 */
function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Formats a date string into a relative time string (e.g., "2 minutes ago").
 */
function formatRelativeTime(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return formatDate(dateStr);
}

/**
 * A single document row rendered as a memo'd component for performance.
 */
const DocumentRow = memo(function DocumentRow({
  document,
  onViewChunks,
  onDelete,
}) {
  const FileIcon = FILE_TYPE_ICONS[document.file_type] || FileText;
  const statusConfig = STATUS_CONFIG[document.status] || STATUS_CONFIG.pending;

  const handleViewChunks = useCallback(() => {
    onViewChunks(document);
  }, [document, onViewChunks]);

  const handleDelete = useCallback(() => {
    onDelete(document);
  }, [document, onDelete]);

  return (
    <tr className="doc-table-row" id={`doc-row-${document.id}`}>
      {/* Filename + type icon */}
      <td className="doc-table-cell doc-table-cell-name">
        <div className="doc-name-wrapper">
          <div className="doc-type-icon">
            <FileIcon size={16} />
          </div>
          <div className="doc-name-text">
            <span className="doc-filename" title={document.filename}>
              {document.filename}
            </span>
            <span className="doc-filetype">.{document.file_type}</span>
          </div>
        </div>
      </td>

      {/* Size */}
      <td className="doc-table-cell doc-table-cell-size">
        {formatFileSize(document.file_size_bytes)}
      </td>

      {/* Status */}
      <td className="doc-table-cell doc-table-cell-status">
        <span className={`badge ${statusConfig.className}`}>
          {statusConfig.active && (
            <Loader size={12} className="badge-spinner" />
          )}
          {statusConfig.label}
          {statusConfig.active && document.progress > 0 && (
            <span style={{ marginLeft: '4px', fontSize: '0.75rem', opacity: 0.8 }}>
              {document.progress}%
            </span>
          )}
        </span>
        {document.status === 'failed' && document.error_message && (
          <span className="doc-error-tooltip" title={document.error_message}>
            <AlertCircle size={14} />
          </span>
        )}
      </td>

      {/* Chunks */}
      <td className="doc-table-cell doc-table-cell-chunks">
        {document.status === 'completed' ? document.chunk_count : '—'}
      </td>

      {/* Uploaded */}
      <td className="doc-table-cell doc-table-cell-date" title={formatDate(document.created_at)}>
        {formatRelativeTime(document.created_at)}
      </td>

      {/* Actions */}
      <td className="doc-table-cell doc-table-cell-actions">
        <div className="doc-actions">
          {document.status === 'completed' && (
            <button
              className="doc-action-btn"
              onClick={handleViewChunks}
              title="View chunks"
              aria-label={`View chunks for ${document.filename}`}
              id={`view-chunks-${document.id}`}
            >
              <Eye size={15} />
            </button>
          )}
          <button
            className="doc-action-btn doc-action-btn-danger"
            onClick={handleDelete}
            title="Delete document"
            aria-label={`Delete ${document.filename}`}
            id={`delete-doc-${document.id}`}
          >
            <Trash2 size={15} />
          </button>
        </div>
      </td>
    </tr>
  );
});

/**
 * DocumentTable — Displays uploaded documents in a responsive table with
 * status badges, actions, and empty state.
 *
 * Props:
 *  - documents: DocumentResponse[]
 *  - onViewChunks: (document) => void
 *  - onDelete: (document) => void
 *  - isLoading: boolean
 */
export default function DocumentTable({
  documents,
  onViewChunks,
  onDelete,
  isLoading = false,
}) {
  // Loading skeleton
  if (isLoading) {
    return (
      <div className="doc-table-loading">
        {[1, 2, 3].map((i) => (
          <div key={i} className="skeleton doc-table-skeleton" />
        ))}
      </div>
    );
  }

  // Empty state
  if (!documents || documents.length === 0) {
    return (
      <div className="doc-table-empty">
        <FileText size={20} style={{ color: 'var(--color-text-tertiary)' }} />
        <span>No documents uploaded yet</span>
        <span className="doc-table-empty-hint">
          Upload PDF, DOCX, TXT, or CSV files to build your chatbot's knowledge base.
        </span>
      </div>
    );
  }

  return (
    <div className="doc-table-wrapper">
      <table className="doc-table" role="table">
        <thead>
          <tr>
            <th className="doc-table-th">Document</th>
            <th className="doc-table-th">Size</th>
            <th className="doc-table-th">Status</th>
            <th className="doc-table-th">Chunks</th>
            <th className="doc-table-th">Uploaded</th>
            <th className="doc-table-th">Actions</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => (
            <DocumentRow
              key={doc.id}
              document={doc}
              onViewChunks={onViewChunks}
              onDelete={onDelete}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
