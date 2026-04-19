import secrets
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    decode_token_safe,
    hash_password,
    password_policy_violation,
    verify_password,
)
from app.modules.sistema.bitacora_service import (
    AUDIT_ACTION_LOGIN,
    AUDIT_ACTION_LOGOUT,
    AUDIT_ACTION_ROLE_ASSIGN,
    AUDIT_ACTION_ROLE_CREATE,
    AUDIT_ACTION_ROLE_DELETE,
    AUDIT_ACTION_ROLE_UNASSIGN,
    AUDIT_ACTION_ROLE_UPDATE,
    AUDIT_ACTION_USUARIO_CREAR,
    AUDIT_ACTION_USUARIO_DESACTIVAR,
    AUDIT_ACTION_USUARIO_EDITAR,
    AUDIT_MODULE_USER_AUTH,
    registrar_bitacora,
)
from app.modules.sistema.logger import revocar_token, token_esta_revocado
from app.modules.usuario_autenticacion.models import Rol, Usuario, usuario_rol
from app.modules.usuario_autenticacion.roles_service import count_users_with_role, load_usuario_with_roles
from app.modules.usuario_autenticacion.permisos import (
    PERMISOS_CATALOGO,
    PERMISOS_VALIDOS,
    dump_permisos,
    parse_permisos,
)
from app.modules.usuario_autenticacion.schemas import (
    LoginRequest,
    MeResponse,
    PasswordChangeRequest,
    PermisoCatalogoItem,
    ProfileSelfUpdateRequest,
    RolCreateRequest,
    RolItem,
    RolUpdateRequest,
    TokenResponse,
    UsuarioCreateRequest,
    UsuarioCreateResponse,
    UsuarioListItem,
    UsuarioListResponse,
    UsuarioRolAssignRequest,
    UsuarioUpdateRequest,
)
from app.modules.usuario_autenticacion.services import (
    enviar_credenciales_nuevo_usuario_sync,
    get_current_user,
    require_admin,
)

auth_router = APIRouter(prefix="/auth", tags=["autenticacion"])
logout_bearer = HTTPBearer()
users_router = APIRouter(prefix="/admin/users", tags=["admin-usuarios"])
roles_router = APIRouter(prefix="/admin", tags=["admin-usuarios"])

SYSTEM_ROLE_NAMES = frozenset({"Administrador", "Cliente", "Tecnico"})


def _to_rol_item(r: Rol) -> RolItem:
    return RolItem(
        id=r.id,
        nombre=r.nombre,
        descripcion=r.descripcion,
        permisos=parse_permisos(r.permisos_json),
    )


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


def _to_me_response(user: Usuario) -> MeResponse:
    return MeResponse(
        id=user.id,
        nombre=user.nombre,
        apellido=user.apellido,
        email=user.email,
        telefono=user.telefono,
        estado=user.estado,
        roles=[r.nombre for r in user.roles],
        foto_perfil=user.fotoperfil,
        fecha_registro=user.fecharegistro,
    )


