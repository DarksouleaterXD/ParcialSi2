from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import expression, func

from app.core.database import Base

class Bitacora(Base):
    __tablename__ = "bitacora"

    id = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)
    modulo = Column(String(50), nullable=False)
    accion = Column(String(100), nullable=False)
    iporigen = Column("iporigen", String(45))
    resultado = Column(String(50))
    fechahora = Column("fechahora", DateTime, server_default=func.now())


class TokenRevocado(Base):
    __tablename__ = "tokenrevocado"

    jti = Column(String(64), primary_key=True)
    expiracion = Column(DateTime, nullable=False)


class Notificacion(Base):
    __tablename__ = "notificacion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)
    titulo = Column(String(150), nullable=False)
    mensaje = Column(Text, nullable=False)
    tipo = Column(String(50), nullable=True)
    leida = Column(Boolean, nullable=False, default=False, server_default=expression.false())
    fechahora = Column("fechahora", DateTime, server_default=func.now())


class NotificacionPushToken(Base):
    """Token FCM/Web para notificaciones push (un usuario puede tener varios dispositivos)."""

    __tablename__ = "notificacion_push_token"
    __table_args__ = (UniqueConstraint("id_usuario", "token", name="uq_push_token_user_token"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(512), nullable=False)
    plataforma = Column(String(32), nullable=False)
    fechacreacion = Column("fechacreacion", DateTime, server_default=func.now())


class IdempotenciaRegistro(Base):
    """Claves de idempotencia por usuario y alcance (TTL en `expira_en`)."""

    __tablename__ = "idempotencia_registro"
    __table_args__ = (UniqueConstraint("id_usuario", "alcance", "clave", name="uq_idempotencia_usuario_alcance_clave"),)

    id = Column(Integer, primary_key=True)
    alcance = Column(String(50), nullable=False)
    clave = Column(String(128), nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)
    huella_carga = Column(String(64), nullable=False)
    id_incidente_ref = Column(Integer, ForeignKey("incidente.id", ondelete="CASCADE"), nullable=True)
    id_evidencia_ref = Column(Integer, ForeignKey("evidencia.id", ondelete="CASCADE"), nullable=True)
    fechacreacion = Column(DateTime, server_default=func.now())
    expira_en = Column(DateTime, nullable=False)
