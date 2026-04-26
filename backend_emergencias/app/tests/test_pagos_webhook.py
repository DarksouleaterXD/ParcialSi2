"""Stripe webhook: signature verification, side effects, idempotencia."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.incidentes_servicios.models import Incidente
from app.modules.pagos.models import Pago
from app.modules.sistema.models import Bitacora
from app.modules.usuario_autenticacion.models import Usuario, Vehiculo


def _stripe_sign(body: bytes, secret: str) -> str:
    ts = int(time.time())
    payload = body.decode("utf-8")
    signed = f"{ts}.{payload}"
    sig = hmac.new(secret.encode("utf-8"), signed.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def _create_incidente_finalizado(*, id_usuario: int = 2, tecnico_id: int | None = 3) -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        veh = Vehiculo(
            id_usuario=id_usuario,
            placa=f"WH-{uuid.uuid4().hex[:8]}",
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
            descripcion="Webhook test",
            estado="Finalizado",
            tecnico_id=tecnico_id,
        )
        db.add(inc)
        db.commit()
        db.refresh(inc)
        return int(inc.id)
    finally:
        db.close()


def _webhook_body(*, incidente_id: int, amount_cents: int = 5000, pi_id: str | None = None) -> dict:
    pi = pi_id or f"pi_test_{uuid.uuid4().hex[:12]}"
    return {
        "id": f"evt_test_{uuid.uuid4().hex[:16]}",
        "object": "event",
        "api_version": "2022-11-15",
        "type": "payment_intent.succeeded",
        "livemode": False,
        "data": {
            "object": {
                "id": pi,
                "object": "payment_intent",
                "amount": amount_cents,
                "currency": "usd",
                "metadata": {"incidente_id": str(incidente_id)},
            },
        },
    }


def test_webhook_sin_firma_devuelve_400(client, monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "stripe_webhook_secret", "whsec_test_local_only", raising=False)
    res = client.post("/api/pagos/webhook", content=b"{}", headers={})
    assert res.status_code == 400


def test_webhook_firma_invalida_devuelve_400(client, monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "stripe_webhook_secret", "whsec_test_local_only", raising=False)
    body = json.dumps(_webhook_body(incidente_id=1)).encode()
    res = client.post(
        "/api/pagos/webhook",
        content=body,
        headers={"stripe-signature": "t=0,v1=deadbeef"},
    )
    assert res.status_code == 400


def test_webhook_payment_intent_succeeded_crea_pago_y_bitacora(client, monkeypatch):
    from app.core import config

    secret = "whsec_test_local_only"
    monkeypatch.setattr(config.settings, "stripe_webhook_secret", secret, raising=False)

    iid = _create_incidente_finalizado()
    body_dict = _webhook_body(incidente_id=iid, amount_cents=10000)
    raw = json.dumps(body_dict, separators=(",", ":")).encode()
    sig = _stripe_sign(raw, secret)

    before = _bitacora_pagos_count()
    res = client.post("/api/pagos/webhook", content=raw, headers={"stripe-signature": sig})
    assert res.status_code == 200, res.text
    assert res.json().get("status") == "success"

    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        inc = db.get(Incidente, iid)
        assert inc is not None
        assert (inc.estado or "").strip().lower() == "pagado"
        pago = db.execute(select(Pago).where(Pago.incidente_id == iid)).scalar_one_or_none()
        assert pago is not None
        assert float(pago.monto_total) == 100.0
        assert float(pago.comision_plataforma) == 10.0
        assert float(pago.monto_taller) == 90.0
        assert pago.metodo_pago == "STRIPE"
    finally:
        db.close()

    after = _bitacora_pagos_count()
    assert after == before + 1


def _bitacora_pagos_count() -> int:
    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        return int(
            db.scalar(
                select(func.count())
                .select_from(Bitacora)
                .where(Bitacora.modulo == "pagos", Bitacora.accion == "PAGO_PROCESADO"),
            )
            or 0,
        )
    finally:
        db.close()


def test_webhook_idempotente_mismo_evento_dos_veces_un_solo_pago(client, monkeypatch):
    from app.core import config

    secret = "whsec_test_local_idem"
    monkeypatch.setattr(config.settings, "stripe_webhook_secret", secret, raising=False)

    iid = _create_incidente_finalizado()
    body_dict = _webhook_body(incidente_id=iid, amount_cents=8000, pi_id="pi_idem_shared")
    raw = json.dumps(body_dict, separators=(",", ":")).encode()
    sig1 = _stripe_sign(raw, secret)
    time.sleep(1.1)
    sig2 = _stripe_sign(raw, secret)

    r1 = client.post("/api/pagos/webhook", content=raw, headers={"stripe-signature": sig1})
    r2 = client.post("/api/pagos/webhook", content=raw, headers={"stripe-signature": sig2})
    assert r1.status_code == 200 and r2.status_code == 200

    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        n = db.execute(select(func.count()).select_from(Pago).where(Pago.incidente_id == iid)).scalar()
        assert int(n or 0) == 1
    finally:
        db.close()


def test_webhook_sin_metadata_incidente_no_crea_pago(client, monkeypatch):
    from app.core import config

    secret = "whsec_test_local_only"
    monkeypatch.setattr(config.settings, "stripe_webhook_secret", secret, raising=False)

    iid = _create_incidente_finalizado()
    body_dict = _webhook_body(incidente_id=iid)
    body_dict["data"]["object"]["metadata"] = {}
    raw = json.dumps(body_dict, separators=(",", ":")).encode()
    sig = _stripe_sign(raw, secret)

    res = client.post("/api/pagos/webhook", content=raw, headers={"stripe-signature": sig})
    assert res.status_code == 200

    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        pago = db.execute(select(Pago).where(Pago.incidente_id == iid)).scalar_one_or_none()
        assert pago is None
    finally:
        db.close()


def test_webhook_incidente_sin_tecnico_no_crea_pago(client, monkeypatch):
    from app.core import config

    secret = "whsec_test_local_only"
    monkeypatch.setattr(config.settings, "stripe_webhook_secret", secret, raising=False)

    iid = _create_incidente_finalizado(tecnico_id=None)
    body_dict = _webhook_body(incidente_id=iid)
    raw = json.dumps(body_dict, separators=(",", ":")).encode()
    sig = _stripe_sign(raw, secret)

    res = client.post("/api/pagos/webhook", content=raw, headers={"stripe-signature": sig})
    assert res.status_code == 200

    engine = app.state.test_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        pago = db.execute(select(Pago).where(Pago.incidente_id == iid)).scalar_one_or_none()
        assert pago is None
    finally:
        db.close()