@auth_router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    email_norm = str(req.email).strip().lower()
    stmt = select(Usuario).options(selectinload(Usuario.roles)).where(func.lower(Usuario.email) == email_norm)
    user = db.execute(stmt).scalar_one_or_none()
    ip = _client_ip(request)

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    if (user.estado or "").strip().lower() != "activo":
        registrar_bitacora(
            db,
            id_usuario=user.id,
            modulo=AUDIT_MODULE_USER_AUTH,
            accion=AUDIT_ACTION_LOGIN,
            ip=ip,
            resultado="DENEGADO_INACTIVO",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta deshabilitada")

    if not verify_password(req.password, user.passwordhash):
        registrar_bitacora(
            db,
            id_usuario=user.id,
            modulo=AUDIT_MODULE_USER_AUTH,
            accion=AUDIT_ACTION_LOGIN,
            ip=ip,
            resultado="FALLO_CREDENCIAL",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    roles = [r.nombre for r in user.roles]
    token, _jti, _exp = create_access_token(subject=str(user.id), roles=roles)
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo=AUDIT_MODULE_USER_AUTH,
        accion=AUDIT_ACTION_LOGIN,
        ip=ip,
        resultado="OK",
    )
    db.commit()

    redirect_hint = "web" if "Administrador" in roles else "mobile"
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
        roles=roles,
        redirect_hint=redirect_hint,
    )


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(logout_bearer),
) -> None:
    payload = decode_token_safe(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    sub = payload.get("sub")
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    user_id = int(sub)
    ip = _client_ip(request)
    exp_dt = datetime.fromtimestamp(int(exp), timezone.utc) if exp else datetime.now(timezone.utc)
    if jti and not token_esta_revocado(db, jti):
        revocar_token(db, jti=jti, expiracion=exp_dt)
        logout_outcome = "OK"
    else:
        logout_outcome = "SIN_JTI" if not jti else "TOKEN_YA_REVOCADO"
    registrar_bitacora(
        db,
        id_usuario=user_id,
        modulo=AUDIT_MODULE_USER_AUTH,
        accion=AUDIT_ACTION_LOGOUT,
        ip=ip,
        resultado=logout_outcome,
    )
    db.commit()


@auth_router.get("/me", response_model=MeResponse)
def me(user: Usuario = Depends(get_current_user)) -> MeResponse:
    return _to_me_response(user)


@auth_router.patch("/me", response_model=MeResponse)
def update_my_profile(
    body: ProfileSelfUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> MeResponse:
    ip = _client_ip(request)
    raw = body.model_dump(exclude_unset=True)
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay campos para actualizar.")
    if "nombre" in raw and raw["nombre"] is not None:
        user.nombre = str(raw["nombre"]).strip()
    if "apellido" in raw and raw["apellido"] is not None:
        user.apellido = str(raw["apellido"]).strip()
    if "telefono" in raw:
        t = raw["telefono"]
        user.telefono = str(t).strip() if t is not None and str(t).strip() else None
    if "foto_perfil" in raw:
        fp = raw["foto_perfil"]
        user.fotoperfil = str(fp).strip() if fp is not None and str(fp).strip() else None
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo="usuario_autenticacion",
        accion="PERFIL_ACTUALIZAR",
        ip=ip,
        resultado="OK",
    )
    db.commit()
    db.refresh(user)
    return _to_me_response(user)


@auth_router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(
    body: PasswordChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> Response:
    ip = _client_ip(request)
    if body.password_nueva != body.password_confirmacion:
        registrar_bitacora(
            db,
            id_usuario=user.id,
            modulo="usuario_autenticacion",
            accion="CAMBIO_PASSWORD",
            ip=ip,
            resultado="CONTRASEÑAS_NO_COINCIDEN",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las contraseñas nuevas no coinciden.",
        )
    policy_msg = password_policy_violation(body.password_nueva)
    if policy_msg:
        registrar_bitacora(
            db,
            id_usuario=user.id,
            modulo="usuario_autenticacion",
            accion="CAMBIO_PASSWORD",
            ip=ip,
            resultado="POLITICA_NO_CUMPLIDA",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=policy_msg)
    if not verify_password(body.password_actual, user.passwordhash):
        registrar_bitacora(
            db,
            id_usuario=user.id,
            modulo="usuario_autenticacion",
            accion="CAMBIO_PASSWORD",
            ip=ip,
            resultado="PASSWORD_ACTUAL_INCORRECTA",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta.",
        )
    user.passwordhash = hash_password(body.password_nueva)
    registrar_bitacora(
        db,
        id_usuario=user.id,
        modulo="usuario_autenticacion",
        accion="CAMBIO_PASSWORD",
        ip=ip,
        resultado="OK",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@roles_router.get("/roles/permisos-catalogo", response_model=list[PermisoCatalogoItem])
def permisos_catalogo(_admin: Usuario = Depends(require_admin)) -> list[PermisoCatalogoItem]:
    return [PermisoCatalogoItem(codigo=c, descripcion=d) for c, d in PERMISOS_CATALOGO]


@roles_router.get("/roles", response_model=list[RolItem])
def list_roles(db: Session = Depends(get_db), _admin: Usuario = Depends(require_admin)) -> list[RolItem]:
    rows = db.execute(select(Rol).order_by(Rol.id)).scalars().all()
    return [_to_rol_item(r) for r in rows]


@roles_router.post("/roles", response_model=RolItem, status_code=status.HTTP_201_CREATED)
def create_rol(
    body: RolCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_admin),
) -> RolItem:
    ip = _client_ip(request)
    nombre_norm = body.nombre.strip()
    invalid = [p for p in body.permisos if p not in PERMISOS_VALIDOS]
    if invalid:
        registrar_bitacora(
            db,
            id_usuario=admin.id,
            modulo=AUDIT_MODULE_USER_AUTH,
            accion=AUDIT_ACTION_ROLE_CREATE,
            ip=ip,
            resultado="PERMISOS_INVALIDOS",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permisos inválidos: " + ", ".join(invalid),
        )
    dup = db.execute(select(Rol.id).where(func.lower(Rol.nombre) == nombre_norm.lower())).first()
    if dup is not None:
        registrar_bitacora(
            db,
            id_usuario=admin.id,
            modulo=AUDIT_MODULE_USER_AUTH,
            accion=AUDIT_ACTION_ROLE_CREATE,
            ip=ip,
            resultado="NOMBRE_DUPLICADO",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un rol con ese nombre")
    desc = body.descripcion.strip() if body.descripcion else None
    r = Rol(nombre=nombre_norm, descripcion=desc, permisos_json=dump_permisos(body.permisos))
    db.add(r)
    try:
        db.flush()
        registrar_bitacora(
            db,
            id_usuario=admin.id,
            modulo=AUDIT_MODULE_USER_AUTH,
            accion=AUDIT_ACTION_ROLE_CREATE,
            ip=ip,
            resultado=f"OK:r={r.id}"[:50],
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un rol con ese nombre") from None
    db.refresh(r)
    return _to_rol_item(r)


@roles_router.patch("/roles/{rol_id}", response_model=RolItem)
def update_rol(
    rol_id: int,
    body: RolUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_admin),
) -> RolItem:
    ip = _client_ip(request)
    r = db.get(Rol, rol_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    changed = False
    if body.nombre is not None:
        nuevo = body.nombre.strip()
        if nuevo != r.nombre and r.nombre in SYSTEM_ROLE_NAMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede cambiar el nombre de un rol del sistema",
            )
        otro = db.execute(
            select(Rol.id).where(func.lower(Rol.nombre) == nuevo.lower(), Rol.id != rol_id),
        ).first()
        if otro is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un rol con ese nombre")
        if nuevo != r.nombre:
            changed = True
        r.nombre = nuevo
    if body.descripcion is not None:
        new_d = body.descripcion.strip() or None
        if new_d != r.descripcion:
            changed = True
        r.descripcion = new_d
    if body.permisos is not None:
        invalid = [p for p in body.permisos if p not in PERMISOS_VALIDOS]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permisos inválidos: " + ", ".join(invalid),
            )
        new_p = dump_permisos(body.permisos)
        if new_p != r.permisos_json:
            changed = True
        r.permisos_json = new_p
    if changed:
        try:
            registrar_bitacora(
                db,
                id_usuario=admin.id,
                modulo=AUDIT_MODULE_USER_AUTH,
                accion=AUDIT_ACTION_ROLE_UPDATE,
                ip=ip,
                resultado=f"OK:r={rol_id}"[:50],
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un rol con ese nombre") from None
    db.refresh(r)
    return _to_rol_item(r)


@roles_router.delete("/roles/{rol_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rol(
    rol_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_admin),
) -> None:
    ip = _client_ip(request)
    r = db.get(Rol, rol_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    if r.nombre in SYSTEM_ROLE_NAMES:
        registrar_bitacora(
            db,
            id_usuario=admin.id,
            modulo=AUDIT_MODULE_USER_AUTH,
            accion=AUDIT_ACTION_ROLE_DELETE,
            ip=ip,
            resultado="ROL_SISTEMA",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rol del sistema no eliminable",
        )
    n_users = count_users_with_role(db, rol_id)
    if n_users > 0:
        registrar_bitacora(
            db,
            id_usuario=admin.id,
            modulo=AUDIT_MODULE_USER_AUTH,
            accion=AUDIT_ACTION_ROLE_DELETE,
            ip=ip,
            resultado="EN_USO",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar, hay usuarios asignados",
        )
    db.delete(r)
    registrar_bitacora(
        db,
        id_usuario=admin.id,
        modulo=AUDIT_MODULE_USER_AUTH,
        accion=AUDIT_ACTION_ROLE_DELETE,
        ip=ip,
        resultado=f"OK:r={rol_id}"[:50],
    )
    db.commit()


def _to_item(u: Usuario) -> UsuarioListItem:
    return UsuarioListItem(
        id=u.id,
        nombre=u.nombre,
        apellido=u.apellido,
        email=u.email,
        telefono=u.telefono,
        estado=u.estado,
        roles=[r.nombre for r in u.roles],
    )


@users_router.get("", response_model=UsuarioListResponse)
def list_users(
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(require_admin),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(description="Filtro por nombre, apellido o email")] = None,
    id_rol: Annotated[int | None, Query(description="Filtrar por id de rol")] = None,
) -> UsuarioListResponse:
    stmt = select(Usuario).options(selectinload(Usuario.roles))
    filt = None
    if q and q.strip():
        term = f"%{q.strip()}%"
        filt = or_(
            Usuario.nombre.ilike(term),
            Usuario.apellido.ilike(term),
            Usuario.email.ilike(term),
        )
        stmt = stmt.where(filt)
    if id_rol is not None:
        stmt = stmt.join(usuario_rol).where(usuario_rol.c.id_rol == id_rol).distinct()
    if id_rol is None:
        count_base = select(func.count()).select_from(Usuario)
        if filt is not None:
            count_base = count_base.where(filt)
    else:
        count_base = select(func.count(func.distinct(Usuario.id))).select_from(Usuario).join(usuario_rol).where(
            usuario_rol.c.id_rol == id_rol
        )
        if filt is not None:
            count_base = count_base.where(filt)
    total = int(db.execute(count_base).scalar_one())
    skip = (page - 1) * page_size
    stmt = stmt.offset(skip).limit(page_size)
    rows = db.execute(stmt).scalars().unique().all()
    return UsuarioListResponse(
        items=[_to_item(u) for u in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@users_router.get("/{user_id}", response_model=UsuarioListItem)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(require_admin),
) -> UsuarioListItem:
    u = db.execute(select(Usuario).options(selectinload(Usuario.roles)).where(Usuario.id == user_id)).scalar_one_or_none()
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return _to_item(u)


@users_router.post("/{user_id}/roles", response_model=UsuarioListItem)
def assign_user_role(
    user_id: int,
    body: UsuarioRolAssignRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_admin),
) -> UsuarioListItem:
    u = load_usuario_with_roles(db, user_id)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    rol = db.get(Rol, body.id_rol)
    if rol is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol inválido")
    prev_ids = [r.id for r in u.roles]
    if len(prev_ids) == 1 and prev_ids[0] == body.id_rol:
        return _to_item(u)
    ip = _client_ip(request)
    u.roles.clear()
    u.roles.append(rol)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No se pudo actualizar el rol") from None
    for oid in prev_ids:
        registrar_bitacora(
            db,
            id_usuario=admin.id,
            modulo=AUDIT_MODULE_USER_AUTH,
            accion=AUDIT_ACTION_ROLE_UNASSIGN,
            ip=ip,
            resultado=f"u={user_id}:r={oid}"[:50],
        )
    registrar_bitacora(
        db,
        id_usuario=admin.id,
        modulo=AUDIT_MODULE_USER_AUTH,
        accion=AUDIT_ACTION_ROLE_ASSIGN,
        ip=ip,
        resultado=f"u={user_id}:r={body.id_rol}"[:50],
    )
    db.commit()
    db.refresh(u)
    return _to_item(u)


@users_router.delete("/{user_id}/roles/{rol_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_user_role(
    user_id: int,
    rol_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_admin),
) -> None:
    u = load_usuario_with_roles(db, user_id)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if db.get(Rol, rol_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    to_remove = next((r for r in u.roles if r.id == rol_id), None)
    if to_remove is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario no tiene ese rol asignado",
        )
    if len(u.roles) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario debe conservar al menos un rol",
        )
    u.roles.remove(to_remove)
    registrar_bitacora(
        db,
        id_usuario=admin.id,
        modulo=AUDIT_MODULE_USER_AUTH,
        accion=AUDIT_ACTION_ROLE_UNASSIGN,
        ip=_client_ip(request),
        resultado=f"u={user_id}:r={rol_id}"[:50],
    )
    db.commit()


