from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

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
