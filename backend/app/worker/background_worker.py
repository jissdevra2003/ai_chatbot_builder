"""
Native background worker queue for document processing.

Uses Python's built-in ThreadPoolExecutor with bounded concurrency (max_workers=2)
to ensure processing large files (up to 500 MB) is memory-safe, non-blocking,
and doesn't overload CPU or RAM.
"""
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

logger = logging.getLogger(__name__)


class DocumentWorkerQueue:
    def __init__(self, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="doc_worker_"
        )
        self._active_tasks: Dict[str, str] = {}
        self._lock = threading.Lock()

    def submit_task(self, document_id: str) -> str:
        """
        Enqueues a document for background processing.
        Returns a unique task identifier string.
        """
        task_id = f"bgtask-{document_id}"
        
        with self._lock:
            self._active_tasks[document_id] = task_id

        logger.info(f"Submitting document {document_id} to background worker queue (task_id={task_id})")
        self.executor.submit(self._run_task_wrapper, document_id, task_id)
        return task_id

    def _run_task_wrapper(self, document_id: str, task_id: str):
        """Executes process_document_task and handles cleanup/logging."""
        try:
            from app.worker.tasks import process_document_task
            logger.info(f"Starting background worker task {task_id} for document {document_id}")
            result = process_document_task(document_id)
            logger.info(f"Completed background task {task_id}: {result}")
        except Exception as e:
            logger.exception(f"Unhandled error in background task {task_id} for document {document_id}: {e}")
        finally:
            with self._lock:
                self._active_tasks.pop(document_id, None)


# Global singleton worker queue instance
document_worker_queue = DocumentWorkerQueue(max_workers=2)
