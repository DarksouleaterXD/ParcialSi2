"""API de incidentes y evidencias. Autenticación JWT obligatoria en mutaciones y lecturas sensibles."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, Header, Query, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.incidentes_servicios.ai_assignment_schemas import (
    AssignmentCandidatesResponse,
    AssignmentConfirmRequest,
    AssignmentOverrideRequest,
    IncidentIaProcessResponse,
    IncidentIaResultResponse,
)
from app.modules.incidentes_servicios.schemas import (
    CalificacionCreate,
    CalificacionResponse,
    EvidenceCreateResponse,
    IncidentAcceptRequest,
    IncidentCreateRequest,
    IncidentDetailResponse,
    IncidentFinalizeRequest,
    IncidentListResponse,
    IncidentRejectResponse,
    IncidentResponse,
    IncidentesHealth,
)
from app.modules.incidentes_servicios.services import (
    aceptar_solicitud,
    add_evidence_to_incident,
    cancel_incident_by_client,
    delete_incident_by_client,
    confirm_assignment_endpoint,
    crear_calificacion,
    create_incident_for_client,
    finalizar_servicio,
    get_incident_detail,
    get_incident_ia_result_endpoint,
    list_assignment_candidates_endpoint,
    list_incidents_paginated,
    marcar_en_camino,
    marcar_en_proceso,
    override_assignment_endpoint,
    rechazar_solicitud,
    run_enrich_incident_with_ai_task,
    trigger_ia_process_endpoint,
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


@router.get(
    "/incidentes",
    response_model=IncidentListResponse,
    summary="Listar incidentes (paginado)",
    description="""
Listado paginado con orden descendente por fecha de creación.

**Query:** `page` (default 1), `page_size` (default 10, máx. 100), `estado` (coincidencia exacta),
`cliente` (id usuario dueño, admin), `cliente_busqueda` (admin: texto en nombre, apellido o email),
`vehiculo_placa` (texto parcial en placa), `fecha_desde` / `fecha_hasta` (YYYY-MM-DD, inclusive).

**Permisos:** **Administrador** ve todos y puede filtrar por `cliente` o `cliente_busqueda`. **Cliente** solo sus incidentes.
**Técnico:** incidentes en bolsa (`Pendiente` sin `tecnico_id`) más los asignados a sí mismo (`tecnico_id` = usuario actual).

**JWT obligatorio.**
""",
)
def list_incidents(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    page: Annotated[int, Query(ge=1, description="Número de página")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Tamaño de página")] = 10,
    estado: Annotated[str | None, Query(description="Filtrar por estado exacto")] = None,
    cliente: Annotated[int | None, Query(ge=1, description="Solo administrador: id usuario dueño")] = None,
    cliente_busqueda: Annotated[
        str | None,
        Query(max_length=100, description="Solo administrador: busca en nombre, apellido o email (parcial)"),
    ] = None,
    vehiculo_placa: Annotated[
        str | None,
        Query(max_length=32, description="Placa del vehículo (coincidencia parcial, sin importar mayúsculas)"),
    ] = None,
    fecha_desde: Annotated[date | None, Query(description="Inicio inclusive (YYYY-MM-DD)")] = None,
    fecha_hasta: Annotated[date | None, Query(description="Fin inclusive (YYYY-MM-DD)")] = None,
) -> IncidentListResponse:
    return list_incidents_paginated(
        db,
        user,
        page=page,
        page_size=page_size,
        estado=estado,
        cliente=cliente,
        cliente_busqueda=cliente_busqueda,
        vehiculo_placa=vehiculo_placa,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


@router.post(
    "/incidentes",
    response_model=IncidentResponse,
    summary="Crear incidente (cliente)",
    description="""
Crea un incidente **Pendiente** para el vehículo indicado.

**Header obligatorio:** `Idempotency-Key` (8-128 caracteres `[A-Za-z0-9._-]`) para reintentos móviles sin duplicar.

**Request (JSON):** `vehiculo_id`, `latitud`, `longitud`, `descripcion_texto` (opcional, máx. 1000).

**Response:** `201` primera creación; `200` replay con misma clave y mismo cuerpo.

