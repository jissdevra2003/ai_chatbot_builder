"""
Tests for Phase 3: Chat & Conversation System.
Gemini API is mocked to avoid real API calls during testing.
"""
import json
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient


# --- Helper Functions ---

def signup_and_login(client: TestClient, email="chatuser@test.com") -> dict:
    """Creates a user, logs in, and returns auth headers."""
    client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "testpass123",
        "full_name": "Chat Tester",
        "org_name": "Chat Test Org"
    })
    login_resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "testpass123"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_chatbot(client: TestClient, headers: dict) -> dict:
    """Creates a chatbot and returns its data."""
    resp = client.post("/api/v1/chatbots/", json={
        "name": "Test Chat Bot",
        "system_prompt": "You are a helpful test assistant.",
        "model_name": "gemini-2.0-flash",
        "temperature": 0.5,
    }, headers=headers)
    assert resp.status_code == 201
    return resp.json()


# Mock for AIService.generate_response
def mock_generate_response(*args, **kwargs):
    """Returns a fake AI response for testing."""
    return ("This is a test response from the AI.", 150)


# --- Tests ---

class TestSendMessage:
    """Tests for POST /api/v1/chatbots/{chatbot_id}/chat"""

    @patch("app.services.chat_service.AIService.generate_response", side_effect=mock_generate_response)
    def test_send_message_creates_conversation(self, mock_ai, client: TestClient):
        """Sending a message should create a new conversation and return a response."""
        headers = signup_and_login(client)
        chatbot = create_chatbot(client, headers)

        resp = client.post(
            f"/api/v1/chatbots/{chatbot['id']}/chat",
            json={"message": "Hello, what can you do?"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["message"] == "This is a test response from the AI."
        assert data["session_id"]  # Should have a session_id
        assert data["conversation_id"]  # Should have a conversation_id
        assert data["tokens_used"] == 150
        assert data["response_time_ms"] is not None
        mock_ai.assert_called_once()

    @patch("app.services.chat_service.AIService.generate_response", side_effect=mock_generate_response)
    def test_session_id_continues_conversation(self, mock_ai, client: TestClient):
        """Sending messages with the same session_id should continue the same conversation."""
        headers = signup_and_login(client)
        chatbot = create_chatbot(client, headers)

        # First message
        resp1 = client.post(
            f"/api/v1/chatbots/{chatbot['id']}/chat",
            json={"message": "First message"},
            headers=headers,
        )
        assert resp1.status_code == 200
        session_id = resp1.json()["session_id"]
        conversation_id = resp1.json()["conversation_id"]

        # Second message with same session_id
        resp2 = client.post(
            f"/api/v1/chatbots/{chatbot['id']}/chat",
            json={"message": "Second message", "session_id": session_id},
            headers=headers,
        )
        assert resp2.status_code == 200
        assert resp2.json()["session_id"] == session_id
        assert resp2.json()["conversation_id"] == conversation_id

    @patch("app.services.chat_service.AIService.generate_response", side_effect=mock_generate_response)
    def test_new_session_id_creates_new_conversation(self, mock_ai, client: TestClient):
        """Different session_ids should create different conversations."""
        headers = signup_and_login(client)
        chatbot = create_chatbot(client, headers)

        resp1 = client.post(
            f"/api/v1/chatbots/{chatbot['id']}/chat",
            json={"message": "Hello", "session_id": "session-aaa"},
            headers=headers,
        )
        resp2 = client.post(
            f"/api/v1/chatbots/{chatbot['id']}/chat",
            json={"message": "Hello", "session_id": "session-bbb"},
            headers=headers,
        )

        assert resp1.json()["conversation_id"] != resp2.json()["conversation_id"]

    def test_send_message_invalid_chatbot(self, client: TestClient):
        """Sending message to non-existent chatbot should return 404."""
        headers = signup_and_login(client)
        resp = client.post(
            "/api/v1/chatbots/nonexistent-id/chat",
            json={"message": "Hello"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_send_empty_message(self, client: TestClient):
        """Empty message should return 422 validation error."""
        headers = signup_and_login(client)
        chatbot = create_chatbot(client, headers)

        resp = client.post(
            f"/api/v1/chatbots/{chatbot['id']}/chat",
            json={"message": ""},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_send_message_unauthenticated(self, client: TestClient):
        """Sending message without auth should return 401."""
        resp = client.post(
            "/api/v1/chatbots/some-id/chat",
            json={"message": "Hello"},
        )
        assert resp.status_code == 401


class TestConversations:
    """Tests for conversation listing, detail, and deletion endpoints."""

    @patch("app.services.chat_service.AIService.generate_response", side_effect=mock_generate_response)
    def test_list_conversations(self, mock_ai, client: TestClient):
        """Should list all conversations for a chatbot."""
        headers = signup_and_login(client)
        chatbot = create_chatbot(client, headers)

        # Create two conversations
        client.post(
            f"/api/v1/chatbots/{chatbot['id']}/chat",
            json={"message": "Conv 1", "session_id": "sess-1"},
            headers=headers,
        )
        client.post(
            f"/api/v1/chatbots/{chatbot['id']}/chat",
            json={"message": "Conv 2", "session_id": "sess-2"},
            headers=headers,
        )

        resp = client.get(
            f"/api/v1/chatbots/{chatbot['id']}/conversations",
            headers=headers,
        )
        assert resp.status_code == 200
        conversations = resp.json()
        assert len(conversations) == 2

    @patch("app.services.chat_service.AIService.generate_response", side_effect=mock_generate_response)
    def test_get_conversation_detail(self, mock_ai, client: TestClient):
        """Should return conversation with all messages."""
        headers = signup_and_login(client)
        chatbot = create_chatbot(client, headers)

        # Send a message
        chat_resp = client.post(
            f"/api/v1/chatbots/{chatbot['id']}/chat",
            json={"message": "Tell me about something"},
            headers=headers,
        )
        conversation_id = chat_resp.json()["conversation_id"]

        # Get conversation detail
        resp = client.get(
            f"/api/v1/conversations/{conversation_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == conversation_id
        assert len(data["messages"]) == 2  # 1 user + 1 bot
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "Tell me about something"
        assert data["messages"][1]["role"] == "bot"
        assert data["message_count"] == 2

    @patch("app.services.chat_service.AIService.generate_response", side_effect=mock_generate_response)
    def test_get_conversation_not_found(self, mock_ai, client: TestClient):
        """Getting non-existent conversation should return 404."""
        headers = signup_and_login(client)
        resp = client.get(
            "/api/v1/conversations/nonexistent-id",
            headers=headers,
        )
        assert resp.status_code == 404

    @patch("app.services.chat_service.AIService.generate_response", side_effect=mock_generate_response)
    def test_delete_conversation(self, mock_ai, client: TestClient):
        """Deleting a conversation should remove it and all messages."""
        headers = signup_and_login(client)
        chatbot = create_chatbot(client, headers)

        # Create a conversation
        chat_resp = client.post(
            f"/api/v1/chatbots/{chatbot['id']}/chat",
            json={"message": "Delete me later"},
            headers=headers,
        )
        conversation_id = chat_resp.json()["conversation_id"]

        # Delete it
        del_resp = client.delete(
            f"/api/v1/conversations/{conversation_id}",
            headers=headers,
        )
        assert del_resp.status_code == 204

        # Verify it's gone
        get_resp = client.get(
            f"/api/v1/conversations/{conversation_id}",
            headers=headers,
        )
        assert get_resp.status_code == 404

    @patch("app.services.chat_service.AIService.generate_response", side_effect=mock_generate_response)
    def test_conversation_title_auto_set(self, mock_ai, client: TestClient):
        """Conversation title should auto-set from first user message."""
        headers = signup_and_login(client)
        chatbot = create_chatbot(client, headers)

        chat_resp = client.post(
            f"/api/v1/chatbots/{chatbot['id']}/chat",
            json={"message": "What is your return policy?"},
            headers=headers,
        )
        conversation_id = chat_resp.json()["conversation_id"]

        # Check conversation title
        resp = client.get(
            f"/api/v1/conversations/{conversation_id}",
            headers=headers,
        )
        assert resp.json()["title"] == "What is your return policy?"

    @patch("app.services.chat_service.AIService.generate_response", side_effect=mock_generate_response)
    def test_multi_turn_conversation(self, mock_ai, client: TestClient):
        """Multiple messages in same session should accumulate in one conversation."""
        headers = signup_and_login(client)
        chatbot = create_chatbot(client, headers)

        session_id = "multi-turn-test"

        # Send 3 messages
        for i in range(3):
            client.post(
                f"/api/v1/chatbots/{chatbot['id']}/chat",
                json={"message": f"Message {i+1}", "session_id": session_id},
                headers=headers,
            )

        # Get conversation detail — should have 6 messages (3 user + 3 bot)
        conversations = client.get(
            f"/api/v1/chatbots/{chatbot['id']}/conversations",
            headers=headers,
        ).json()
        assert len(conversations) == 1
        assert conversations[0]["message_count"] == 6

        conv_detail = client.get(
            f"/api/v1/conversations/{conversations[0]['id']}",
            headers=headers,
        ).json()
        assert len(conv_detail["messages"]) == 6
