-- Ejecutar una sola vez en bases ya creadas sin la columna permisos_json (CU3 permisos en JSON).
ALTER TABLE rol ADD COLUMN IF NOT EXISTS permisos_json TEXT;
