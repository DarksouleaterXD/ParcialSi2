-- Ejecutar en Neon / Render Postgres si POST /api/vehiculos falla con ProgrammingError
-- (columna inexistente en INSERT). Idempotente.

ALTER TABLE vehiculo ADD COLUMN IF NOT EXISTS tiposeguro VARCHAR(50);
ALTER TABLE vehiculo ADD COLUMN IF NOT EXISTS fotofrontal VARCHAR(255);
