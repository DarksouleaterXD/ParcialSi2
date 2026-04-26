-- =========================================================================
-- SCRIPT DE CREACIÓN DE BASE DE DATOS: PLATAFORMA DE EMERGENCIAS (POSTGRESQL)
-- =========================================================================

-- ==========================================
-- 1. TABLAS INDEPENDIENTES (Sin Foráneas)
-- ==========================================

CREATE TABLE Usuario (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    passwordHash VARCHAR(255) NOT NULL,
    telefono VARCHAR(20),
    fotoPerfil VARCHAR(255),
    estado VARCHAR(50) DEFAULT 'Activo',
    latitud DECIMAL(10, 8),
    longitud DECIMAL(11, 8),
    fechaRegistro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Rol (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    descripcion VARCHAR(255),
    permisos_json TEXT
);

-- ==========================================
-- 2. TABLAS INTERMEDIAS Y DEPENDIENTES (Nivel 1)
-- ==========================================

CREATE TABLE Usuario_Rol (
    id_usuario INT,
    id_rol INT,
    PRIMARY KEY (id_usuario, id_rol),
    FOREIGN KEY (id_usuario) REFERENCES Usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (id_rol) REFERENCES Rol(id) ON DELETE CASCADE
);

CREATE TABLE Vehiculo (
    id SERIAL PRIMARY KEY,
    id_usuario INT NOT NULL,
    placa VARCHAR(20) UNIQUE NOT NULL,
    marca VARCHAR(50) NOT NULL,
    modelo VARCHAR(50) NOT NULL,
    anio INT NOT NULL,
    color VARCHAR(30),
    tipoSeguro VARCHAR(50),
    fotoFrontal VARCHAR(255),
    FOREIGN KEY (id_usuario) REFERENCES Usuario(id) ON DELETE CASCADE
);

CREATE TABLE Taller (
    id SERIAL PRIMARY KEY,
    id_admin INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    direccion VARCHAR(255) NOT NULL,
    latitud DECIMAL(10, 8),
    longitud DECIMAL(11, 8),
    telefono VARCHAR(20),
    email VARCHAR(150),
    horario_atencion VARCHAR(120),
    disponibilidad BOOLEAN DEFAULT TRUE,
    capacidadMax INT NOT NULL,
    calificacion DECIMAL(3, 2) DEFAULT 0.00,
    FOREIGN KEY (id_admin) REFERENCES Usuario(id) ON DELETE RESTRICT
);

-- ==========================================
-- 3. DEPENDIENTES (Nivel 2)
-- ==========================================

CREATE TABLE Mecanico_Taller (
    id_usuario INT,
    id_taller INT,
    especialidad VARCHAR(30),
    PRIMARY KEY (id_usuario, id_taller),
    FOREIGN KEY (id_usuario) REFERENCES Usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (id_taller) REFERENCES Taller(id) ON DELETE CASCADE
);

CREATE TABLE Incidente (
    id SERIAL PRIMARY KEY,
    id_vehiculo INT NOT NULL,
    latitud DECIMAL(10, 8) NOT NULL,
    longitud DECIMAL(11, 8) NOT NULL,
    descripcion TEXT NOT NULL,
    fechaCreacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(50) DEFAULT 'Pendiente',
    categoria_ia VARCHAR(100),
    prioridad_ia VARCHAR(50),
    resumen_ia TEXT,
    confianza_ia DECIMAL(5, 2),
    tecnico_id INT,
    FOREIGN KEY (id_vehiculo) REFERENCES Vehiculo(id) ON DELETE RESTRICT,
    FOREIGN KEY (tecnico_id) REFERENCES Usuario(id) ON DELETE SET NULL
);

CREATE TABLE Notificacion (
    id SERIAL PRIMARY KEY,
    id_usuario INT NOT NULL,
    titulo VARCHAR(150) NOT NULL,
    mensaje TEXT NOT NULL,
    tipo VARCHAR(50),
    leida BOOLEAN DEFAULT FALSE,
    fechaHora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES Usuario(id) ON DELETE CASCADE
);

CREATE TABLE Bitacora (
    id SERIAL PRIMARY KEY,
    id_usuario INT NOT NULL,
    modulo VARCHAR(50) NOT NULL,
    accion VARCHAR(100) NOT NULL,
    ipOrigen VARCHAR(45),
    resultado VARCHAR(50),
    fechaHora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES Usuario(id) ON DELETE CASCADE
);

-- ==========================================
-- 4. DEPENDIENTES (Nivel 3)
-- ==========================================

CREATE TABLE Evidencia (
    id SERIAL PRIMARY KEY,
    id_incidente INT NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    urlArchivo VARCHAR(255) NOT NULL,
    textoExtraido_ia TEXT,
    analisisDano_ia TEXT,
    fechaSubida TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_incidente) REFERENCES Incidente(id) ON DELETE CASCADE
);