**Errores:** 403 si no es cliente o el vehículo no es propio; 404 si el vehículo no existe; 409 si el vehículo ya tiene incidente activo o clave idempotente con cuerpo distinto; 422 clave inválida.
""",
)
def create_incident(
    body: IncidentCreateRequest,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> IncidentResponse:
    out, created = create_incident_for_client(
        db,
        user,
        body,
        client_ip=_client_ip(request),
        idempotency_key_raw=idempotency_key,
    )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    if created:
        background_tasks.add_task(
            run_enrich_incident_with_ai_task,
            out.id,
            user.id,
            _client_ip(request),
        )
    return out


@router.post(
    "/incidentes/{incidente_id}/evidencias",
    response_model=EvidenceCreateResponse,
    summary="Adjuntar evidencia",
    description="""
`multipart/form-data`:

- **tipo** (obligatorio): `foto` | `audio` | `texto`
- **contenido_texto** (obligatorio si tipo=texto): texto plano
- **archivo** (obligatorio si tipo=foto o audio): binario; MIME permitidos (foto: jpeg/png/webp; audio: mpeg, mp4, webm, wav)

Idempotencia por **huella** (incidente + tipo + hash binario + texto): reintentos con el mismo contenido devuelven la misma evidencia (`200`) sin duplicar archivo.

**Response:** `201` alta nueva; `200` replay idempotente.

**Errores:** 403 si no es el dueño del incidente; 404 si el incidente no existe; 422 validación de tipo/contenido/MIME.
""",
)
async def attach_evidence(
    incidente_id: int,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
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
    out, created = add_evidence_to_incident(
        db,
        user,
        incidente_id,
        tipo_raw=tipo,
        contenido_texto=contenido_texto,
        file_bytes=file_bytes,
        file_content_type=ct,
        client_ip=_client_ip(request),
    )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    if created:
        background_tasks.add_task(
            run_enrich_incident_with_ai_task,
            incidente_id,
            user.id,
            _client_ip(request),
            force=True,
        )
    return out


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


@router.post(
    "/incidentes/{incidente_id}/aceptar",
    response_model=IncidentDetailResponse,
    summary="Aceptar solicitud (técnico o administrador)",
    description="""
**Técnico:** sin cuerpo; se asigna a sí mismo (`tecnico_id` = usuario actual).

**Administrador:** cuerpo JSON obligatorio `{"tecnico_id": <id>}` para asignar a un técnico.

**Cliente:** 403.

Si el incidente ya no está `Pendiente` libre en bolsa, **409**.
""",
)
def accept_incident(
    incidente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    body: Annotated[IncidentAcceptRequest | None, Body()] = None,
) -> IncidentDetailResponse:
    return aceptar_solicitud(db, user, incidente_id, client_ip=_client_ip(request), body=body)


@router.post(
    "/incidentes/{incidente_id}/rechazar",
    response_model=IncidentRejectResponse,
    summary="Rechazar solicitud en bolsa (técnico)",
    description="""
Solo **técnico**. Registra auditoría `INCIDENTE_RECHAZADO`; el incidente permanece `Pendiente` para otros.

**Administrador** y **cliente:** 403.
""",
)
def reject_incident(
    incidente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> IncidentRejectResponse:
    return rechazar_solicitud(db, user, incidente_id, client_ip=_client_ip(request))


@router.post(
    "/incidentes/{incidente_id}/cancelar",
    response_model=IncidentDetailResponse,
    summary="Cancelar solicitud (cliente dueño)",
    description="""
Solo el **cliente** dueño del vehículo puede cancelar. Estados permitidos: **Pendiente** o **Asignado** (aún no en curso).

**Response 200:** incidente con `estado` **Cancelado** (detalle con evidencias).

**403:** no es cliente, no es el dueño, o el incidente no es accesible.

**404:** incidente inexistente (para el cálculo de acceso del usuario actual).

**409:** solicitud en curso (p. ej. en camino, en proceso, finalizado) o ya cancelada.
""",
)
def cancel_incident(
    incidente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> IncidentDetailResponse:
    return cancel_incident_by_client(db, user, incidente_id, client_ip=_client_ip(request))


@router.delete(
    "/incidentes/{incidente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar solicitud (cliente dueño)",
    description="""
Borrado definitivo de solicitud por el cliente dueño, solo en estados cerrados/cancelados.

Estados permitidos (normalizados): cancelado, finalizado, pagado, cerrado, resuelto, completado.
""",
)
def delete_incident(
    incidente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> Response:
    delete_incident_by_client(db, user, incidente_id, client_ip=_client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/incidentes/{incidente_id}/en-camino",
    response_model=IncidentResponse,
    summary="Marcar en camino (técnico asignado)",
    description="""
