import uuid

from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.incidentes_servicios.models import Incidente
from app.modules.pagos.models import Pago
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


def _create_pago(*, incidente_id: int, estado: str) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        p = Pago(
            incidente_id=incidente_id,
            cliente_id=2,
            tecnico_id=3,
            monto_total=100,
            monto_taller=90,
            comision_plataforma=10,
            metodo_pago="TARJETA",
            estado=estado,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return p.id
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
    assert data["cliente"]["id"] == 2
    assert data["tecnico"]["id"] == 3
    assert data["taller"]["nombre"] == "Taller Test"


def test_calificar_servicio_no_finalizado_400(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Pendiente")
    res = client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token),
        json={"puntuacion": 3},
    )
    assert res.status_code == 400


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


def test_calificar_si_pago_no_confirmado_400(client):
    token = _login(client, "cliente-test@example.com")
    iid = _create_incidente(estado="Finalizado")
    _create_pago(incidente_id=iid, estado="PENDIENTE")
    res = client.post(
        f"/api/incidentes-servicios/{iid}/calificacion",
        headers=_hdr(token),
        json={"puntuacion": 5},
    )
    assert res.status_code == 400


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
