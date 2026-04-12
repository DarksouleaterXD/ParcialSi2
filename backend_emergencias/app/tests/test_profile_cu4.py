import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def admin_token(client: TestClient) -> str:
    r = client.post(
        "/api/auth/login",
        json={"email": "login-test@example.com", "password": "clave-valida-123"},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def test_get_me_includes_foto_and_fecha(client: TestClient, admin_token: str) -> None:
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "login-test@example.com"
    assert "foto_perfil" in body
    assert "fecha_registro" in body


def test_patch_profile_updates_and_bitacora(client: TestClient, admin_token: str) -> None:
    r = client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"nombre": "NombreNuevo", "telefono": "099123456", "foto_perfil": "https://example.com/a.jpg"},
    )
    assert r.status_code == 200
    assert r.json()["nombre"] == "NombreNuevo"
    assert r.json()["telefono"] == "099123456"
    assert r.json()["foto_perfil"] == "https://example.com/a.jpg"


def test_change_password_wrong_current(client: TestClient, admin_token: str) -> None:
    r = client.post(
        "/api/auth/me/change-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "password_actual": "no-es-la-clave",
            "password_nueva": "NuevaClave9",
            "password_confirmacion": "NuevaClave9",
        },
    )
    assert r.status_code == 400
    assert "actual" in r.json()["detail"].lower()


def test_change_password_policy_short(client: TestClient, admin_token: str) -> None:
    r = client.post(
        "/api/auth/me/change-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "password_actual": "clave-valida-123",
            "password_nueva": "Ab1",
            "password_confirmacion": "Ab1",
        },
    )
    assert r.status_code == 400


def test_change_password_mismatch_confirm(client: TestClient, admin_token: str) -> None:
    r = client.post(
        "/api/auth/me/change-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "password_actual": "clave-valida-123",
            "password_nueva": "NuevaClave9",
            "password_confirmacion": "OtraCosa9",
        },
    )
    assert r.status_code == 400


def test_change_password_ok_then_login_with_new(client: TestClient, admin_token: str) -> None:
    r = client.post(
        "/api/auth/me/change-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "password_actual": "clave-valida-123",
            "password_nueva": "OtraValida9",
            "password_confirmacion": "OtraValida9",
        },
    )
    assert r.status_code == 204
    bad = client.post(
        "/api/auth/login",
        json={"email": "login-test@example.com", "password": "clave-valida-123"},
    )
    assert bad.status_code == 401
    ok = client.post(
        "/api/auth/login",
        json={"email": "login-test@example.com", "password": "OtraValida9"},
    )
    assert ok.status_code == 200