-- Idempotencia CU-09 (POST /incidentes y evidencias): misma clave + mismo cuerpo = replay sin duplicar.
-- Alineado con Alembic revision 004_idempotencia. Si ya migraste con Alembic, CREATE IF NOT EXISTS no hace nada.
CREATE TABLE IF NOT EXISTS idempotencia_registro (
    id SERIAL PRIMARY KEY,
    alcance VARCHAR(50) NOT NULL,
    clave VARCHAR(128) NOT NULL,
    id_usuario INT NOT NULL,
    huella_carga VARCHAR(64) NOT NULL,
    id_incidente_ref INT,
    id_evidencia_ref INT,
    fechacreacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expira_en TIMESTAMP NOT NULL,
    CONSTRAINT uq_idempotencia_usuario_alcance_clave UNIQUE (id_usuario, alcance, clave),
    FOREIGN KEY (id_usuario) REFERENCES Usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (id_incidente_ref) REFERENCES Incidente(id) ON DELETE CASCADE,
    FOREIGN KEY (id_evidencia_ref) REFERENCES Evidencia(id) ON DELETE CASCADE
);

CREATE TABLE AsignacionServicio (
    id SERIAL PRIMARY KEY,
    id_incidente INT NOT NULL,
    id_taller INT NOT NULL,
    id_mecanico INT NOT NULL,
    costoEstimado DECIMAL(10, 2),
    distanciaKm DECIMAL(8, 2),
    tiempoLlegada INT, -- Minutos
    estado VARCHAR(50) DEFAULT 'Asignado',
    fechaCreacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fechaAceptacion TIMESTAMP,
    fechaFin TIMESTAMP,
    motivoRechazo TEXT,
    trabajoRealizado TEXT,
    costoFinal DECIMAL(10, 2),
    obsMecanico TEXT,
    FOREIGN KEY (id_incidente) REFERENCES Incidente(id) ON DELETE RESTRICT,
    FOREIGN KEY (id_taller) REFERENCES Taller(id) ON DELETE RESTRICT,
    FOREIGN KEY (id_mecanico) REFERENCES Usuario(id) ON DELETE RESTRICT
);

-- ==========================================
-- 5. DEPENDIENTES (Nivel 4 - Finales)
-- ==========================================

CREATE TABLE Pago (
    id SERIAL PRIMARY KEY,
    id_asignacion INT UNIQUE NOT NULL, -- Relación 1 a 1
    montoTotal DECIMAL(10, 2) NOT NULL,
    comisionPlataforma DECIMAL(10, 2) NOT NULL,
    montoTaller DECIMAL(10, 2) NOT NULL,
    estado VARCHAR(50) DEFAULT 'Pendiente',
    metodoPago VARCHAR(50),
    idTransExterna VARCHAR(150),
    fechaPago TIMESTAMP,
    FOREIGN KEY (id_asignacion) REFERENCES AsignacionServicio(id) ON DELETE RESTRICT
);

CREATE TABLE Calificacion (
    id SERIAL PRIMARY KEY,
    id_asignacion INT UNIQUE NOT NULL, -- Relación 1 a 1
    puntuacion INT NOT NULL CHECK (puntuacion BETWEEN 1 AND 5),
    comentario TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_asignacion) REFERENCES AsignacionServicio(id) ON DELETE CASCADE
);
-- =========================================================================
-- PARCHE: TABLAS FALTANTES SEGÚN LOS REQUERIMIENTOS DEL PDF DEL PARCIAL
-- Ejecutar SÓLO si ya tenías la versión anterior de la base de datos
-- =========================================================================

-- 1. Agregar el campo de disponibilidad a los mecánicos (en la tabla Usuario existente)
ALTER TABLE Usuario 
ADD COLUMN disponibilidad_servicio BOOLEAN DEFAULT TRUE;

-- 2. Crear Catálogo de Especialidades (Para saber si el taller tiene grúa, eléctrico, etc)
CREATE TABLE Especialidad (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    descripcion TEXT
);

-- 3. Crear Tabla Intermedia Taller - Especialidad
CREATE TABLE Taller_Especialidad (
    id_taller INT REFERENCES Taller(id) ON DELETE CASCADE,
    id_especialidad INT REFERENCES Especialidad(id) ON DELETE CASCADE,
    PRIMARY KEY (id_taller, id_especialidad)
);

-- 4. Crear Tabla de Candidatos Sugeridos por IA (Paso previo a la Asignación)
CREATE TABLE Taller_Candidato (
    id SERIAL PRIMARY KEY,
    id_incidente INT NOT NULL REFERENCES Incidente(id) ON DELETE CASCADE,
    id_taller INT NOT NULL REFERENCES Taller(id) ON DELETE CASCADE,
    puntaje_ia DECIMAL(5,2),
    estado_sugerencia VARCHAR(50) DEFAULT 'Sugerido',
    fechaSugerencia TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Crear Tabla de Comunicación (Chat Cliente-Taller)
CREATE TABLE Mensaje_Incidente (
    id SERIAL PRIMARY KEY,
    id_incidente INT NOT NULL REFERENCES Incidente(id) ON DELETE CASCADE,
    id_remitente INT NOT NULL REFERENCES Usuario(id) ON DELETE CASCADE,
    mensaje TEXT NOT NULL,
    fechaEnvio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    leido BOOLEAN DEFAULT FALSE
);

-- Revocación de JWT (logout); limpiar filas con expiracion < now() periódicamente
CREATE TABLE TokenRevocado (
    jti VARCHAR(64) PRIMARY KEY,
    expiracion TIMESTAMP NOT NULL
);

CREATE INDEX idx_tokenrevocado_exp ON TokenRevocado(expiracion);

-- =========================================================================
-- FIN DEL SCRIPT POSTGRESQL
-- =========================================================================