**Solo el técnico asignado:** pasa de **Asignado** a **En Camino**.

**403** sin asignación o con otro usuario. **409** si el estado no es Asignado.
""",
)
def incidente_marcar_en_camino(
    incidente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> IncidentResponse:
    return marcar_en_camino(db, user, incidente_id, client_ip=_client_ip(request))


@router.post(
    "/incidentes/{incidente_id}/en-proceso",
    response_model=IncidentResponse,
    summary="Marcar en proceso (técnico asignado)",
    description="""
**Solo el técnico asignado:** pasa de **En Camino** a **En Proceso**.

**409** si el estado no es En Camino (p. ej. asignado sin en camino intermedio, o ya finalizado).
""",
)
def incidente_marcar_en_proceso(
    incidente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> IncidentResponse:
    return marcar_en_proceso(db, user, incidente_id, client_ip=_client_ip(request))


@router.post(
    "/incidentes/{incidente_id}/finalizar",
    response_model=IncidentResponse,
    summary="Finalizar servicio (técnico asignado)",
    description="""
**Solo el técnico asignado:** pasa de **En Proceso** a **Finalizado**.

Cuerpo JSON opcional: `diagnostico_final`, `precio_base` (informativo; resumen en bitácora).

**409** si el estado no es **En Proceso** (p. ej. asignado o en camino sin el paso intermedio requerido).
""",
)
def incidente_finalizar_servicio(
    incidente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    body: Annotated[IncidentFinalizeRequest | None, Body()] = None,
) -> IncidentResponse:
    return finalizar_servicio(
        db,
        user,
        incidente_id,
        body=body,
        client_ip=_client_ip(request),
    )


@router.post(
    "/incidentes/{incidente_id}/ia/process",
    response_model=IncidentIaProcessResponse,
    summary="Disparar reproceso IA (cliente dueño o admin)",
)
def incidente_ia_process(
    incidente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    force: Annotated[bool, Query(description="Forzar reproceso aunque exista resultado completed")] = False,
) -> IncidentIaProcessResponse:
    return trigger_ia_process_endpoint(
        db,
        user,
        incidente_id,
        force=force,
        client_ip=_client_ip(request),
    )


@router.get(
    "/incidentes/{incidente_id}/ia/result",
    response_model=IncidentIaResultResponse,
    summary="Resultado IA estructurado",
)
def incidente_ia_result(
    incidente_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> IncidentIaResultResponse:
    return get_incident_ia_result_endpoint(db, user, incidente_id)


@router.get(
    "/incidentes/{incidente_id}/asignacion/candidatos",
    response_model=AssignmentCandidatesResponse,
    summary="Candidatos de taller ordenados (scoring determinístico)",
)
def incidente_asignacion_candidatos(
    incidente_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> AssignmentCandidatesResponse:
    return list_assignment_candidates_endpoint(db, user, incidente_id)


@router.post(
    "/incidentes/{incidente_id}/asignacion/confirmar",
    response_model=IncidentDetailResponse,
    summary="Confirmar asignación sugerida (admin)",
)
def incidente_asignacion_confirmar(
    incidente_id: int,
    body: AssignmentConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> IncidentDetailResponse:
    return confirm_assignment_endpoint(db, user, incidente_id, body, client_ip=_client_ip(request))


@router.post(
    "/incidentes/{incidente_id}/asignacion/override",
    response_model=IncidentDetailResponse,
    summary="Override de asignación (admin)",
)
def incidente_asignacion_override(
    incidente_id: int,
    body: AssignmentOverrideRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> IncidentDetailResponse:
    return override_assignment_endpoint(db, user, incidente_id, body, client_ip=_client_ip(request))


@router.post(
    "/incidentes/{incidente_id}/calificar",
    response_model=CalificacionResponse,
    summary="Calificar servicio (cliente dueño)",
    description="""
Registra **una** calificación (1–5) y comentario opcional para un incidente **Finalizado** o **Pagado**.

**403:** no es cliente, no es el dueño del vehículo, o rol no permitido.

**404:** incidente inexistente o sin vehículo asociado.

**400:** estado del incidente no permite calificar, o ya existe calificación.
""",
)
def incidente_calificar(
    incidente_id: int,
    body: CalificacionCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> CalificacionResponse:
    return crear_calificacion(
        db,
        incidente_id,
        body,
        user,
        client_ip=_client_ip(request),
    )
