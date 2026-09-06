import { useState, useRef, useCallback } from 'react';
import { Upload, X, FileText, AlertCircle, CheckCircle2 } from 'lucide-react';
import { documentsAPI } from '../../api/client';

/**
 * Allowed file extensions and corresponding MIME types.
 * Defense-in-depth: backend also validates, but we reject early on the client
 * to save bandwidth and give instant feedback.
 */
const ALLOWED_EXTENSIONS = ['pdf', 'docx', 'txt', 'csv'];
const ALLOWED_MIME_TYPES = new Set([
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/csv',
  'application/csv',
]);
const MAX_FILE_SIZE_MB = 500;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

/**
 * Extracts the file extension from a filename, lowercased.
 * Returns empty string if no extension found.
 */
function getFileExtension(filename) {
  if (!filename || !filename.includes('.')) return '';
  return filename.split('.').pop().toLowerCase();
}

/**
 * Formats bytes into a human-readable string (KB, MB).
 */
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * FileUploadZone — Drag-and-drop file upload with client-side validation,
 * progress tracking, and cancellation support.
 *
 * Props:
 *  - chatbotId: string
 *  - existingFilenames: string[] — filenames already uploaded (for duplicate detection)
 *  - onUploadComplete: (document) => void — called when a file finishes uploading
 *  - onUploadError: (filename, errorMessage) => void
 *  - disabled: boolean
 */
