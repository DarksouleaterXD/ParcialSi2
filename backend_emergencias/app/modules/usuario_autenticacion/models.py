from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Table, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

usuario_rol = Table(
    "usuario_rol",
    Base.metadata,
    Column("id_usuario", Integer, ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True),
    Column("id_rol", Integer, ForeignKey("rol.id", ondelete="CASCADE"), primary_key=True),
)


class Rol(Base):
    __tablename__ = "rol"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String(255))
    permisos_json = Column("permisos_json", Text, nullable=True)


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    passwordhash = Column("passwordhash", String(255), nullable=False)
    telefono = Column(String(20))
    fotoperfil = Column("fotoperfil", String(255))
    estado = Column(String(50), default="Activo")
    latitud = Column(Numeric(10, 8))
    longitud = Column(Numeric(11, 8))
    fecharegistro = Column("fecharegistro", DateTime, server_default=func.now())

    roles = relationship("Rol", secondary=usuario_rol, lazy="selectin")
    vehiculos = relationship("Vehiculo", back_populates="usuario", lazy="selectin")


class Vehiculo(Base):
    __tablename__ = "vehiculo"

    id = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)
    placa = Column(String(20), unique=True, nullable=False)
    marca = Column(String(50), nullable=False)
    modelo = Column(String(50), nullable=False)
    anio = Column(Integer, nullable=False)
    color = Column(String(30))
    tiposeguro = Column("tiposeguro", String(50))
    fotofrontal = Column("fotofrontal", String(255))

    usuario = relationship("Usuario", back_populates="vehiculos")
    incidentes = relationship("Incidente", back_populates="vehiculo", lazy="selectin")
