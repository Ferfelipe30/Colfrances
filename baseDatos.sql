-- =============================================================================
-- Base de datos de prueba: alertas y paradas de máquina (SQLite)
--
-- Equivale a: python manage.py crear_demo --con-datos
-- Requisito: ejecutarlo DESPUÉS de "python manage.py migrate", que crea las tablas,
-- los content types y los permisos. Se puede ejecutar varias veces: no duplica datos.
--
-- Fechas: con USE_TZ = True Django guarda en UTC. Colombia es UTC-5 todo el año
-- (sin horario de verano), por eso: hora de Colombia + 5 horas = valor guardado.
-- Ojo: lo que se inserta por SQL no pasa por las validaciones de Django; estos datos
-- ya son válidos y la PARTE 3 permite comprobarlo.
-- =============================================================================


-- =============================================================================
-- PARTE 1. ESQUEMA (solo referencia, comentado)
-- Las tablas las crea "python manage.py migrate". Para ver este SQL listo para
-- ejecutar: python manage.py sqlmigrate planta 0001
-- =============================================================================
-- CREATE TABLE "planta_maquina" (
--     "id"     integer NOT NULL PRIMARY KEY AUTOINCREMENT,
--     "nombre" varchar(80) NOT NULL UNIQUE
-- );
-- CREATE TABLE "planta_alerta" (
--     "id"          integer NOT NULL PRIMARY KEY AUTOINCREMENT,
--     "descripcion" text NOT NULL,
--     "fecha"       datetime NOT NULL,
--     "maquina_id"  bigint NOT NULL REFERENCES "planta_maquina" ("id") DEFERRABLE INITIALLY DEFERRED,
--     "usuario_id"  integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
-- );
-- CREATE TABLE "planta_parada" (
--     "id"                 integer NOT NULL PRIMARY KEY AUTOINCREMENT,
--     "inicio"             datetime NOT NULL,
--     "fin"                datetime NOT NULL,
--     "motivo"             text NOT NULL,
--     "registrada_en"      datetime NOT NULL,
--     "cancelada_en"       datetime NULL,
--     "motivo_cancelacion" text NOT NULL,
--     "cancelada_por_id"   integer NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
--     "maquina_id"         bigint NOT NULL REFERENCES "planta_maquina" ("id") DEFERRABLE INITIALLY DEFERRED,
--     "usuario_id"         integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
-- );
-- CREATE INDEX "planta_alerta_maquina_id_600fc9ad"       ON "planta_alerta" ("maquina_id");
-- CREATE INDEX "planta_alerta_usuario_id_ed90680e"       ON "planta_alerta" ("usuario_id");
-- CREATE INDEX "planta_parada_cancelada_por_id_58b6036c" ON "planta_parada" ("cancelada_por_id");
-- CREATE INDEX "planta_parada_maquina_id_881ccbce"       ON "planta_parada" ("maquina_id");
-- CREATE INDEX "planta_parada_usuario_id_ddb08b32"       ON "planta_parada" ("usuario_id");


-- =============================================================================
-- PARTE 2. DATOS DE PRUEBA
-- =============================================================================

-- 2.1 Roles (grupos de Django) y sus permisos
INSERT OR IGNORE INTO auth_group (name) VALUES ('Operario'), ('Supervisor'), ('Jefe');

WITH permisos_por_rol (rol, codename) AS (VALUES
    ('Operario',   'add_alerta'),
    ('Supervisor', 'view_alerta'),
    ('Supervisor', 'change_alerta'),
    ('Supervisor', 'add_parada'),
    ('Supervisor', 'view_parada'),
    ('Jefe',       'view_alerta'),
    ('Jefe',       'view_parada'),
    ('Jefe',       'cancelar_parada')
)
INSERT OR IGNORE INTO auth_group_permissions (group_id, permission_id)
SELECT g.id, p.id
FROM permisos_por_rol r
JOIN auth_group g          ON g.name = r.rol
JOIN auth_permission p     ON p.codename = r.codename
JOIN django_content_type c ON c.id = p.content_type_id AND c.app_label = 'planta';

