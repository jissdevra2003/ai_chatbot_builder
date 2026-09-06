import io
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentChunk, DocumentStatusEnum


# --- Helper: signup + login + get token + create chatbot ---
def _setup_chatbot(client: TestClient, email: str = "docuser@test.com"):
    payload = {"email": email, "password": "Pass123!", "full_name": "Doc User", "org_name": "Doc Corp"}
    client.post("/api/v1/auth/signup", json=payload)
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Pass123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    bot_resp = client.post("/api/v1/chatbots/", headers=headers, json={"name": "KB Bot"})
    chatbot_id = bot_resp.json()["id"]
    return headers, chatbot_id


class TestDocumentUpload:
    """Tests for document upload API — Background worker task is mocked."""

    @patch("app.worker.background_worker.document_worker_queue.submit_task", return_value="bgtask-test-id")
    @patch("app.services.document_service._detect_mime_type", return_value="text/plain")
    def test_upload_txt_document(self, mock_mime, mock_submit, client: TestClient, db_session: Session):
        """Upload returns immediately with status=queued (Background worker processes async)."""
        headers, chatbot_id = _setup_chatbot(client, "txtupl@test.com")

        txt_content = "This is a test document.\n\nIt has multiple paragraphs."
        file = io.BytesIO(txt_content.encode("utf-8"))

        resp = client.post(
            f"/api/v1/chatbots/{chatbot_id}/documents/upload",
            headers=headers,
            files={"file": ("test_doc.txt", file, "text/plain")}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "test_doc.txt"
        assert data["file_type"] == "txt"
        assert data["status"] == "queued"  # Now async — returns queued, not completed
        assert data["error_message"] is None
        mock_submit.assert_called_once()

    @patch("app.worker.background_worker.document_worker_queue.submit_task", return_value="bgtask-test-id")
    @patch("app.services.document_service._detect_mime_type", return_value=None)
    def test_upload_unsupported_file_type(self, mock_mime, mock_submit, client: TestClient, db_session: Session):
        headers, chatbot_id = _setup_chatbot(client, "unsup@test.com")

        file = io.BytesIO(b"binary data")
        resp = client.post(
            f"/api/v1/chatbots/{chatbot_id}/documents/upload",
            headers=headers,
            files={"file": ("test.exe", file, "application/octet-stream")}
        )
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.json()["detail"]
        mock_submit.assert_not_called()

    @patch("app.worker.background_worker.document_worker_queue.submit_task", return_value="bgtask-test-id")
    @patch("app.services.document_service._detect_mime_type", return_value="text/plain")
    def test_upload_empty_file(self, mock_mime, mock_submit, client: TestClient, db_session: Session):
        headers, chatbot_id = _setup_chatbot(client, "empty@test.com")

        file = io.BytesIO(b"")
        resp = client.post(
            f"/api/v1/chatbots/{chatbot_id}/documents/upload",
            headers=headers,
            files={"file": ("empty.txt", file, "text/plain")}
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()
        mock_submit.assert_not_called()

    @patch("app.worker.background_worker.document_worker_queue.submit_task", return_value="bgtask-test-id")
    @patch("app.services.document_service._detect_mime_type", return_value="text/plain")
    def test_list_documents(self, mock_mime, mock_submit, client: TestClient, db_session: Session):
        headers, chatbot_id = _setup_chatbot(client, "listdoc@test.com")

        # Upload 2 documents
        for name in ["doc1.txt", "doc2.txt"]:
            file = io.BytesIO(b"Some content for testing")
            client.post(
                f"/api/v1/chatbots/{chatbot_id}/documents/upload",
                headers=headers,
                files={"file": (name, file, "text/plain")}
            )

        resp = client.get(f"/api/v1/chatbots/{chatbot_id}/documents/", headers=headers)
        assert resp.status_code == 200
        docs = resp.json()
        assert len(docs) == 2

    @patch("app.worker.background_worker.document_worker_queue.submit_task", return_value="bgtask-test-id")
    @patch("app.services.document_service._detect_mime_type", return_value="text/plain")
    def test_get_document_detail(self, mock_mime, mock_submit, client: TestClient, db_session: Session):
        headers, chatbot_id = _setup_chatbot(client, "detaildoc@test.com")

        file = io.BytesIO(b"Detail test content here")
        upload_resp = client.post(
            f"/api/v1/chatbots/{chatbot_id}/documents/upload",
            headers=headers,
            files={"file": ("detail.txt", file, "text/plain")}
        )
        doc_id = upload_resp.json()["id"]

        resp = client.get(f"/api/v1/chatbots/{chatbot_id}/documents/{doc_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["filename"] == "detail.txt"
        assert resp.json()["status"] == "queued"
        assert "processing_stage" in resp.json()
        assert "progress" in resp.json()

    @patch("app.worker.background_worker.document_worker_queue.submit_task", return_value="bgtask-test-id")
    @patch("app.services.document_service._detect_mime_type", return_value="text/plain")
    def test_delete_document(self, mock_mime, mock_submit, client: TestClient, db_session: Session):
        headers, chatbot_id = _setup_chatbot(client, "deldoc@test.com")

        file = io.BytesIO(b"Content to delete")
        upload_resp = client.post(
            f"/api/v1/chatbots/{chatbot_id}/documents/upload",
            headers=headers,
            files={"file": ("todelete.txt", file, "text/plain")}
        )
        doc_id = upload_resp.json()["id"]

        # Delete
        resp = client.delete(f"/api/v1/chatbots/{chatbot_id}/documents/{doc_id}", headers=headers)
        assert resp.status_code == 204

        # Verify deleted
        get_resp = client.get(f"/api/v1/chatbots/{chatbot_id}/documents/{doc_id}", headers=headers)
        assert get_resp.status_code == 404


class TestChunkingLogic:
    """Tests for the chunking algorithm (no Celery required)."""

    def test_chunk_text_basic(self):
        from app.worker.chunking import chunk_text
        text = "Hello world. " * 200  # ~2600 chars
        chunks = chunk_text(text, chunk_size=500, overlap=100)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 600  # Allow some tolerance

    def test_chunk_text_short_text(self):
        from app.worker.chunking import chunk_text
        chunks = chunk_text("Short text", chunk_size=1000, overlap=200)
        assert len(chunks) == 1
        assert chunks[0] == "Short text"

    def test_chunk_text_empty(self):
        from app.worker.chunking import chunk_text
        assert chunk_text("", chunk_size=1000, overlap=200) == []
        assert chunk_text("   ", chunk_size=1000, overlap=200) == []


class TestExtractionLogic:
    """Tests for file extraction (no Celery required)."""

    def test_extract_txt(self, tmp_path):
        from app.worker.extraction import extract_txt
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world. This is a test file.", encoding="utf-8")

        results = list(extract_txt(str(test_file)))
        assert len(results) >= 1
        full_text = " ".join(text for _, text in results)
        assert "Hello world" in full_text

    def test_extract_csv(self, tmp_path):
        from app.worker.extraction import extract_csv
        test_file = tmp_path / "test.csv"
        test_file.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")

        results = list(extract_csv(str(test_file)))
        assert len(results) >= 1
        full_text = " ".join(text for _, text in results)
        assert "Alice" in full_text
        assert "Bob" in full_text