@users_router.post("", response_model=UsuarioCreateResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UsuarioCreateRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_admin),
) -> UsuarioCreateResponse:
    email_norm = str(body.email).strip().lower()
    rol = db.get(Rol, body.id_rol)
    if rol is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol inválido")

    pw = (body.password or "").strip()
    pwc = (body.password_confirmacion or "").strip()
    enviar_correo = True
    if pw or pwc:
        if not pw or not pwc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Completá contraseña y confirmación",
            )
        if pw != pwc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Las contraseñas no coinciden",
            )
        policy_msg = password_policy_violation(pw)
        if policy_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=policy_msg)
        password_plano = pw
        enviar_correo = False
    else:
        password_plano = secrets.token_urlsafe(10)
    u = Usuario(
        nombre=body.nombre.strip(),
        apellido=body.apellido.strip(),
        email=email_norm,
        passwordhash=hash_password(password_plano),
        telefono=body.telefono.strip() if body.telefono else None,
        estado="Activo",
    )
    u.roles.append(rol)
    db.add(u)
    ip = _client_ip(request)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        registrar_bitacora(
            db,
            id_usuario=admin.id,
            modulo=AUDIT_MODULE_USER_AUTH,
            accion=AUDIT_ACTION_USUARIO_CREAR,
            ip=ip,
            resultado="EMAIL_DUPLICADO",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email ya registrado") from None
    registrar_bitacora(
        db,
        id_usuario=admin.id,
        modulo=AUDIT_MODULE_USER_AUTH,
        accion=AUDIT_ACTION_USUARIO_CREAR,
        ip=ip,
        resultado=f"OK:t={u.id}"[:50],
    )
    registrar_bitacora(
        db,
        id_usuario=admin.id,
        modulo=AUDIT_MODULE_USER_AUTH,
        accion=AUDIT_ACTION_ROLE_ASSIGN,
        ip=ip,
        resultado=f"u={u.id}:r={rol.id}"[:50],
    )
    db.commit()
    db.refresh(u)

    nombre = f"{u.nombre} {u.apellido}".strip()
    if enviar_correo:
        background_tasks.add_task(
            enviar_credenciales_nuevo_usuario_sync,
            destino=u.email,
            password_plano=password_plano,
            nombre=nombre,
        )
    return UsuarioCreateResponse(
        id=u.id,
        email=u.email,
        password_generada=password_plano,
        roles=[r.nombre for r in u.roles],
    )


@users_router.patch("/{user_id}", response_model=UsuarioListItem)
def update_user(
    user_id: int,
    body: UsuarioUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_admin),
) -> UsuarioListItem:
    u = db.execute(select(Usuario).options(selectinload(Usuario.roles)).where(Usuario.id == user_id)).scalar_one_or_none()
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    prev_rid = u.roles[0].id if u.roles else None
    prev = (
        u.nombre,
        u.apellido,
        u.telefono,
        u.estado,
        u.email,
        u.passwordhash,
        prev_rid,
    )

    if body.nombre is not None:
        u.nombre = body.nombre.strip()
    if body.apellido is not None:
        u.apellido = body.apellido.strip()
    if body.telefono is not None:
        u.telefono = body.telefono.strip() or None
    if body.estado is not None:
        u.estado = body.estado.strip()
    if body.email is not None:
        u.email = str(body.email).strip().lower()
    if body.id_rol is not None:
        rol = db.get(Rol, body.id_rol)
        if rol is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol inválido")
        u.roles.clear()
        u.roles.append(rol)

    pn = (body.password_nueva or "").strip()
    pnc = (body.password_confirmacion or "").strip()
    if pn or pnc:
        if not pn or not pnc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Completá contraseña nueva y confirmación",
            )
        if pn != pnc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Las contraseñas no coinciden",
            )
        policy_msg = password_policy_violation(pn)
        if policy_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=policy_msg)
        u.passwordhash = hash_password(pn)

    curr_rid = u.roles[0].id if u.roles else None
    curr = (
        u.nombre,
        u.apellido,
        u.telefono,
        u.estado,
        u.email,
        u.passwordhash,
        curr_rid,
    )
    if prev == curr:
        db.commit()
        db.refresh(u)
        return _to_item(u)

    ip = _client_ip(request)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        registrar_bitacora(
            db,
            id_usuario=admin.id,
            modulo=AUDIT_MODULE_USER_AUTH,
            accion=AUDIT_ACTION_USUARIO_EDITAR,
            ip=ip,
            resultado="EMAIL_DUPLICADO",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email ya registrado") from None

    other_changed = prev[0:6] != curr[0:6]
    rol_changed = prev[6] != curr[6]
    if other_changed:
        registrar_bitacora(
            db,
            id_usuario=admin.id,
            modulo=AUDIT_MODULE_USER_AUTH,
            accion=AUDIT_ACTION_USUARIO_EDITAR,
            ip=ip,
            resultado=f"OK:t={user_id}"[:50],
        )
    if rol_changed:
        if prev_rid is not None:
            registrar_bitacora(
                db,
                id_usuario=admin.id,
                modulo=AUDIT_MODULE_USER_AUTH,
                accion=AUDIT_ACTION_ROLE_UNASSIGN,
                ip=ip,
                resultado=f"u={user_id}:r={prev_rid}"[:50],
            )
        if curr_rid is not None:
            registrar_bitacora(
                db,
                id_usuario=admin.id,
                modulo=AUDIT_MODULE_USER_AUTH,
                accion=AUDIT_ACTION_ROLE_ASSIGN,
                ip=ip,
                resultado=f"u={user_id}:r={curr_rid}"[:50],
            )
    if other_changed or rol_changed:
        db.commit()
    db.refresh(u)
    return _to_item(u)


@users_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_admin),
) -> None:
    u = db.get(Usuario, user_id)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    u.estado = "Inactivo"
    registrar_bitacora(
        db,
        id_usuario=admin.id,
        modulo=AUDIT_MODULE_USER_AUTH,
        accion=AUDIT_ACTION_USUARIO_DESACTIVAR,
        ip=_client_ip(request),
        resultado=f"OK:t={user_id}"[:50],
    )
    db.commit()