-- 2.2 Usuarios de demostración. Contraseña de todos: demo1234
-- Django nunca guarda la contraseña en claro: este texto es el hash PBKDF2 de "demo1234".
INSERT OR IGNORE INTO auth_user
    (username, password, first_name, last_name, email,
     is_superuser, is_staff, is_active, date_joined, last_login)
VALUES
    ('operario1',  'pbkdf2_sha256$1500000$2YmPVSi7siDF0YXtAeMKHj$clzvKv4FLYsn0ZOChEykO4Fci1aYgkc61nEcWkJO0l0=', '', '', '', 0, 0, 1, datetime('now'), NULL),
    ('operario2',  'pbkdf2_sha256$1500000$2YmPVSi7siDF0YXtAeMKHj$clzvKv4FLYsn0ZOChEykO4Fci1aYgkc61nEcWkJO0l0=', '', '', '', 0, 0, 1, datetime('now'), NULL),
    ('supervisor', 'pbkdf2_sha256$1500000$2YmPVSi7siDF0YXtAeMKHj$clzvKv4FLYsn0ZOChEykO4Fci1aYgkc61nEcWkJO0l0=', '', '', '', 0, 0, 1, datetime('now'), NULL),
    ('jefe',       'pbkdf2_sha256$1500000$2YmPVSi7siDF0YXtAeMKHj$clzvKv4FLYsn0ZOChEykO4Fci1aYgkc61nEcWkJO0l0=', '', '', '', 0, 0, 1, datetime('now'), NULL);

WITH usuario_rol (username, rol) AS (VALUES
    ('operario1',  'Operario'),
    ('operario2',  'Operario'),
    ('supervisor', 'Supervisor'),
    ('jefe',       'Jefe')
)
INSERT OR IGNORE INTO auth_user_groups (user_id, group_id)
SELECT u.id, g.id
FROM usuario_rol ur
JOIN auth_user u  ON u.username = ur.username
JOIN auth_group g ON g.name = ur.rol;

-- 2.3 Máquinas
INSERT OR IGNORE INTO planta_maquina (nombre)
VALUES ('Empacadora 1'), ('Horno 2'), ('Mezcladora 3');

-- 2.4 Diez alertas: 6 de operario1 y 4 de operario2 (solo si la tabla está vacía)
WITH datos (orden, maquina, usuario, descripcion) AS (VALUES
    (1,  'Empacadora 1', 'operario1', 'Ruido anormal en el motor principal'),
    (2,  'Horno 2',      'operario1', 'Temperatura por encima del rango'),
    (3,  'Mezcladora 3', 'operario1', 'Sensor de presencia no detecta producto'),
    (4,  'Empacadora 1', 'operario1', 'Atasco de material en la banda'),
    (5,  'Horno 2',      'operario1', 'Vibración excesiva'),
    (6,  'Mezcladora 3', 'operario1', 'Fuga de aceite en el reductor'),
    (7,  'Empacadora 1', 'operario2', 'Baja presión de aire'),
    (8,  'Horno 2',      'operario2', 'Cuchillas desalineadas'),
    (9,  'Mezcladora 3', 'operario2', 'Botón de paro de emergencia activado'),
    (10, 'Empacadora 1', 'operario2', 'Error de comunicación con el PLC')
)
INSERT INTO planta_alerta (maquina_id, descripcion, usuario_id, fecha)
SELECT m.id, d.descripcion, u.id, datetime('now')
FROM datos d
JOIN planta_maquina m ON m.nombre = d.maquina
JOIN auth_user u      ON u.username = d.usuario
WHERE NOT EXISTS (SELECT 1 FROM planta_alerta)
ORDER BY d.orden;

-- 2.5 Cinco paradas registradas por el supervisor (solo si la tabla está vacía).
-- La primera cruza la medianoche: 23:50 -> 00:20 = 30 minutos.
WITH datos (orden, maquina, inicio_colombia, fin_colombia, motivo) AS (VALUES
    (1, 'Empacadora 1', '2026-10-07 23:50', '2026-10-08 00:20', 'Cambio de turno con limpieza (cruza medianoche)'),
    (2, 'Horno 2',      '2026-10-08 06:00', '2026-10-08 06:45', 'Mantenimiento preventivo'),
    (3, 'Mezcladora 3', '2026-10-08 08:15', '2026-10-08 09:00', 'Falta de materia prima'),
    (4, 'Empacadora 1', '2026-10-08 10:00', '2026-10-08 10:12', 'Atasco en la banda'),
    (5, 'Horno 2',      '2026-10-08 13:30', '2026-10-08 15:00', 'Falla eléctrica')
)
INSERT INTO planta_parada
    (maquina_id, inicio, fin, motivo, usuario_id, registrada_en,
     cancelada_por_id, cancelada_en, motivo_cancelacion)
