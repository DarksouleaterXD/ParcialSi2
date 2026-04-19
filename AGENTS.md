# Proyecto: Plataforma Inteligente de Atención de Emergencias Vehiculares

## 1. Descripción del Negocio
Sistema para conectar conductores con problemas vehiculares (batería, pinchazo, choque) con talleres mecánicos. La plataforma usa IA de forma central en el flujo para transcribir audios del usuario, analizar fotos de daños y clasificar el incidente automáticamente, sugiriendo el mejor taller disponible basado en cercanía y especialidad.

## 2. Actores del Sistema
1. **Cliente (App Móvil - Flutter):** Reporta emergencias, envía ubicación, fotos, audio. Ve el seguimiento del auxilio y paga.
2. **Administrador/Taller (App Web - Angular):** Recibe sugerencias de incidentes, acepta/rechaza, despacha mecánicos y cobra.
3. **Mecánico (Rol derivado):** Va al lugar del hecho, cambia estados y finaliza el servicio.
4. **Sistema / Motor IA (Backend - FastAPI):** Actor secundario que procesa transcripciones, clasifica imágenes, calcula distancias y sugiere asignaciones.

## 3. Stack Tecnológico
- **Backend:** Python + FastAPI
- **Base de Datos:** PostgreSQL (13 tablas relacionales)
- **Frontend (Web):** Angular (Arquitectura Core/Shared/Features)
- **Mobile (Cliente):** Flutter (Arquitectura Feature-First / Clean Architecture)

## 4. Estructura de Paquetes UML (Dominio)
El código en LOS TRES PROYECTOS debe respetar estrictamente esta división de 5 módulos en español:
1. `usuario_autenticacion` (Login, Registro, Perfil, Roles, Vehículos)
2. `taller_tecnico` (Talleres, Mecánicos, Especialidades)
3. `incidentes_servicios` (Reporte, Evidencias, Asignaciones, Motor IA)
4. `pagos` (Transacciones, Comisiones del 10%, Calificaciones)
5. `sistema` (Bitácora, Notificaciones Push)

## 5. Base de Datos (PostgreSQL)
Modelo relacional (script [Taller_Inteligente.sql](Taller_Inteligente.sql)):
- Independientes: `Usuario`, `Rol`, `Especialidad`
- Nivel 1: `Usuario_Rol`, `Vehiculo`, `Taller`
- Nivel 2: `Taller_Especialidad`, `Mecanico_Taller`, `Incidente`, `Notificacion`, `Bitacora`
- Nivel 3: `Evidencia`, `Taller_Candidato`, `Mensaje_Incidente`, `AsignacionServicio`
- Nivel 4: `Pago`, `Calificacion`
- Autenticación: `TokenRevocado` (JWT `jti` invalidado en logout; limpiar expirados periódicamente)

Semillas iniciales (roles, admin, especialidades de ejemplo): ejecutar [database/Taller_Inteligente_seeds.sql](database/Taller_Inteligente_seeds.sql) después del script principal.

## 6. Estado Actual del Desarrollo y Reglas
- **FASE ACTUAL:** Login y autenticación estables; **bitácora** con backend listo y **frontend web de consulta** en el paquete `sistema`.
- **RESTRICCIÓN:** NO implementar lógica de incidentes ni IA hasta alinear la fase acordada. El login debe seguir operativo en las tres plataformas.
- **REGLA DE CÓDIGO:** Mantener el nombre de los paquetes de dominio en español, pero usar convenciones de framework en inglés (ej: `login.screen.dart`, `auth.service.ts`, `models.py`).
- **REGLA DE IA:** La IA no es un módulo aislado, es parte del flujo principal de `incidentes_servicios`.

