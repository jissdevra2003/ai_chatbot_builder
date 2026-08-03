from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership, RoleEnum


def test_signup_creates_user_org_membership_transactionally(client: TestClient, db_session: Session):
    """Test signup creates user, auto-creates organization, and assigns owner role in one transaction."""
    payload = {
        "email": "jiss@example.com",
        "password": "SecurePassword123!",
        "full_name": "Jiss Dev",
        "org_name": "Jiss Corp"
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "jiss@example.com"
    assert data["full_name"] == "Jiss Dev"
    assert "id" in data

    # Verify DB state directly
    user = db_session.query(User).filter_by(email="jiss@example.com").first()
    assert user is not None

    membership = db_session.query(Membership).filter_by(user_id=user.id).first()
    assert membership is not None
    assert membership.role == RoleEnum.OWNER

    org = db_session.query(Organization).filter_by(id=membership.org_id).first()
    assert org is not None
    assert org.name == "Jiss Corp"


def test_signup_default_workspace_name(client: TestClient, db_session: Session):
    """Test signup without explicit org_name defaults to '{full_name}'s Workspace'."""
    payload = {
        "email": "alice@example.com",
        "password": "Password123!",
        "full_name": "Alice Smith"
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201

    user = db_session.query(User).filter_by(email="alice@example.com").first()
    membership = db_session.query(Membership).filter_by(user_id=user.id).first()
    org = db_session.query(Organization).filter_by(id=membership.org_id).first()

    assert org.name == "Alice Smith's Workspace"


def test_duplicate_email_signup_fails(client: TestClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "full_name": "User One"
    }
    resp1 = client.post("/api/v1/auth/signup", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/auth/signup", json=payload)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]


def test_login_success(client: TestClient):
    # 1. Signup
    client.post("/api/v1/auth/signup", json={
        "email": "loginuser@example.com",
        "password": "SecretPassword123!",
        "full_name": "Login User"
    })

    # 2. Login
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "loginuser@example.com",
        "password": "SecretPassword123!"
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


def test_login_invalid_password_fails(client: TestClient):
    client.post("/api/v1/auth/signup", json={
        "email": "wrongpwd@example.com",
        "password": "CorrectPassword123!",
        "full_name": "Wrong Pwd User"
    })

    login_resp = client.post("/api/v1/auth/login", json={
        "email": "wrongpwd@example.com",
        "password": "WrongPassword123!"
    })
    assert login_resp.status_code == 401


def test_get_me_authenticated_user(client: TestClient):
    # Signup & Login
    client.post("/api/v1/auth/signup", json={
        "email": "meuser@example.com",
        "password": "SecretPassword123!",
        "full_name": "Me User",
        "org_name": "Me Innovations"
    })

    login_resp = client.post("/api/v1/auth/login", json={
        "email": "meuser@example.com",
        "password": "SecretPassword123!"
    })
    token = login_resp.json()["access_token"]

    # Call /me endpoint with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()

    assert me_data["user"]["email"] == "meuser@example.com"
    assert me_data["user"]["full_name"] == "Me User"
    assert me_data["active_organization"]["name"] == "Me Innovations"
    assert me_data["role"] == "owner"


def test_get_me_unauthenticated_fails(client: TestClient):
    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 401
