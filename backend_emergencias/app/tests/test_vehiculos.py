"""Tests de la API /api/vehiculos."""

from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.incidentes_servicios.models import Incidente
from app.modules.usuario_autenticacion.models import Vehiculo


def _login(client, email: str = "login-test@example.com", password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _vehiculo_body(placa: str = "ABC123", **kwargs: object) -> dict:
    body: dict = {
        "placa": placa,
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2020,
        "color": "Blanco",
        "tipo_seguro": "Todo riesgo",
        "foto_frontal": None,
    }
    body.update(kwargs)
    return body


def _vehiculo_db(*, id_usuario: int, placa: str) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        v = Vehiculo(
            id_usuario=id_usuario,
            placa=placa,
            marca="Seed",
            modelo="X",
            anio=2020,
        )
        db.add(v)
        db.commit()
        db.refresh(v)
        return v.id
    finally:
        db.close()


def test_admin_no_puede_crear_vehiculo(client):
    token = _login(client)
    res = client.post("/api/vehiculos", json=_vehiculo_body(), headers=_hdr(token))
    assert res.status_code == 403
    assert "administrador" in res.json()["detail"].lower()


def test_admin_lista_vehiculos_de_cliente(client):
    token_admin = _login(client)
    token_cliente = _login(client, "cliente-test@example.com", "clave-valida-123")
    assert client.post("/api/vehiculos", json=_vehiculo_body("LIST01"), headers=_hdr(token_cliente)).status_code == 201
    res2 = client.get("/api/vehiculos", headers=_hdr(token_admin))
    assert res2.status_code == 200
    assert res2.json()["total"] >= 1


def test_admin_id_usuario_cero_lista_todos(client):
    """id_usuario=0 no debe filtrar a nadie: el admin ve el listado completo."""
    token_admin = _login(client)
    token_cliente = _login(client, "cliente-test@example.com", "clave-valida-123")
    assert client.post("/api/vehiculos", json=_vehiculo_body("ADMPL1"), headers=_hdr(token_cliente)).status_code == 201
    assert client.post("/api/vehiculos", json=_vehiculo_body("CLIPL1"), headers=_hdr(token_cliente)).status_code == 201
    res = client.get("/api/vehiculos?id_usuario=0", headers=_hdr(token_admin))
    assert res.status_code == 200
    assert res.json()["total"] >= 2


def test_placa_duplicada_409(client):
    token = _login(client, "cliente-test@example.com", "clave-valida-123")
    client.post("/api/vehiculos", json=_vehiculo_body("DUP999"), headers=_hdr(token))
    res = client.post("/api/vehiculos", json=_vehiculo_body("DUP999"), headers=_hdr(token))
    assert res.status_code == 409
    assert res.json()["detail"] == "Placa ya registrada"


def test_cliente_no_accede_vehiculo_de_otro(client):
    token_cliente = _login(client, "cliente-test@example.com", "clave-valida-123")
    vid = _vehiculo_db(id_usuario=1, placa="ADMVEH1")
    res2 = client.get(f"/api/vehiculos/{vid}", headers=_hdr(token_cliente))
    assert res2.status_code == 404


def test_cliente_no_puede_crear_para_otro_usuario(client):
    token = _login(client, "cliente-test@example.com", "clave-valida-123")
    res = client.post(
        "/api/vehiculos",
        json={**_vehiculo_body("ASG001"), "id_usuario": 1},
        headers=_hdr(token),
    )
    assert res.status_code == 403


def test_eliminar_con_incidente_activo_409(client):
    token = _login(client, "cliente-test@example.com", "clave-valida-123")
    res = client.post("/api/vehiculos", json=_vehiculo_body("INC001"), headers=_hdr(token))
    assert res.status_code == 201
    vid = res.json()["id"]

    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(
            Incidente(
                id_vehiculo=vid,
                latitud=-34.6,
                longitud=-58.4,
                descripcion="Test",
                estado="Pendiente",
            ),
        )
        db.commit()
    finally:
        db.close()

    rdel = client.delete(f"/api/vehiculos/{vid}", headers=_hdr(token))
    assert rdel.status_code == 409


def test_eliminar_con_incidente_cerrado_204(client):
    token = _login(client, "cliente-test@example.com", "clave-valida-123")
    res = client.post("/api/vehiculos", json=_vehiculo_body("INC002"), headers=_hdr(token))
    assert res.status_code == 201
    vid = res.json()["id"]

    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(
            Incidente(
                id_vehiculo=vid,
                latitud=-34.6,
                longitud=-58.4,
                descripcion="Test",
                estado="cerrado",
            ),
        )
        db.commit()
    finally:
        db.close()

    rdel = client.delete(f"/api/vehiculos/{vid}", headers=_hdr(token))
    assert rdel.status_code == 204
