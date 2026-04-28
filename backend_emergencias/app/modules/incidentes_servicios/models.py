"""Modelos de incidentes, evidencias y asignación a técnico."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
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
    tecnico_id = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    ai_result_json = Column(Text)
    ai_confidence = Column(Numeric(5, 2))
    ai_status = Column(String(32))
    ai_provider = Column(String(64))
    ai_model = Column(String(128))
    prompt_version = Column(String(32))
    assignment_trace_json = Column(Text)

    vehiculo = relationship("Vehiculo", back_populates="incidentes", foreign_keys=[id_vehiculo])
    evidencias = relationship("Evidencia", back_populates="incidente", lazy="selectin", cascade="all, delete-orphan")
    asignaciones_servicio = relationship(
        "AsignacionServicio",
        back_populates="incidente",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class Evidencia(Base):
    __tablename__ = "evidencia"

    id = Column(Integer, primary_key=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(50), nullable=False)
    urlarchivo = Column("urlarchivo", String(255), nullable=False, default="")
    contenido_texto = Column("contenido_texto", Text, nullable=True)
    fechasubida = Column("fechasubida", DateTime, server_default=func.now())

    incidente = relationship("Incidente", back_populates="evidencias")


class AsignacionServicio(Base):
    """Servicio atendido (taller + mecánico) vinculado al incidente (script SQL / Neon)."""

    __tablename__ = "asignacionservicio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id", ondelete="RESTRICT"), nullable=False)
    id_taller = Column(Integer, ForeignKey("taller.id", ondelete="RESTRICT"), nullable=False)
    id_mecanico = Column(Integer, ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    costo_estimado = Column("costoestimado", Numeric(10, 2), nullable=True)
    distancia_km = Column("distanciakm", Numeric(8, 2), nullable=True)
    tiempo_llegada = Column("tiempollegada", Integer, nullable=True)
    estado = Column(String(50), nullable=True, default="Asignado")
    fecha_creacion = Column("fechacreacion", DateTime, server_default=func.now(), nullable=True)
    fecha_aceptacion = Column("fechaaceptacion", DateTime, nullable=True)
    fecha_fin = Column("fechafin", DateTime, nullable=True)
    motivo_rechazo = Column("motivorechazo", Text, nullable=True)
    trabajo_realizado = Column("trabajorealizado", Text, nullable=True)
    costo_final = Column("costofinal", Numeric(10, 2), nullable=True)
    obs_mecanico = Column("obsmecanico", Text, nullable=True)

    incidente = relationship("Incidente", back_populates="asignaciones_servicio")
    calificacion = relationship("Calificacion", back_populates="asignacion", uselist=False, cascade="all, delete-orphan")


class Calificacion(Base):
    """Valoración 1–5 del cliente; 1:1 con la fila de `AsignacionServicio`."""

    __tablename__ = "calificacion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_asignacion = Column(
        Integer,
        ForeignKey("asignacionservicio.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    puntuacion = Column(Integer, nullable=False)
    comentario = Column(Text)
    fecha = Column(DateTime, server_default=func.now(), nullable=False)

    asignacion = relationship("AsignacionServicio", back_populates="calificacion")


class IncidenteTallerCandidato(Base):
    """Ranking determinístico de talleres para un incidente (post-IA)."""

    __tablename__ = "incidente_taller_candidato"
    __table_args__ = (UniqueConstraint("id_incidente", "id_taller", name="uq_incidente_taller_candidato_inc_taller"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id", ondelete="CASCADE"), nullable=False)
    id_taller = Column(Integer, ForeignKey("taller.id", ondelete="CASCADE"), nullable=False)
    id_tecnico_sugerido = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    rank_order = Column(Integer, nullable=False)
    score_total = Column(Numeric(10, 4), nullable=False)
    score_breakdown_json = Column(Text, nullable=False, default="{}")
    eta_minutos_estimada = Column(Numeric(10, 2), nullable=True)