### Bitácora (auditoría del sistema)
- **Dominio:** Paquete `sistema` en código; entidad `Bitacora` en PostgreSQL. Login y logout quedan registrados en bitácora; el administrador consulta el historial desde la web.
- **Backend (implementado):**
  - Persistencia y contrato tipado en `backend_emergencias/app/modules/sistema/bitacora_service.py` (`BitacoraEventCreate`, `record_audit_event`); revocación JWT en `sistema/logger.py`.
  - Login y logout escriben filas con `modulo=usuario_autenticacion` y acciones `LOGIN` / `LOGOUT` (sin guardar contraseña ni token completo).
  - API solo **Administrador:** `GET /api/admin/bitacora` (paginado, query: `page`, `page_size`, `fecha`, `usuario`, `modulo`, `accion`) y `GET /api/admin/bitacora/{id}`. Los filtros `modulo` y `accion` son **coincidencia exacta** con la columna (p. ej. `usuario_autenticacion`, `LOGIN`), no búsqueda parcial.
- **Frontend web (en curso):** pantalla de consulta en `frontend_talleres_web/src/app/features/sistema/bitacora/` (`BitacoraApiService`, página standalone, navegación bajo el acordeón **Sistema**). Cliente móvil Flutter: pendiente cuando corresponda la fase.

## 7. Reglas de Estilo UI/UX (Cursor Guidelines)
Para que las herramientas de IA generen código con un estándar visual premium y profesional:

### Estándares Generales
- El código debe estar en inglés (variables, métodos, clases), pero el dominio y las carpetas de los módulos en español (ej: `usuario_autenticacion`).
- No usar comentarios obvios. Solo documentar decisiones de negocio o flujos complejos.

### Frontend Web (Angular 17+)
- Usar componentes Standalone siempre que sea posible.
- **Estilo y CSS:** Usar EXCLUSIVAMENTE Tailwind CSS. Prohibido usar CSS puro o Bootstrap.
- **Diseño Profesional:** Estilo minimalista y limpio (tipo Vercel/Stripe).
  - Usar colores neutros de Tailwind (`slate` o `zinc`) para fondos y textos.
  - Usar **naranja** (`orange-500` / `orange-600`) como color primario para CTAs y acentos, alineado al panel (borde lateral y botones activos).
  - Componentes de UI: Bordes redondeados (`rounded-xl`), sombras suaves (`shadow-sm`, `shadow-md`), y mucho espacio en blanco (`padding` y `gap`).
  - Inputs: Estados claros (focus, error, disabled) usando `focus:ring-2`, `focus:border-orange-500`.
- **Estado:** Usar Signals (`signal()`, `computed()`) para el manejo de estado reactivo local.
- **Validaciones:** Formularios reactivos (`ReactiveFormsModule`) con feedback visual en tiempo real.

### Mobile (Flutter)
- Usar **Material 3** (`useMaterial3: true`).
- Implementar un `ColorScheme` dinámico o basado en un color semilla (Seed Color) que coincida con la paleta de la web.
- Evitar los "Spinners" infinitos. Usar Skeleton Loaders (Shimmer effect) para tiempos de carga en listas.
- Formularios limpios con validación `TextFormField` e iconografía clara.

## 8. Habilidades (Skills) a cargar
- Al trabajar en Backend: Cargar contexto de FastAPI, SQLAlchemy y JWT.
- Al trabajar en Frontend: Cargar contexto de Angular 17+, Lazy Loading y Guards.
- Al trabajar en Mobile: Cargar contexto de Flutter, BLoC/Provider y Dio.

## 8. Inicialización del Proyecto (Setup Local)
Para levantar los entornos de desarrollo en Windows (y que el Agente o vos los prueben), seguir estrictamente estos pasos:

### 1. Base de Datos (PostgreSQL)
1. Levantar el servicio de PostgreSQL localmente.
2. Crear una base de datos vacía (ej: `emergencias_db`).
3. Ejecutar [Taller_Inteligente.sql](Taller_Inteligente.sql) y luego [database/Taller_Inteligente_seeds.sql](database/Taller_Inteligente_seeds.sql) (roles, admin inicial, especialidades de ejemplo).

