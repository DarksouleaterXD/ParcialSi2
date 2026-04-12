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
- **FASE ACTUAL:** Inicialización de arquitecturas.
- **RESTRICCIÓN:** SOLO implementar el módulo de `usuario_autenticacion` (específicamente el LOGIN). NO implementar lógica de incidentes ni IA hasta que el login esté 100% funcional en las 3 plataformas.
- **REGLA DE CÓDIGO:** Mantener el nombre de los paquetes de dominio en español, pero usar convenciones de framework en inglés (ej: `login.screen.dart`, `auth.service.ts`, `models.py`).
- **REGLA DE IA:** La IA no es un módulo aislado, es parte del flujo principal de `incidentes_servicios`.

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
  - Usar un color primario vibrante (ej: `indigo-600` o `blue-600`) para llamadas a la acción (CTAs).
  - Componentes de UI: Bordes redondeados (`rounded-xl`), sombras suaves (`shadow-sm`, `shadow-md`), y mucho espacio en blanco (`padding` y `gap`).
  - Inputs: Estados claros (focus, error, disabled) usando `focus:ring-2`, `focus:border-indigo-500`.
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

## 9. Casos de Uso Core y Flujos (Dominio)

Resumen de las reglas arquitectónicas derivadas de los Casos de Uso y diagramas de Robustez:

1. **CU01 - Gestionar Usuario**: Exclusivo para Administrador. Requiere validación de email único, generación automática de contraseña y envío de credenciales por correo electrónico. La entidad de Usuario debe incluir estrictamente los campos: `id`, `apellido`, `email`, `password`, `telefono`, `foto`, `latitud`, `longitud` y `fecharegistro`. Todas las acciones (crear, actualizar, eliminar) DEBEN registrarse en la entidad `Bitacora`. Este flujo incluye lógicamente CU03 (Roles) y CU08 (Bitácora).
2. **CU02 - Gestionar Inicio de Sesión**: Aplica para Administrador, Cliente y Mecánico (Técnico). Valida credenciales, genera el token JWT, registra de manera obligatoria el login y logout en la `Bitacora`, y redirecciona según el rol del usuario.
3. **CU03 - Gestionar Roles**: Exclusivo para Administrador. Gestiona roles y sus permisos asociados. Existe una restricción estricta: no se puede eliminar un rol si tiene usuarios asignados. Todas las acciones se registran en la `Bitacora`.