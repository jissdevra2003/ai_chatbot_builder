from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.membership import Membership, RoleEnum
from app.models.invitation import Invitation, InvitationStatusEnum


def test_create_invitation_success(client: TestClient, db_session: Session):
    # 1. Owner signs up
    signup_resp = client.post("/api/v1/auth/signup", json={
        "email": "owner_inviter@example.com",
        "password": "Password123!",
        "full_name": "Org Owner",
        "org_name": "Inviter Corp"
    })
    assert signup_resp.status_code == 201

    login_resp = client.post("/api/v1/auth/login", json={
        "email": "owner_inviter@example.com",
        "password": "Password123!"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Invite a new ADMIN
    invite_resp = client.post("/api/v1/auth/../invitations/", headers=headers, json={
        "email": "new_admin@example.com",
        "role": "admin"
    })
    assert invite_resp.status_code == 201
    invite_data = invite_resp.json()
    assert invite_data["email"] == "new_admin@example.com"
    assert invite_data["role"] == "admin"
    assert invite_data["status"] == "pending"
    assert "token" in invite_data


def test_cannot_invite_as_owner(client: TestClient):
    signup_resp = client.post("/api/v1/auth/signup", json={
        "email": "owner_fail@example.com",
        "password": "Password123!",
        "full_name": "Owner User"
    })
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "owner_fail@example.com",
        "password": "Password123!"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    invite_resp = client.post("/api/v1/invitations/", headers=headers, json={
        "email": "illegal_owner@example.com",
        "role": "owner"
    })
    assert invite_resp.status_code == 400
    assert "Cannot invite users with the OWNER role" in invite_resp.json()["detail"]


def test_accept_invitation_creates_user_and_membership(client: TestClient, db_session: Session):
    # 1. Owner creates invitation
    client.post("/api/v1/auth/signup", json={
        "email": "owner_host@example.com",
        "password": "Password123!",
        "full_name": "Host Owner",
        "org_name": "Host Company"
    })
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "owner_host@example.com",
        "password": "Password123!"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    invite_resp = client.post("/api/v1/invitations/", headers=headers, json={
        "email": "joined_admin@example.com",
        "role": "admin"
    })
    invite_token = invite_resp.json()["token"]

    # 2. Accept invitation as a new user
    accept_resp = client.post("/api/v1/invitations/accept", json={
        "token": invite_token,
        "password": "SecurePassword123!",
        "full_name": "Joined Admin User"
    })
    assert accept_resp.status_code == 200
    assert accept_resp.json()["role"] == "admin"

    # 3. Verify DB state
    joined_user = db_session.query(User).filter_by(email="joined_admin@example.com").first()
    assert joined_user is not None
    assert joined_user.full_name == "Joined Admin User"

    membership = db_session.query(Membership).filter_by(user_id=joined_user.id).first()
    assert membership is not None
    assert membership.role == RoleEnum.ADMIN
