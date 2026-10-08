from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from planta.models import Alerta, Maquina, Parada

CONTRASENA_DEMO = "demo1234"

PERMISOS_POR_ROL = {
    "Operario": ["add_alerta"],
    "Supervisor": ["view_alerta", "change_alerta", "add_parada", "view_parada"],
    "Jefe": ["view_alerta", "view_parada", "cancelar_parada"],
}

USUARIOS_DEMO = [
    ("operario1", "Operario"),
    ("operario2", "Operario"),
    ("supervisor", "Supervisor"),
    ("jefe", "Jefe"),
]

MAQUINAS = ["Empacadora 1", "Horno 2", "Mezcladora 3"]


class Command(BaseCommand):
    help = (
        "Crea los grupos con sus permisos, los usuarios de demostración y las máquinas. "
        "Con --con-datos agrega 10 alertas y 5 paradas de ejemplo (caso 5)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--con-datos",
            action="store_true",
            help="Crea 10 alertas (6 de operario1 y 4 de operario2) y 5 paradas.",
        )

    @transaction.atomic
    def handle(self, *args, **opciones):
        grupos = {}
        for rol, codenames in PERMISOS_POR_ROL.items():
            permisos = list(
                Permission.objects.filter(
                    content_type__app_label="planta", codename__in=codenames
                )
            )
            if len(permisos) != len(codenames):
                raise CommandError("Faltan permisos. Ejecute primero: python manage.py migrate")
            grupo, _ = Group.objects.get_or_create(name=rol)
            grupo.permissions.set(permisos)
            grupos[rol] = grupo

        User = get_user_model()
        usuarios = {}
        for nombre, rol in USUARIOS_DEMO:
            usuario, creado = User.objects.get_or_create(username=nombre)
            if creado:
                # Solo al crearlo: cambiar la contraseña cerraría las sesiones abiertas.
                usuario.set_password(CONTRASENA_DEMO)
                usuario.save()
            usuario.groups.set([grupos[rol]])
            usuarios[nombre] = usuario

        maquinas = [Maquina.objects.get_or_create(nombre=n)[0] for n in MAQUINAS]
        self.stdout.write(self.style.SUCCESS(
            f"Grupos, usuarios ({', '.join(usuarios)}; contraseña {CONTRASENA_DEMO}) "
            f"y {len(maquinas)} máquinas listos."
        ))

        if opciones["con_datos"]:
            self._crear_datos(usuarios, maquinas)

    def _crear_datos(self, usuarios, maquinas):
        descripciones = [
            "Ruido anormal en el motor principal",
            "Temperatura por encima del rango",
            "Sensor de presencia no detecta producto",
            "Atasco de material en la banda",
            "Vibración excesiva",
            "Fuga de aceite en el reductor",
            "Baja presión de aire",
            "Cuchillas desalineadas",
            "Botón de paro de emergencia activado",
            "Error de comunicación con el PLC",
        ]
        for i, descripcion in enumerate(descripciones):
            operario = usuarios["operario1"] if i < 6 else usuarios["operario2"]
            Alerta.objects.create(
                maquina=maquinas[i % len(maquinas)], descripcion=descripcion, usuario=operario
            )

        hoy = timezone.localdate()
        ayer = hoy - timedelta(days=1)

        def fecha_hora(dia, hora, minuto):
            return timezone.make_aware(datetime.combine(dia, time(hora, minuto)))

        paradas = [
            # (máquina, inicio, fin, motivo)
            (0, fecha_hora(ayer, 23, 50), fecha_hora(hoy, 0, 20), "Cambio de turno con limpieza (cruza medianoche)"),
            (1, fecha_hora(hoy, 6, 0), fecha_hora(hoy, 6, 45), "Mantenimiento preventivo"),
            (2, fecha_hora(hoy, 8, 15), fecha_hora(hoy, 9, 0), "Falta de materia prima"),
            (0, fecha_hora(hoy, 10, 0), fecha_hora(hoy, 10, 12), "Atasco en la banda"),
            (1, fecha_hora(hoy, 13, 30), fecha_hora(hoy, 15, 0), "Falla eléctrica"),
        ]
        for indice, inicio, fin, motivo in paradas:
            Parada.objects.create(
                maquina=maquinas[indice], inicio=inicio, fin=fin, motivo=motivo,
                usuario=usuarios["supervisor"],
            )
        self.stdout.write(self.style.SUCCESS("Se crearon 10 alertas y 5 paradas de ejemplo."))