SELECT m.id,
       datetime(d.inicio_colombia, '+5 hours'),  -- hora de Colombia -> UTC
       datetime(d.fin_colombia, '+5 hours'),
       d.motivo, u.id, datetime('now'),
       NULL, NULL, ''                            -- sin cancelar
FROM datos d
JOIN planta_maquina m ON m.nombre = d.maquina
JOIN auth_user u      ON u.username = 'supervisor'
WHERE NOT EXISTS (SELECT 1 FROM planta_parada)
ORDER BY d.orden;


-- =============================================================================
-- PARTE 3. CONSULTAS DE VERIFICACIÓN (solo lectura; ejecutar cada una por separado)
-- =============================================================================

-- Caso 1. No hay datos inválidos guardados. Esperado: 0 en las cuatro columnas.
SELECT
    (SELECT COUNT(*) FROM planta_alerta WHERE TRIM(descripcion) = '')                 AS alertas_sin_descripcion,
    (SELECT COUNT(*) FROM planta_parada WHERE TRIM(motivo) = '')                      AS paradas_sin_motivo,
    (SELECT COUNT(*) FROM planta_parada WHERE julianday(fin) <= julianday(inicio))    AS paradas_fin_no_posterior,
    (SELECT COUNT(*) FROM planta_parada
      WHERE cancelada_en IS NOT NULL AND TRIM(motivo_cancelacion) = '')               AS cancelaciones_sin_motivo;

-- Caso 2. Duración en minutos, con fechas en hora de Colombia.
-- Esperado: la parada de 23:50 a 00:20 da 30.
SELECT p.id,
       m.nombre                                               AS maquina,
       datetime(p.inicio, '-5 hours')                         AS inicio_colombia,
       datetime(p.fin, '-5 hours')                            AS fin_colombia,
       (strftime('%s', p.fin) - strftime('%s', p.inicio)) / 60 AS duracion_min
FROM planta_parada p
JOIN planta_maquina m ON m.id = p.maquina_id
ORDER BY p.inicio;

-- Caso 3a. Permisos por rol. Esperado: change_alerta solo en Supervisor.
SELECT g.name AS rol, p.codename AS permiso
FROM auth_group g
JOIN auth_group_permissions gp ON gp.group_id = g.id
JOIN auth_permission p         ON p.id = gp.permission_id
ORDER BY g.name, p.codename;

-- Caso 3b. Después del intento manual como operario o jefe, la alerta 1 no cambió.
SELECT id, descripcion FROM planta_alerta WHERE id = 1;

-- Caso 4. Después de cancelar dos veces la parada 2: se conserva la primera
-- cancelación (usuario, fecha y motivo) y siguen existiendo 5 paradas.
SELECT p.id,
       u.username                            AS cancelada_por,
       datetime(p.cancelada_en, '-5 hours')  AS cancelada_en_colombia,
       p.motivo_cancelacion,
       (SELECT COUNT(*) FROM planta_parada)  AS total_paradas
FROM planta_parada p
LEFT JOIN auth_user u ON u.id = p.cancelada_por_id
WHERE p.id = 2;

-- Caso 5. Volumen y alertas por usuario. Esperado: 10 alertas, 5 paradas;
-- operario1 = 6 y operario2 = 4.
SELECT (SELECT COUNT(*) FROM planta_alerta) AS total_alertas,
       (SELECT COUNT(*) FROM planta_parada) AS total_paradas;

SELECT u.username, COUNT(*) AS alertas
FROM planta_alerta a
JOIN auth_user u ON u.id = a.usuario_id
GROUP BY u.username
ORDER BY u.username;