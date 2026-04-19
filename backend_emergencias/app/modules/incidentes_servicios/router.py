"""API incidentes y evidencias (CU-09). Autenticación JWT obligatoria en mutaciones y lecturas."""

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.incidentes_servicios.schemas import (
    EvidenceCreateResponse,
    IncidentCreateRequest,
    IncidentDetailResponse,
    IncidentResponse,
    IncidentesHealth,
)
from app.modules.incidentes_servicios.services import (
    add_evidence_to_incident,
    create_incident_for_client,
    get_incident_detail,
)
from app.modules.usuario_autenticacion.models import Usuario
from app.modules.usuario_autenticacion.services import get_current_user

router = APIRouter(prefix="/incidentes-servicios", tags=["incidentes_servicios"])


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


@router.get("/health", response_model=IncidentesHealth)
def incidentes_health() -> IncidentesHealth:
    """Estado del módulo (sin autenticación)."""
    return IncidentesHealth(modulo="incidentes_servicios", status="ok")


@router.post(
    "/incidentes",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear incidente (cliente)",
    description="""
Crea un incidente **Pendiente** para el vehículo indicado.

**Request (JSON):** `vehiculo_id`, `latitud`, `longitud`, `descripcion_texto` (opcional, máx. 1000).

**Response 201:** `IncidentResponse` con `evidencias_count` en 0.

**Errores:** 403 si no es cliente o el vehículo no es propio; 404 si el vehículo no existe; 409 si el vehículo ya tiene incidente activo.
""",
)
def create_incident(
    body: IncidentCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> IncidentResponse:
    return create_incident_for_client(db, user, body, client_ip=_client_ip(request))


@router.post(
    "/incidentes/{incidente_id}/evidencias",
    response_model=EvidenceCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adjuntar evidencia",
    description="""
`multipart/form-data`:

- **tipo** (obligatorio): `foto` | `audio` | `texto`
- **contenido_texto** (obligatorio si tipo=texto): texto plano
- **archivo** (obligatorio si tipo=foto o audio): binario; MIME permitidos (foto: jpeg/png/webp; audio: mpeg, mp4, webm, wav)

**Response 201:** `EvidenceCreateResponse` con `url_or_path` relativo al directorio de uploads (vacío para evidencia solo texto).

**Errores:** 403 si no es el dueño del incidente; 404 si el incidente no existe; 422 validación de tipo/contenido/MIME.
""",
)
async def attach_evidence(
    incidente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    tipo: str = Form(..., description="foto | audio | texto"),
    contenido_texto: str | None = Form(None),
    archivo: UploadFile | None = File(None),
) -> EvidenceCreateResponse:
    file_bytes: bytes | None = None
    ct: str | None = None
    if archivo is not None:
        ct = archivo.content_type
        file_bytes = await archivo.read()
    return add_evidence_to_incident(
        db,
        user,
        incidente_id,
        tipo_raw=tipo,
        contenido_texto=contenido_texto,
        file_bytes=file_bytes,
        file_content_type=ct,
        client_ip=_client_ip(request),
    )


@router.get(
    "/incidentes/{incidente_id}",
    response_model=IncidentDetailResponse,
    summary="Detalle de incidente",
    description="""
Devuelve datos del incidente, conteo de evidencias y la lista de evidencias (sin incluir el texto completo de notas en `url_or_path`).

**Autorización:** dueño del vehículo (cliente) o **Administrador**.

**Response 200:** `IncidentDetailResponse`.
""",
)
def get_incident(
    incidente_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> IncidentDetailResponse:
    return get_incident_detail(db, user, incidente_id)
