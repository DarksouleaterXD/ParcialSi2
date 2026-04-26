import uuid

from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.incidentes_servicios.models import Incidente
from app.modules.usuario_autenticacion.models import Vehiculo


def _login(client, email: str, password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_incidente(*, estado: str, id_usuario_vehiculo: int = 2) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        veh = Vehiculo(
            id_usuario=id_usuario_vehiculo,
            placa=f"CAL-{uuid.uuid4().hex[:8]}",
            marca="VW",
            modelo="Gol",
            anio=2019,
        )
        db.add(veh)
        db.flush()
        inc = Incidente(
            id_vehiculo=veh.id,
            latitud=-34.60,
            longitud=-58.38,
            descripcion="Prueba calificación",
            estado=estado,
            tecnico_id=3,
        )
        db.add(inc)
        db.commit()
        db.refresh(inc)
        return inc.id
    finally:
        db.close()


def test_calificar_finalizado_ok(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    res = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/calificar",
        headers=_hdr(token),
        json={"puntuacion": 5, "comentario": "Excelente"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["puntuacion"] == 5
    assert data["comentario"] == "Excelente"
    assert data["incidente_id"] == iid


def test_calificar_pagado_ok(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Pagado")
    res = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/calificar",
        headers=_hdr(token),
        json={"puntuacion": 4},
    )
    assert res.status_code == 200
    assert res.json()["puntuacion"] == 4


def test_calificar_pendiente_400(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Pendiente")
    res = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/calificar",
        headers=_hdr(token),
        json={"puntuacion": 3},
    )
    assert res.status_code == 400


def test_calificar_duplicado_400(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    r1 = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/calificar",
        headers=_hdr(token),
        json={"puntuacion": 5},
    )
    assert r1.status_code == 200
    r2 = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/calificar",
        headers=_hdr(token),
        json={"puntuacion": 2},
    )
    assert r2.status_code == 400


def test_calificar_no_dueño_403(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Finalizado", id_usuario_vehiculo=1)
    res = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/calificar",
        headers=_hdr(token),
        json={"puntuacion": 5},
    )
    assert res.status_code == 403


def test_calificar_tecnico_403(client):
    token = _login(client, "tecnico-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    res = client.post(
        f"/api/incidentes-servicios/incidentes/{iid}/calificar",
        headers=_hdr(token),
        json={"puntuacion": 5},
    )
    assert res.status_code == 403


def test_calificar_404(client):
    token = _login(client, "cliente-test@example.com")
    res = client.post(
        "/api/incidentes-servicios/incidentes/999999/calificar",
        headers=_hdr(token),
        json={"puntuacion": 5},
    )
    assert res.status_code == 404
