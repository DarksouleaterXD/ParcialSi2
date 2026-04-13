-- CU06 Gestionar taller: campos de contacto y horario (ejecutar en PostgreSQL sobre esquema existente).
ALTER TABLE taller ADD COLUMN IF NOT EXISTS email VARCHAR(150);
ALTER TABLE taller ADD COLUMN IF NOT EXISTS horario_atencion VARCHAR(120);
