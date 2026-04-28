import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.incidentes_servicios.models import AsignacionServicio, Calificacion, Incidente
from app.modules.usuario_autenticacion.models import Vehiculo


def _login(client, email: str, password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_incidente(
    *,
    estado: str,
    id_usuario_vehiculo: int = 2,
    with_asignacion: bool = True,
    asignacion_finalizada: bool = True,
) -> int:
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
        db.flush()
        if with_asignacion:
            asi = AsignacionServicio(
                id_incidente=inc.id,
                id_taller=1,
                id_mecanico=3,
                estado="Finalizado" if asignacion_finalizada else "Asignado",
                fecha_fin=datetime.utcnow() if asignacion_finalizada else None,
            )
            db.add(asi)
        db.commit()
        db.refresh(inc)
        return inc.id
    finally:
        db.close()


def test_calificacion_persiste_id_asignacion(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    res = client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token),
        json={"puntuacion": 5},
    )
    assert res.status_code == 200
    data = res.json()
    aid = data["id_asignacion"]
    cid = data["id"]
    Session = sessionmaker(bind=app.state.test_engine)
    db = Session()
    try:
        cal = db.execute(select(Calificacion).where(Calificacion.id == cid)).scalar_one()
        assert cal.id_asignacion == aid
        asi = db.get(AsignacionServicio, aid)
        assert asi is not None and asi.id_incidente == iid
    finally:
        db.close()


def test_calificar_finalizado_ok(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    res = client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token),
        json={"puntuacion": 5, "comentario": "Excelente"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["puntuacion"] == 5
    assert data["comentario"] == "Excelente"
    assert data["incidente_id"] == iid
    assert "id_asignacion" in data and data["id_asignacion"] >= 1
    assert data["mensaje"]
    assert data["cliente"]["id"] == 2
    assert data["tecnico"]["id"] == 3
    assert data["taller"]["nombre"] == "Taller Test"


def test_calificar_servicio_no_finalizado_400(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Finalizado", asignacion_finalizada=False)
    res = client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token),
        json={"puntuacion": 3},
    )
    assert res.status_code == 400
    assert "finalizado" in (res.json().get("detail") or "").lower()


def test_calificar_sin_asignacion_400(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Finalizado", with_asignacion=False)
    res = client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token),
        json={"puntuacion": 4},
    )
    assert res.status_code == 400
    assert "asignación" in (res.json().get("detail") or "").lower()


def test_calificar_duplicado_409(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    r1 = client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token),
        json={"puntuacion": 5},
    )
    assert r1.status_code == 200
    r2 = client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token),
        json={"puntuacion": 2},
    )
    assert r2.status_code == 409
    assert "calificado" in (r2.json().get("detail") or "").lower()


def test_calificar_servicio_de_otro_cliente_403(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Finalizado", id_usuario_vehiculo=1)
    res = client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token),
        json={"puntuacion": 5},
    )
    assert res.status_code == 403


def test_calificar_tecnico_403(client):
    token = _login(client, "tecnico-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    res = client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token),
        json={"puntuacion": 5},
    )
    assert res.status_code == 403


def test_calificar_rango_puntuacion_422(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    res = client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token),
        json={"puntuacion": 7},
    )
    assert res.status_code == 422


def test_calificar_404(client):
    token = _login(client, "cliente-test@example.com")
    res = client.post(
        "/api/incidentes-servicios/999999/calificacion",
        headers=_hdr(token),
        json={"puntuacion": 5},
    )
    assert res.status_code == 404


def test_cliente_lista_mis_calificaciones(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    c = client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token),
        json={"puntuacion": 4, "comentario": "Todo ok"},
    )
    assert c.status_code == 200
    res = client.get("/api/incidentes-servicios/calificaciones/mis?page=1&page_size=10", headers=_hdr(token))
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert data["items"][0]["cliente"]["id"] == 2


def test_admin_lista_calificaciones(client):
    token_cliente = _login(client, "cliente-test@example.com")
    token_admin = _login(client, "login-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    assert (
        client.post(
            f"/api/incidentes-servicios/{iid}/calificacion",
            headers=_hdr(token_cliente),
            json={"puntuacion": 5, "comentario": "Excelente"},
        ).status_code
        == 200
    )
    res = client.get("/api/admin/incidentes-servicios/calificaciones?page=1&page_size=10", headers=_hdr(token_admin))
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert "summary" in data


def test_admin_filtra_por_cliente(client):
    token_cliente = _login(client, "cliente-test@example.com")
    token_admin = _login(client, "login-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    assert (
        client.post(
            f"/api/incidentes-servicios/{iid}/calificacion",
            headers=_hdr(token_cliente),
            json={"puntuacion": 3},
        ).status_code
        == 200
    )
    res = client.get(
        "/api/admin/incidentes-servicios/calificaciones?cliente=cliente-test@example.com",
        headers=_hdr(token_admin),
    )
    assert res.status_code == 200
    assert res.json()["total"] >= 1


def test_admin_filtra_por_taller(client):
    token_cliente = _login(client, "cliente-test@example.com")
    token_admin = _login(client, "login-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    assert client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token_cliente),
        json={"puntuacion": 5},
    ).status_code == 200
    res = client.get(
        "/api/admin/incidentes-servicios/calificaciones?taller=Taller%20Test",
        headers=_hdr(token_admin),
    )
    assert res.status_code == 200
    assert res.json()["total"] >= 1


def test_admin_filtra_por_tecnico(client):
    token_cliente = _login(client, "cliente-test@example.com")
    token_admin = _login(client, "login-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    assert client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token_cliente),
        json={"puntuacion": 4},
    ).status_code == 200
    res = client.get(
        "/api/admin/incidentes-servicios/calificaciones?tecnico=T%C3%A9cnico",
        headers=_hdr(token_admin),
    )
    assert res.status_code == 200
    assert res.json()["total"] >= 1


def test_admin_filtra_por_puntuacion(client):
    token_cliente = _login(client, "cliente-test@example.com")
    token_admin = _login(client, "login-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    assert client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token_cliente),
        json={"puntuacion": 2},
    ).status_code == 200
    res = client.get(
        "/api/admin/incidentes-servicios/calificaciones?puntuacion=2",
        headers=_hdr(token_admin),
    )
    assert res.status_code == 200
    assert all(item["puntuacion"] == 2 for item in res.json()["items"])


def test_no_admin_no_accede_admin_calificaciones(client):
    token_cliente = _login(client, "cliente-test@example.com")
    res = client.get("/api/admin/incidentes-servicios/calificaciones", headers=_hdr(token_cliente))
    assert res.status_code == 403


def test_admin_detalle_calificacion(client):
    token_cliente = _login(client, "cliente-test@example.com")
    token_admin = _login(client, "login-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    create = client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token_cliente),
        json={"puntuacion": 5, "comentario": "Excelente"},
    )
    assert create.status_code == 200
    cid = create.json()["id"]
    res = client.get(f"/api/admin/incidentes-servicios/calificaciones/{cid}", headers=_hdr(token_admin))
    assert res.status_code == 200
    assert res.json()["id"] == cid


def test_bitacora_event_create_truncates_client_ip_and_outcome():
    from app.modules.sistema.bitacora_service import BitacoraEventCreate

    long_ip = "127.0.0.1, " + "1.2.3.4, " * 30
    e = BitacoraEventCreate(
        user_id=1,
        module="pagos",
        action="TEST",
        client_ip=long_ip,
        outcome="x" * 80,
    )
    assert len(e.client_ip or "") <= 45
    assert len(e.outcome or "") <= 50
