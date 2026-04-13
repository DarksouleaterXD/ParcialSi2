"""Tests CU06 — API /api/admin/talleres."""


def _login(client, email: str = "login-test@example.com", password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _taller_body(**kwargs: object) -> dict:
    body: dict = {
        "nombre": "Taller Test",
        "direccion": "Calle Falsa 123",
        "latitud": "-17.78629",
        "longitud": "-63.18117",
        "telefono": "70001234",
        "email": "taller@test.com",
        "capacidad_maxima": 8,
        "horario_atencion": "Lun–Vie 8:00–18:00",
    }
    body.update(kwargs)
    return body


def test_cliente_no_accede_talleres(client):
    token = _login(client, "cliente-test@example.com", "clave-valida-123")
    res = client.get("/api/admin/talleres", headers=_hdr(token))
    assert res.status_code == 403


def test_admin_crear_listar_y_desactivar(client):
    token = _login(client)
    r = client.post("/api/admin/talleres", json=_taller_body(nombre="CU6 Alpha"), headers=_hdr(token))
    assert r.status_code == 201
    row = r.json()
    assert row["nombre"] == "CU6 Alpha"
    assert row["disponibilidad"] is True
    assert row["capacidad_maxima"] == 8
    tid = row["id"]

    lst = client.get("/api/admin/talleres", headers=_hdr(token))
    assert lst.status_code == 200
    assert lst.json()["total"] >= 1

    one = client.get(f"/api/admin/talleres/{tid}", headers=_hdr(token))
    assert one.status_code == 200
    assert one.json()["id"] == tid

    off = client.post(f"/api/admin/talleres/{tid}/desactivar", headers=_hdr(token))
    assert off.status_code == 200
    assert off.json()["disponibilidad"] is False

    filt = client.get("/api/admin/talleres?activo=false", headers=_hdr(token))
    assert filt.status_code == 200
    assert any(x["id"] == tid for x in filt.json()["items"])

    on = client.post(f"/api/admin/talleres/{tid}/reactivar", headers=_hdr(token))
    assert on.status_code == 200
    assert on.json()["disponibilidad"] is True


def test_crear_latitud_invalida_422(client):
    token = _login(client)
    body = _taller_body(latitud="91", longitud="0")
    res = client.post("/api/admin/talleres", json=body, headers=_hdr(token))
    assert res.status_code == 422


def test_patch_solo_latitud_422(client):
    token = _login(client)
    r = client.post("/api/admin/talleres", json=_taller_body(nombre="GPS Par"), headers=_hdr(token))
    tid = r.json()["id"]
    res = client.patch(f"/api/admin/talleres/{tid}", json={"latitud": "-17.8"}, headers=_hdr(token))
    assert res.status_code == 422
