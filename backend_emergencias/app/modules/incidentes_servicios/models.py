"""Modelos de incidentes (p. ej. validación de baja de vehículo con incidente activo)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Incidente(Base):
    __tablename__ = "incidente"

    id = Column(Integer, primary_key=True)
    id_vehiculo = Column(Integer, ForeignKey("vehiculo.id", ondelete="RESTRICT"), nullable=False)
    latitud = Column(Numeric(10, 8), nullable=False)
    longitud = Column(Numeric(11, 8), nullable=False)
    descripcion = Column(Text, nullable=False)
    fechacreacion = Column("fechacreacion", DateTime, server_default=func.now())
    estado = Column(String(50), default="Pendiente")
    categoria_ia = Column(String(100))
    prioridad_ia = Column(String(50))
    resumen_ia = Column(Text)
    confianza_ia = Column(Numeric(5, 2))

    vehiculo = relationship("Vehiculo", back_populates="incidentes", foreign_keys=[id_vehiculo])
