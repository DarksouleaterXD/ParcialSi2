-- =========================================================================
-- Parche: incidente.tecnico_id (CU10 — asignación de técnico)
-- Ejecutar en la misma base que usa el backend (psql, pgAdmin, DBeaver…).
-- Idempotente: seguro si la columna o la FK ya existen.
-- =========================================================================
-- Motivo del error: el ORM (SQLAlchemy) y Taller_Inteligente.sql incluyen
-- tecnico_id, pero bases creadas con un script viejo no tienen la columna.
-- Alternativa: desde backend_emergencias con venv activo → alembic upgrade head
-- (revisión 005_incidente_tecnico).
-- =========================================================================

ALTER TABLE incidente
  ADD COLUMN IF NOT EXISTS tecnico_id INT;

ALTER TABLE incidente DROP CONSTRAINT IF EXISTS incidente_tecnico_id_fkey;

ALTER TABLE incidente
  ADD CONSTRAINT incidente_tecnico_id_fkey
  FOREIGN KEY (tecnico_id) REFERENCES usuario(id) ON DELETE SET NULL;
