-- =========================================================================
-- SEMILLAS: roles base + usuario administrador inicial
-- Ejecutar DESPUÉS de Taller_Inteligente.sql sobre la misma base de datos.
--
-- Admin por defecto:
--   Email:    admin@emergencias.local
--   Password: Admin123!
-- Cambiar en producción.
--
-- Re-ejecutar este script es seguro:
--   - Si el admin no es id_admin de ningún taller, se elimina y se vuelve a insertar.
--   - Si hay talleres que lo referencian, no se borra pero se actualiza hash/estado/nombre
--     (corrige usuarios viejos creados antes de cambios en roles o con contraseña incorrecta).
-- =========================================================================

INSERT INTO rol (nombre, descripcion) VALUES
    ('Administrador', 'Gestión de usuarios y configuración del sistema'),
    ('Cliente', 'Usuario de la app móvil'),
    ('Tecnico', 'Técnico / mecánico de taller')
ON CONFLICT (nombre) DO NOTHING;

-- Bases creadas antes de CU3: añadir columna (Taller_Inteligente.sql nuevo ya la incluye en CREATE rol)
ALTER TABLE rol ADD COLUMN IF NOT EXISTS permisos_json TEXT;

-- Permisos del rol Administrador alineados con backend (app/.../permisos.py)
UPDATE rol
SET permisos_json = $$["incidentes.acceder","pagos.acceder","roles.gestionar","sistema.acceder","taller.acceder","usuarios.editar","usuarios.ver"]$$
WHERE nombre = 'Administrador';

-- Quitar admin semilla previo solo si nada crítico lo referencia (p. ej. taller.id_admin)
DO $$
DECLARE
  uid INTEGER;
  taller_ref BOOLEAN;
BEGIN
  SELECT id INTO uid FROM usuario WHERE lower(trim(email)) = 'admin@emergencias.local';
  IF uid IS NULL THEN
    RETURN;
  END IF;

  taller_ref := FALSE;
  IF to_regclass('public.taller') IS NOT NULL THEN
    SELECT EXISTS (SELECT 1 FROM taller WHERE id_admin = uid) INTO taller_ref;
  END IF;

  IF taller_ref THEN
    RETURN;
  END IF;

  DELETE FROM usuario WHERE id = uid;
END $$;

-- Hash bcrypt de la contraseña Admin123! (bcrypt)
INSERT INTO usuario (nombre, apellido, email, passwordhash, telefono, estado)
VALUES (
    'Admin',
    'Sistema',
    'admin@emergencias.local',
    '$2b$12$r9hFw0lLIcMq/RLBZ4OcueQeW/WoW/wHiA48xfOsPwNo84jI9a.Di',
    NULL,
    'Activo'
)
ON CONFLICT (email) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    apellido = EXCLUDED.apellido,
    passwordhash = EXCLUDED.passwordhash,
    telefono = EXCLUDED.telefono,
    estado = EXCLUDED.estado;

INSERT INTO usuario_rol (id_usuario, id_rol)
SELECT u.id, r.id
FROM usuario u
CROSS JOIN rol r
WHERE lower(trim(u.email)) = 'admin@emergencias.local'
  AND r.nombre = 'Administrador'
ON CONFLICT (id_usuario, id_rol) DO NOTHING;

-- Especialidades de ejemplo (solo si existe la tabla; bases viejas sin migración la omiten)
DO $$
BEGIN
  IF to_regclass('public.especialidad') IS NOT NULL THEN
    INSERT INTO especialidad (nombre, descripcion) VALUES
      ('Batería', 'Arranque y baterías'),
      ('Neumáticos', 'Pinchazos y ruedas'),
      ('Chapa y pintura', 'Daños por colisión')
    ON CONFLICT (nombre) DO NOTHING;
  END IF;
END $$;
