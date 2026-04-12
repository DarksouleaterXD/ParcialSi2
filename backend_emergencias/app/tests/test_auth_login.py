from app.core.security import decode_token


def test_login_ok_returns_bearer_token_and_roles(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "login-test@example.com", "password": "clave-valida-123"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0
    assert "Administrador" in body["roles"]
    assert body["redirect_hint"] == "web"

    payload = decode_token(body["access_token"])
    assert payload["sub"] is not None
    assert payload["type"] == "access"
    assert "Administrador" in payload["roles"]
    assert payload.get("jti")


def test_login_wrong_password_401(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "login-test@example.com", "password": "mala-clave"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Credenciales inválidas"
