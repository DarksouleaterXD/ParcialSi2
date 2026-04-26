import uuid

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.incidentes_servicios.models import Incidente
from app.modules.pagos.models import Pago
from app.modules.usuario_autenticacion.models import Rol, Usuario, Vehiculo, usuario_rol


def _login(client, email: str, password: str = "clave-valida-123") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_incidente(*, estado: str) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        veh = Vehiculo(
            id_usuario=2,
            placa=f"PAG-{uuid.uuid4().hex[:8]}",
            marca="Ford",
            modelo="Fiesta",
            anio=2020,
        )
        db.add(veh)
        db.flush()
        inc = Incidente(
            id_vehiculo=veh.id,
            latitud=-34.60,
            longitud=-58.38,
            descripcion="Servicio finalizado para prueba de pago",
            estado=estado,
            tecnico_id=3,
        )
        db.add(inc)
        db.commit()
        db.refresh(inc)
        return inc.id
    finally:
        db.close()


def _ensure_extra_cliente(client) -> str:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        from app.core.security import hash_password

        email = f"cliente.extra.{uuid.uuid4().hex[:8]}@example.com"
        u = Usuario(
            nombre="Cliente",
            apellido="Extra",
            email=email,
            passwordhash=hash_password("clave-valida-123"),
            estado="Activo",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        rc = db.execute(select(Rol).where(Rol.nombre == "Cliente")).scalar_one()
        db.execute(usuario_rol.insert().values(id_usuario=u.id, id_rol=rc.id))
        db.commit()
    finally:
        db.close()
    return _login(client, email)


def _ensure_extra_tecnico(client) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        from app.core.security import hash_password

        email = f"tecnico.extra.{uuid.uuid4().hex[:8]}@example.com"
        u = Usuario(
            nombre="Tecnico",
            apellido="Extra",
            email=email,
            passwordhash=hash_password("clave-valida-123"),
            estado="Activo",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        rt = db.execute(select(Rol).where(Rol.nombre == "Tecnico")).scalar_one()
        db.execute(usuario_rol.insert().values(id_usuario=u.id, id_rol=rt.id))
        db.commit()
        return int(u.id)
    finally:
        db.close()


def test_procesar_pago_ok_calcula_comision_y_actualiza_incidente(client):
    token_cliente = _login(client, "cliente-test@example.com")
    incidente_id = _create_incidente(estado="Finalizado")

    res = client.post(
        f"/api/pagos/incidentes/{incidente_id}/procesar",
        headers=_hdr(token_cliente),
        json={"monto_total": 1000},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["incidente_id"] == incidente_id
    assert body["monto_total"] == 1000.0
    assert body["comision_plataforma"] == 100.0
    assert body["monto_taller"] == 900.0
    assert body["estado"] == "COMPLETADO"

    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        inc = db.get(Incidente, incidente_id)
        assert inc is not None
        assert (inc.estado or "").lower() == "pagado"
        pago = db.execute(select(Pago).where(Pago.incidente_id == incidente_id)).scalar_one_or_none()
        assert pago is not None
    finally:
        db.close()


def test_procesar_pago_reintento_devuelve_409(client):
    token_cliente = _login(client, "cliente-test@example.com")
    incidente_id = _create_incidente(estado="Finalizado")

    first = client.post(
        f"/api/pagos/incidentes/{incidente_id}/procesar",
        headers=_hdr(token_cliente),
        json={"monto_total": 800, "metodo_pago": "EFECTIVO"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/pagos/incidentes/{incidente_id}/procesar",
        headers=_hdr(token_cliente),
        json={"monto_total": 800, "metodo_pago": "EFECTIVO"},
    )
    assert second.status_code == 409


def test_procesar_pago_usuario_no_duenio_devuelve_403(client):
    token_otro_cliente = _ensure_extra_cliente(client)
    incidente_id = _create_incidente(estado="Finalizado")

    res = client.post(
        f"/api/pagos/incidentes/{incidente_id}/procesar",
        headers=_hdr(token_otro_cliente),
        json={"monto_total": 500},
    )
    assert res.status_code == 403


def test_procesar_pago_si_no_finalizado_devuelve_400(client):
    token_cliente = _login(client, "cliente-test@example.com")
    incidente_id = _create_incidente(estado="En Proceso")

    res = client.post(
        f"/api/pagos/incidentes/{incidente_id}/procesar",
        headers=_hdr(token_cliente),
        json={"monto_total": 700},
    )
    assert res.status_code == 400


def _insert_pago_row(*, incidente_id: int, cliente_id: int, tecnico_id: int, monto_total: float) -> None:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        from app.modules.pagos.models import Pago

        total = float(monto_total)
        comision = round(total * 0.10, 2)
        taller = round(total - comision, 2)
        row = Pago(
            incidente_id=incidente_id,
            cliente_id=cliente_id,
            tecnico_id=tecnico_id,
            monto_total=total,
            monto_taller=taller,
            comision_plataforma=comision,
            metodo_pago="EFECTIVO",
            estado="COMPLETADO",
        )
        db.add(row)
        db.commit()
    finally:
        db.close()


def test_listar_pagos_admin_ve_todos_con_paginacion(client):
    token_admin = _login(client, "login-test@example.com")
    i1 = _create_incidente(estado="Pagado")
    i2 = _create_incidente(estado="Pagado")
    i3 = _create_incidente(estado="Pagado")
    _insert_pago_row(incidente_id=i1, cliente_id=2, tecnico_id=3, monto_total=100)
    _insert_pago_row(incidente_id=i2, cliente_id=2, tecnico_id=3, monto_total=200)
    _insert_pago_row(incidente_id=i3, cliente_id=2, tecnico_id=3, monto_total=300)

    res = client.get("/api/pagos?page=1&page_size=2", headers=_hdr(token_admin))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total"] >= 3
    assert len(body["items"]) == 2
    assert body["items"][0]["id"] > body["items"][1]["id"]


def test_listar_pagos_tecnico_solo_propios(client):
    token_tecnico = _login(client, "tecnico-test@example.com")
    token_admin = _login(client, "login-test@example.com")
    tecnico_otro_id = _ensure_extra_tecnico(client)
    i1 = _create_incidente(estado="Pagado")
    i2 = _create_incidente(estado="Pagado")
    _insert_pago_row(incidente_id=i1, cliente_id=2, tecnico_id=3, monto_total=150)
    _insert_pago_row(incidente_id=i2, cliente_id=2, tecnico_id=tecnico_otro_id, monto_total=250)

    res = client.get("/api/pagos", headers=_hdr(token_tecnico))
    assert res.status_code == 200
    body = res.json()
    assert body["items"]
    assert all(item["tecnico_id"] == 3 for item in body["items"])

    # admin sigue viendo todos
    res_admin = client.get("/api/pagos", headers=_hdr(token_admin))
    assert res_admin.status_code == 200
    assert res_admin.json()["total"] >= body["total"]


def test_listar_pagos_cliente_solo_propios(client):
    token_cliente = _login(client, "cliente-test@example.com")
    i1 = _create_incidente(estado="Pagado")
    _insert_pago_row(incidente_id=i1, cliente_id=2, tecnico_id=3, monto_total=190)

    res = client.get("/api/pagos", headers=_hdr(token_cliente))
    assert res.status_code == 200
    body = res.json()
    assert body["items"]
    assert all(item["cliente_id"] == 2 for item in body["items"])
