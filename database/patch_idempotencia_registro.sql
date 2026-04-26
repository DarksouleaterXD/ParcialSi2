-- Parche: tabla idempotencia_registro (CU-09) si la base se creó solo con Taller_Inteligente.sql
-- anterior a esta columna. Ejecutar una vez contra emergencias_db:
--   psql -U postgres -d emergencias_db -f database/patch_idempotencia_registro.sql

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