### 2. Backend (FastAPI)
```powershell
cd backend_emergencias
python -m venv venv
.\venv\Scripts\activate
# Instalar dependencias base
pip install -r requirements.txt
# Levantar el server en modo dev
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend (Angular Web)
```powershell
cd frontend_talleres_web
# Solo la primera vez (asumiendo que tenés Node y Angular CLI instalados)
npm install
# Levantar servidor
ng serve -o
```

### 4. Mobile (Flutter Cliente)
```powershell
cd app_emergencias_cliente
# Si falta la carpeta android/ (u otras plataformas), generar metadatos del SDK:
flutter create . --project-name app_emergencias_cliente
flutter pub get
# API en emulador Android: usar host 10.0.2.2
flutter run --dart-define=API_BASE=http://10.0.2.2:8000/api
# Chrome / Windows con backend local:
flutter run --dart-define=API_BASE=http://localhost:8000/api
```

## 9. Flujos de dominio (resumen)

Reglas arquitectónicas que el código debe respetar:

1. **Usuarios (administración):** exclusivo administrador. Validación de email único, contraseña generada y envío de credenciales. La entidad `Usuario` incluye los campos del modelo relacional (`id`, `apellido`, `email`, `password`, `telefono`, `foto`, `latitud`, `longitud`, `fecharegistro`). Las altas, bajas y cambios relevantes deben reflejarse en `Bitacora`. La gestión de roles enlaza con esta misma trazabilidad.
2. **Inicio de sesión:** administrador, cliente y técnico. Credenciales + JWT; **login y logout** deben registrarse en `Bitacora`; la app redirige según el rol.
3. **Roles:** exclusivo administrador. Permisos asociados; no eliminar un rol si tiene usuarios asignados. Las acciones sobre roles quedan auditadas en `Bitacora`.

## 10. App móvil Flutter — cliente (`app_emergencias_cliente`)

### Alcance y restricciones
- **Solo** flujos del **cliente** (conductor) en esta línea de trabajo incremental. No se implementa UI de administración web, gestión de talleres, técnicos ni roles en el móvil.
- Si un usuario **Administrador** inicia sesión en la app, se muestra un aviso y **cerrar sesión**; la gestión es en la web.
- **Dominio en español** en rutas de carpetas (`usuario_autenticacion`, etc.); **código técnico en inglés** (clases, métodos, variables).
- **HTTP:** paquete `http` + **sesión** en `flutter_secure_storage`. **Navegación:** `Navigator` (sin go_router obligatorio).
- **API base:** constante `kApiBase` en `lib/core/api_config.dart`, sobreescribible con:
  `flutter run --dart-define=API_BASE=http://10.0.2.2:8000/api`
- **No inventar endpoints:** antes de cada pantalla, contrastar con `backend_emergencias` (routers bajo prefijo `/api` en `app/main.py`). Si no existe ruta, dejar **TODO** explícito en código o checklist, sin datos mock que simulen negocio.

### Estructura por feature (recomendada)
Bajo `lib/features/<paquete_dominio>/`:
- `data/` — llamadas HTTP, DTOs, implementación de repositorio.
- `domain/` — contratos, validaciones de dominio ligeras, entidades si aplica.
- `presentation/` — pantallas, widgets, estado local (`ChangeNotifier` / `ValueNotifier` / `StatefulWidget`).

**Core compartido** (`lib/core/`): configuración API, almacenamiento de token, cliente autenticado, parseo de errores FastAPI.

### Inicialización del proyecto móvil
```powershell
cd app_emergencias_cliente
flutter pub get
# Si falta plataforma:
flutter create . --project-name app_emergencias_cliente
flutter run --dart-define=API_BASE=http://localhost:8000/api
# Emulador Android → backend en la máquina host:
flutter run --dart-define=API_BASE=http://10.0.2.2:8000/api
```

