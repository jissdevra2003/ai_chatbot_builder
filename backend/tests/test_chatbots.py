from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.chatbot import Chatbot
from app.models.membership import RoleEnum


# --- Helper: signup + login + get token ---
def _create_authenticated_user(client: TestClient, email: str, password: str, full_name: str, org_name: str = None):
    payload = {"email": email, "password": password, "full_name": full_name}
    if org_name:
        payload["org_name"] = org_name
    client.post("/api/v1/auth/signup", json=payload)
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestChatbotCRUD:
    def test_create_chatbot(self, client: TestClient, db_session: Session):
        headers = _create_authenticated_user(client, "botowner@test.com", "Pass123!", "Bot Owner", "Bot Corp")

        resp = client.post("/api/v1/chatbots/", headers=headers, json={
            "name": "Sales Bot",
            "description": "Handles product inquiries",
            "system_prompt": "You are a sales assistant for Bot Corp.",
            "model_name": "gemini-2.0-flash",
            "temperature": 0.5
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Sales Bot"
        assert data["description"] == "Handles product inquiries"
        assert data["system_prompt"] == "You are a sales assistant for Bot Corp."
        assert data["model_name"] == "gemini-2.0-flash"
        assert data["temperature"] == 0.5
        assert data["api_key"].startswith("cb_")
        assert "id" in data
        assert "org_id" in data

    def test_create_chatbot_with_defaults(self, client: TestClient, db_session: Session):
        headers = _create_authenticated_user(client, "defaults@test.com", "Pass123!", "Default User")

        resp = client.post("/api/v1/chatbots/", headers=headers, json={
            "name": "Default Bot",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["model_name"] == "gemini-2.0-flash"
        assert data["temperature"] == 0.7
        assert data["system_prompt"] == "You are a helpful AI assistant."
        assert data["chunk_size"] == 1000
        assert data["chunk_overlap"] == 200

    def test_list_chatbots(self, client: TestClient, db_session: Session):
        headers = _create_authenticated_user(client, "listbots@test.com", "Pass123!", "List User", "List Corp")

        # Create 2 chatbots
        client.post("/api/v1/chatbots/", headers=headers, json={"name": "Bot A"})
        client.post("/api/v1/chatbots/", headers=headers, json={"name": "Bot B"})

        resp = client.get("/api/v1/chatbots/", headers=headers)
        assert resp.status_code == 200
        bots = resp.json()
        assert len(bots) == 2
        names = {b["name"] for b in bots}
        assert "Bot A" in names
        assert "Bot B" in names

    def test_get_chatbot_by_id(self, client: TestClient, db_session: Session):
        headers = _create_authenticated_user(client, "getbot@test.com", "Pass123!", "Get User")

        create_resp = client.post("/api/v1/chatbots/", headers=headers, json={"name": "Specific Bot"})
        bot_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/chatbots/{bot_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Specific Bot"

    def test_update_chatbot(self, client: TestClient, db_session: Session):
        headers = _create_authenticated_user(client, "updatebot@test.com", "Pass123!", "Update User")

        create_resp = client.post("/api/v1/chatbots/", headers=headers, json={"name": "Old Name"})
        bot_id = create_resp.json()["id"]

        resp = client.patch(f"/api/v1/chatbots/{bot_id}", headers=headers, json={
            "name": "New Name",
            "temperature": 1.2,
            "system_prompt": "Updated prompt"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Name"
        assert data["temperature"] == 1.2
        assert data["system_prompt"] == "Updated prompt"

    def test_delete_chatbot(self, client: TestClient, db_session: Session):
        headers = _create_authenticated_user(client, "deletebot@test.com", "Pass123!", "Delete User")

        create_resp = client.post("/api/v1/chatbots/", headers=headers, json={"name": "To Delete"})
        bot_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/chatbots/{bot_id}", headers=headers)
        assert resp.status_code == 204

        # Verify deleted
        get_resp = client.get(f"/api/v1/chatbots/{bot_id}", headers=headers)
        assert get_resp.status_code == 404

    def test_chatbot_not_found_in_other_org(self, client: TestClient, db_session: Session):
        """Chatbot created in Org A should not be accessible from Org B."""
        headers_a = _create_authenticated_user(client, "orgA@test.com", "Pass123!", "Org A User", "Org A")
        headers_b = _create_authenticated_user(client, "orgB@test.com", "Pass123!", "Org B User", "Org B")

        create_resp = client.post("/api/v1/chatbots/", headers=headers_a, json={"name": "Org A Bot"})
        bot_id = create_resp.json()["id"]

        # Org B tries to access Org A's chatbot
        resp = client.get(f"/api/v1/chatbots/{bot_id}", headers=headers_b)
        assert resp.status_code == 404

    def test_chatbot_not_found_returns_404(self, client: TestClient, db_session: Session):
        headers = _create_authenticated_user(client, "notfound@test.com", "Pass123!", "NF User")
        resp = client.get("/api/v1/chatbots/nonexistent-id", headers=headers)
        assert resp.status_code == 404
