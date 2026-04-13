"""Modelo SQLAlchemy Taller (tabla `taller`)."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String

from app.core.database import Base


class Taller(Base):
    __tablename__ = "taller"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_admin = Column(Integer, ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    nombre = Column(String(100), nullable=False)
    direccion = Column(String(255), nullable=False)
    latitud = Column(Numeric(10, 8))
    longitud = Column(Numeric(11, 8))
    telefono = Column(String(20))
    email = Column(String(150))
    horario_atencion = Column(String(120))
    disponibilidad = Column(Boolean, nullable=False, default=True)
    capacidad_max = Column("capacidadmax", Integer, nullable=False)
    calificacion = Column(Numeric(3, 2), nullable=False, default=0)