### Roadmap casos de uso cliente (orden incremental)
| # | Área | Estado móvil |
|---|------|----------------|
| 1 | Inicio de sesión / sesión / logout | **Hecho:** validación de formulario alineada a política de contraseña del backend, mensajes por código HTTP, `GET /auth/me` al arranque para invalidar token revocado/expirado, `AuthorizedClient` listo para llamadas con Bearer y limpieza en 401. |
| 2 | Perfil de usuario | Pendiente: pantalla + `GET/PATCH /auth/me`. |
| 3 | Vehículos | Pendiente: CRUD vía `GET/POST/PATCH/DELETE /vehiculos` (JWT cliente). |
| 4 | Reportar emergencia | **Bloqueado** hasta existir API real en `incidentes_servicios` (hoy solo `GET /api/incidentes-servicios/health` stub). |
| 5 | Estado de solicitud | Idem incidentes: sin endpoints de lectura de incidente para cliente. |
| 6 | Cancelar solicitud | Idem. |
| 7 | Pagos | **Bloqueado:** `GET /api/pagos/health` stub; sin flujo de pago para cliente. |
| 8 | Calificaciones | Sin endpoints expuestos para cliente en el backend actual. |
| 9 | Notificaciones | Sin API de listado para cliente (bitácora es admin-only). |
| 10 | Historial de servicios | Depende de incidentes/pagos; no hay listado unificado aún. |

### Tabla técnica — endpoints útiles para cliente (verificados en backend)
| Necesidad | Método y ruta | Notas |
|-----------|----------------|--------|
| Login | `POST /api/auth/login` | Body JSON `email`, `password`. Respuesta: `access_token`, `roles`, `expires_in`, `redirect_hint`. |
| Validar sesión / perfil | `GET /api/auth/me` | Bearer. Usado al arranque para descartar sesión inválida. |
| Logout | `POST /api/auth/logout` | Bearer; revoca `jti` en servidor. |
| Actualizar perfil | `PATCH /api/auth/me` | Bearer; campos según `ProfileSelfUpdateRequest` en backend. |
| Cambiar contraseña | `POST /api/auth/me/change-password` | Bearer; cuerpo según backend. |
| Listar vehículos | `GET /api/vehiculos?page=&page_size=` | Bearer; cliente solo ve los propios. |
| Crear vehículo | `POST /api/vehiculos` | Bearer; **no** admin. |
| Ver / editar / borrar vehículo | `GET`, `PATCH`, `DELETE` `/api/vehiculos/{id}` | Bearer; reglas de acceso en router de vehículos. |
| Incidentes / pagos / notificaciones cliente | — | **No implementados** para consumo cliente en la versión actual del API. |

### Archivos clave tras el primer incremento (login)
- `lib/core/api_errors.dart` — mensaje desde `detail` de FastAPI.
- `lib/core/auth_api.dart` — `login`, `logout`, `isSessionValid` (`/auth/me`).
- `lib/core/authorized_client.dart` — requests autenticadas; en **401** limpia `AuthStorage` y lanza `SessionExpiredException`.
- `lib/core/auth_storage.dart` — token + roles JSON.
- `lib/features/usuario_autenticacion/domain/login_validators.dart` — reglas alineadas a contraseña mínima 8 + letra + dígito.
- `lib/features/usuario_autenticacion/data/auth_remote_data_source.dart` — capa fina sobre `AuthApi` (reutilizable en tests).
- `lib/features/usuario_autenticacion/presentation/*` — pantallas de login, home cliente/técnico y aviso admin.
- `lib/main.dart` — `MaterialApp` + arranque con validación de token.

### Calidad UI (Flutter)
- Material 3; semilla naranja alineada a la web (`ColorScheme.fromSeed` ~ `#F97316`).
- Formularios con feedback inmediato; evitar spinners eternos en listas (estados vacío / error / carga acotada).