export default function FileUploadZone({
  chatbotId,
  existingFilenames = [],
  onUploadComplete,
  onUploadError,
  disabled = false,
}) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadQueue, setUploadQueue] = useState([]); // [{ id, file, progress, status, error, abortController }]
  const fileInputRef = useRef(null);
  const uploadIdRef = useRef(0);
  const dragCounterRef = useRef(0);

  /**
   * Validates a single file before adding to the upload queue.
   * Returns { valid: boolean, error?: string }
   */
  const validateFile = useCallback(
    (file) => {
      const ext = getFileExtension(file.name);

      // Extension check
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        return {
          valid: false,
          error: `Unsupported file type ".${ext}". Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`,
        };
      }

      // MIME type check (some browsers may not set type for certain files)
      if (file.type && !ALLOWED_MIME_TYPES.has(file.type)) {
        return {
          valid: false,
          error: `Invalid MIME type "${file.type}" for .${ext} file.`,
        };
      }

      // Size check
      if (file.size > MAX_FILE_SIZE_BYTES) {
        return {
          valid: false,
          error: `File size ${formatFileSize(file.size)} exceeds the ${MAX_FILE_SIZE_MB} MB limit.`,
        };
      }

      // Empty file check
      if (file.size === 0) {
        return { valid: false, error: 'File is empty.' };
      }

      // Duplicate filename check
      if (existingFilenames.includes(file.name)) {
        return {
          valid: false,
          error: `"${file.name}" has already been uploaded. The backend will rename duplicates, but consider renaming first.`,
        };
      }

      return { valid: true };
    },
    [existingFilenames]
  );

  /**
   * Uploads a single file with progress tracking.
   * Wrapped in its own function for sequential processing.
   */
  const uploadFile = useCallback(
    async (uploadItem) => {
      const abortController = new AbortController();

      // Store the abort controller so we can cancel if needed
      setUploadQueue((prev) =>
        prev.map((item) =>
          item.id === uploadItem.id
            ? { ...item, status: 'uploading', abortController }
            : item
        )
      );

      try {
        const response = await documentsAPI.upload(chatbotId, uploadItem.file, {
          onUploadProgress: (progressEvent) => {
            const percent = progressEvent.total
              ? Math.round((progressEvent.loaded / progressEvent.total) * 100)
              : 0;
            setUploadQueue((prev) =>
              prev.map((item) =>
                item.id === uploadItem.id
                  ? { ...item, progress: percent }
                  : item
              )
            );
          },
          signal: abortController.signal,
        });

        // Mark as completed
        setUploadQueue((prev) =>
          prev.map((item) =>
            item.id === uploadItem.id
              ? { ...item, status: 'completed', progress: 100 }
              : item
          )
        );

        // Notify parent
        onUploadComplete?.(response.data);

        // Auto-remove from queue after a delay
        setTimeout(() => {
          setUploadQueue((prev) => prev.filter((item) => item.id !== uploadItem.id));
        }, 2000);
      } catch (err) {
        if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
          setUploadQueue((prev) =>
            prev.map((item) =>
              item.id === uploadItem.id
                ? { ...item, status: 'cancelled', error: 'Upload cancelled' }
                : item
            )
          );
          return;
        }

        const errorMessage =
          err.response?.data?.detail || 'Upload failed. Please try again.';
        const safeError = typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage);

        setUploadQueue((prev) =>
          prev.map((item) =>
            item.id === uploadItem.id
              ? { ...item, status: 'error', error: safeError }
              : item
          )
        );

        onUploadError?.(uploadItem.file.name, safeError);
      }
    },
    [chatbotId, onUploadComplete, onUploadError]
  );

  /**
   * Processes an array of File objects: validates each, rejects invalid ones
   * immediately, and sequentially uploads valid ones.
   */
  const processFiles = useCallback(
    async (files) => {
      const fileArray = Array.from(files);
      const validItems = [];

      for (const file of fileArray) {
        const validation = validateFile(file);
        const id = ++uploadIdRef.current;

        if (!validation.valid) {
          // Show rejected file briefly in the queue with error
          setUploadQueue((prev) => [
            ...prev,
            {
              id,
              file,
              progress: 0,
              status: 'error',
              error: validation.error,
              abortController: null,
            },
          ]);
          // Auto-remove rejected files after 5 seconds
          setTimeout(() => {
            setUploadQueue((prev) => prev.filter((item) => item.id !== id));
          }, 5000);
        } else {
          const item = {
            id,
            file,
            progress: 0,
            status: 'pending',
            error: null,
            abortController: null,
          };
          validItems.push(item);
          setUploadQueue((prev) => [...prev, item]);
        }
      }

      // Sequential uploads to avoid overwhelming the backend
      for (const item of validItems) {
        await uploadFile(item);
      }
    },
    [validateFile, uploadFile]
  );

  /**
   * Cancel an in-progress upload.
   */
  const handleCancelUpload = useCallback((uploadId) => {
    setUploadQueue((prev) => {
      const item = prev.find((i) => i.id === uploadId);
      if (item?.abortController) {
        item.abortController.abort();
      }
      return prev.filter((i) => i.id !== uploadId);
    });
  }, []);

  /**
   * Remove a completed/errored item from the queue.
   */
  const handleDismiss = useCallback((uploadId) => {
    setUploadQueue((prev) => prev.filter((item) => item.id !== uploadId));
  }, []);

  // --- Drag & drop handlers ---
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current++;
    if (e.dataTransfer.items?.length > 0) {
      setIsDragOver(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) {
      setIsDragOver(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    dragCounterRef.current = 0;

    if (disabled) return;

    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles?.length > 0) {
      processFiles(droppedFiles);
    }
  };

  const handleFileInputChange = (e) => {
    const selectedFiles = e.target.files;
    if (selectedFiles?.length > 0) {
      processFiles(selectedFiles);
    }
    // Reset input so the same file can be re-selected
    e.target.value = '';
  };

  const handleBrowseClick = () => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  };

  const handleKeyDown = (e) => {
    if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  };

  return (
    <div className="upload-zone-wrapper">
      {/* Drop zone */}
      <div
        className={`upload-zone ${isDragOver ? 'drag-over' : ''} ${disabled ? 'disabled' : ''}`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={handleBrowseClick}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="Upload documents by dragging files here or clicking to browse"
        aria-disabled={disabled}
        id="document-upload-zone"
      >
        <div className="upload-zone-icon">
          <Upload size={24} />
        </div>
        <div className="upload-zone-text">
          <span className="upload-zone-title">
            {isDragOver ? 'Drop files here' : 'Drag & drop files here'}
          </span>
          <span className="upload-zone-subtitle">
            or <span className="upload-zone-browse">browse files</span>
          </span>
        </div>
        <div className="upload-zone-hint">
          PDF, DOCX, TXT, CSV — up to {MAX_FILE_SIZE_MB} MB each
        </div>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.csv"
          onChange={handleFileInputChange}
          className="sr-only"
          tabIndex={-1}
          aria-hidden="true"
        />
      </div>

      {/* Upload queue */}
      {uploadQueue.length > 0 && (
        <div className="upload-queue" role="list" aria-label="Upload progress">
          {uploadQueue.map((item) => (
            <div
              key={item.id}
              className={`upload-item upload-item-${item.status}`}
              role="listitem"
            >
              <div className="upload-item-icon">
                {item.status === 'error' || item.status === 'cancelled' ? (
                  <AlertCircle size={16} />
                ) : item.status === 'completed' ? (
                  <CheckCircle2 size={16} />
                ) : (
                  <FileText size={16} />
                )}
              </div>
              <div className="upload-item-info">
                <div className="upload-item-name">{item.file.name}</div>
                {item.status === 'error' || item.status === 'cancelled' ? (
                  <div className="upload-item-error">{item.error}</div>
                ) : item.status === 'completed' ? (
                  <div className="upload-item-success">Uploaded successfully</div>
                ) : (
                  <div className="upload-item-progress-bar">
                    <div
                      className="upload-item-progress-fill"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                )}
              </div>
              <div className="upload-item-meta">
                <span className="upload-item-size">{formatFileSize(item.file.size)}</span>
              </div>
              <button
                className="upload-item-action"
                onClick={(e) => {
                  e.stopPropagation();
                  if (item.status === 'uploading') {
                    handleCancelUpload(item.id);
                  } else {
                    handleDismiss(item.id);
                  }
                }}
                aria-label={item.status === 'uploading' ? 'Cancel upload' : 'Dismiss'}
                title={item.status === 'uploading' ? 'Cancel upload' : 'Dismiss'}
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
