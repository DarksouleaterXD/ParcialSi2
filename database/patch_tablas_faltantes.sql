-- =========================================================================
-- Parche: tablas que a veces faltan si la BD se creó con un script viejo.
-- Ejecutar en la base Taller_Inteligente (Query Tool) ANTES de re-ejecutar seeds.
-- Usa IF NOT EXISTS: seguro si alguna tabla ya existe.
-- =========================================================================

CREATE TABLE IF NOT EXISTS especialidad (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    descripcion VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS taller_especialidad (
    id_taller INT NOT NULL,
    id_especialidad INT NOT NULL,
    PRIMARY KEY (id_taller, id_especialidad),
    FOREIGN KEY (id_taller) REFERENCES taller(id) ON DELETE CASCADE,
    FOREIGN KEY (id_especialidad) REFERENCES especialidad(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS taller_candidato (
    id SERIAL PRIMARY KEY,
    id_incidente INT NOT NULL,
    id_taller INT NOT NULL,
    ordensugerencia INT,
    distanciakm DECIMAL(8, 2),
    FOREIGN KEY (id_incidente) REFERENCES incidente(id) ON DELETE CASCADE,
    FOREIGN KEY (id_taller) REFERENCES taller(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mensaje_incidente (
    id SERIAL PRIMARY KEY,
    id_incidente INT NOT NULL,
    id_usuario INT NOT NULL,
    mensaje TEXT NOT NULL,
    fechahora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_incidente) REFERENCES incidente(id) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tokenrevocado (
    jti VARCHAR(64) PRIMARY KEY,
    expiracion TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tokenrevocado_exp ON tokenrevocado(expiracion);
