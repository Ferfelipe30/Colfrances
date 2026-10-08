# Prueba técnica Django — Alertas y paradas de máquina

**Candidato:** Juan Felipe [COMPLETAR APELLIDOS]

## Control de tiempo (hora de Colombia, 8 de octubre de 2026)

| Evento | Hora |
|---|---|
| Creación del repositorio | [HH:MM] |
| Primer commit (proyecto base) | [HH:MM] — [enlace](https://github.com/[USUARIO]/prueba-django-colfrance/commit/[HASH]) |
| Commit final | [HH:MM] — el hash va en el correo de entrega* |

\*El hash del commit final no puede escribirse dentro de ese mismo commit; se envía en el correo.

## Ejecución

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows. En Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py crear_demo --con-datos
python manage.py runserver
```

Abrir http://127.0.0.1:8000. `crear_demo` crea los grupos con sus permisos, los usuarios y 3 máquinas;
con `--con-datos` agrega además 10 alertas y 5 paradas de ejemplo. Pruebas: `python manage.py test planta`.
Probado con Django 4.2, 5.2 y 6.1 (SQLite).

## Usuarios de demostración (contraseña de todos: `demo1234`)

| Usuario | Rol | Puede |
|---|---|---|
| operario1, operario2 | Operario | Crear alertas y ver solo las que él reportó |
| supervisor | Supervisor | Ver y editar todas las alertas; registrar paradas |
| jefe | Jefe | Ver alertas y paradas; cancelar paradas indicando motivo |

## Cómo se controlan los permisos

- Cada rol es un grupo de Django con permisos de modelo (`add_alerta`, `view_alerta`, `change_alerta`,
  `add_parada`, `view_parada`) y uno propio, `cancelar_parada`.
- Cada acción es una vista protegida con `@login_required` y `@permission_required(..., raise_exception=True)`.
  Una petición manual sin permiso recibe 403 y no cambia datos; la plantilla solo oculta botones.
- El operario solo ve sus alertas porque la consulta se filtra en el servidor (`usuario=request.user`).
  El usuario de una alerta o parada se toma de la sesión, nunca del formulario.
- CSRF: middleware de Django activo y `{% csrf_token %}` en todos los formularios (cerrar sesión también es POST).
- Validaciones en el modelo (`clean()` y validadores) usadas por los formularios; `save()` llama a `full_clean()`
  para no guardar datos inválidos tampoco desde el shell.
- Cancelar no borra la parada: guarda quién, cuándo y por qué con un UPDATE condicional
  (`WHERE cancelada_en IS NULL`), así un segundo intento no sobrescribe el primero.
- Duración: se restan fecha y hora completas (zona America/Bogota, guardadas en UTC); 23:50 → 00:20 da 30 minutos.

**Supuestos:** el supervisor ve el listado de paradas en solo lectura para confirmar lo que registra; el operario
no ve paradas. La fecha de la alerta es la del registro. La edición se hace en la misma página principal.

## Resultados de la comprobación

Comprobación manual en el navegador y 12 pruebas automáticas (`python manage.py test planta` → OK).

| Caso | Cómo se comprobó | Resultado |
|---|---|---|
| 1. Vacíos y fin ≤ inicio | Descripción y motivos solo con espacios; parada 10:00 → 10:00 y 10:00 → 09:59; cancelación sin motivo | Rechazado con mensaje; no se guardó nada |
| 2. Cruce de medianoche | Parada del 07/10 23:50 al 08/10 00:20 | Muestra 30 minutos |
| 3. Edición manual | Como operario1 y como jefe, POST con `fetch` a `/alertas/1/editar/` desde la consola del navegador | 403; la alerta no cambió |
| 4. Doble cancelación | Como jefe, cancelar la misma parada desde dos pestañas | Se conservan el primer usuario, fecha y motivo; aviso "ya estaba cancelada"; siguen 5 paradas |
| 5. Volumen | `crear_demo --con-datos` (10 alertas y 5 paradas) | La página carga; operario1 ve 6, operario2 ve 4, supervisor y jefe ven 10 |

**Fallas encontradas y solución**

- Al ejecutar `crear_demo` por segunda vez se reasignaba la contraseña de los usuarios demo y Django cerraba sus
  sesiones abiertas (la prueba del caso 5 devolvía 302 en lugar de 200). Solución: la contraseña solo se asigna
  cuando el usuario se crea.

## Pendientes

- Validar paradas superpuestas en la misma máquina.
- Historial de ediciones de alertas (quién cambió qué y cuándo).
- Paginación y filtros por fecha o máquina.
- Para producción: PostgreSQL, `DEBUG=False`, `SECRET_KEY` por variable de entorno y HTTPS.

## Integración a un monolito Django

1. Copiar la app `planta` al monolito y agregarla a `INSTALLED_APPS`; sus modelos usan `settings.AUTH_USER_MODEL`, así que reutilizan los usuarios existentes.
2. Ejecutar `migrate` y asignar los permisos `planta.*` a los grupos o roles que ya existen, sin crear usuarios nuevos.
3. Incluir `path("planta/", include("planta.urls"))` y usar el login y la sesión del monolito (`LOGIN_URL`).

## Resolución de problemas y manejo de la presión

**Caso 1.**
Primero confirmo el alcance (¿todas las máquinas?, ¿desde qué hora?, ¿qué error aparece?) y pido registrar las paradas en una planilla para cargarlas después.
Investigo sin tocar producción: logs, último cambio desplegado, espacio en disco y bloqueos de la base; reproduzco en local o QA y no reinicio ni borro nada sin una hipótesis.
Informo cada 15–20 minutos qué sé, qué no y cuándo doy la siguiente actualización.
Mantengo la calma con una lista de verificación, un paso a la vez; si en 30 minutos no tengo la causa o el impacto crece, escalo al líder técnico o a infraestructura.

**Caso 2.**
Ordeno por impacto: 1) la falla de paradas, que afecta a toda la línea; 2) el usuario sin acceso, si es quien registra en el turno; 3) el reporte.
Pregunto a cada uno: ¿a cuántas personas afecta?, ¿qué se detiene si espera?, ¿para qué hora se necesita realmente?
Explico el orden, el motivo y una hora estimada, y aviso si cambia.
Delego el restablecimiento de la contraseña al administrador o a la mesa de ayuda, y el reporte a un compañero o a una exportación existente.

**Caso 3.**
Asumo el error y aviso de inmediato a mi líder y a los usuarios afectados, con qué hacer mientras tanto.
No acepto cambiar producción sin revisión: si es seguro (sin migraciones irreversibles ni pérdida de datos), vuelvo a la última versión estable (`git revert` o despliegue de la versión anterior).
Después reproduzco el error en QA, lo corrijo con una prueba que lo cubra y pido revisión de código.
Antes del nuevo cambio verifico respaldo de la base, migraciones, pruebas en verde y los logs después de desplegar; documento la causa.

## Uso de inteligencia artificial

Usé Claude (Anthropic) como apoyo para [COMPLETAR: p. ej. generar la base del código, las pruebas automáticas y el
borrador de este README]. Revisé el código, ejecuté las pruebas y la comprobación manual de los 5 casos, y puedo
explicar cada parte.
