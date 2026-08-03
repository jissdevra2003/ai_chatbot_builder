import io
import os
from unittest.mock import patch
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
    def test_upload_txt_document(self, client: TestClient, db_session: Session):
        headers, chatbot_id = _setup_chatbot(client, "txtupl@test.com")

        txt_content = "This is a test document.\n\nIt has multiple paragraphs.\n\nEach paragraph will become part of the knowledge base."
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
        assert data["status"] == "completed"
        assert data["chunk_count"] >= 1
        assert data["error_message"] is None

    def test_upload_unsupported_file_type(self, client: TestClient, db_session: Session):
        headers, chatbot_id = _setup_chatbot(client, "unsup@test.com")

        file = io.BytesIO(b"binary data")
        resp = client.post(
            f"/api/v1/chatbots/{chatbot_id}/documents/upload",
            headers=headers,
            files={"file": ("test.exe", file, "application/octet-stream")}
        )
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.json()["detail"]

    def test_list_documents(self, client: TestClient, db_session: Session):
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

    def test_get_document_detail(self, client: TestClient, db_session: Session):
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

    def test_get_document_chunks(self, client: TestClient, db_session: Session):
        headers, chatbot_id = _setup_chatbot(client, "chunkdoc@test.com")

        # Upload a document with enough content to create at least 1 chunk
        content = "This is a test paragraph with enough content to create chunks. " * 20
        file = io.BytesIO(content.encode("utf-8"))
        upload_resp = client.post(
            f"/api/v1/chatbots/{chatbot_id}/documents/upload",
            headers=headers,
            files={"file": ("chunks.txt", file, "text/plain")}
        )
        doc_id = upload_resp.json()["id"]

        resp = client.get(f"/api/v1/chatbots/{chatbot_id}/documents/{doc_id}/chunks", headers=headers)
        assert resp.status_code == 200
        chunks = resp.json()
        assert len(chunks) >= 1
        assert "content" in chunks[0]
        assert "chunk_index" in chunks[0]
        assert chunks[0]["chunk_index"] == 0

    def test_delete_document(self, client: TestClient, db_session: Session):
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
    def test_chunk_text_basic(self):
        from app.services.chunking import chunk_text
        text = "Hello world. " * 200  # ~2600 chars
        chunks = chunk_text(text, chunk_size=500, overlap=100)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 600  # Allow some tolerance

    def test_chunk_text_short_text(self):
        from app.services.chunking import chunk_text
        chunks = chunk_text("Short text", chunk_size=1000, overlap=200)
        assert len(chunks) == 1
        assert chunks[0] == "Short text"

    def test_chunk_text_empty(self):
        from app.services.chunking import chunk_text
        assert chunk_text("", chunk_size=1000, overlap=200) == []
        assert chunk_text("   ", chunk_size=1000, overlap=200) == []
