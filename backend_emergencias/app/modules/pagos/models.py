"""Modelos del módulo pagos."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.sql import func

from app.core.database import Base


class Pago(Base):
    __tablename__ = "pago"

    id = Column(Integer, primary_key=True)
    incidente_id = Column("id_incidente", Integer, ForeignKey("incidente.id", ondelete="RESTRICT"), nullable=False, unique=True)
    cliente_id = Column("id_cliente", Integer, ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    tecnico_id = Column("id_tecnico", Integer, ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    monto_total = Column(Numeric(12, 2), nullable=False)
    monto_taller = Column(Numeric(12, 2), nullable=False)
    comision_plataforma = Column(Numeric(12, 2), nullable=False)
    metodo_pago = Column(String(50), nullable=False, default="TARJETA_SIMULADA")
    estado = Column(String(50), nullable=False, default="COMPLETADO")
    created_at = Column("fechapago", DateTime, server_default=func.now(), nullable=False)
