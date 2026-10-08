"""
Pruebas de los 5 casos de la prueba técnica. Ejecutar: python manage.py test planta
"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from .models import Alerta, Maquina, Parada


class BasePlanta(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("crear_demo", stdout=StringIO())
        User = get_user_model()
        cls.operario1 = User.objects.get(username="operario1")
        cls.operario2 = User.objects.get(username="operario2")
        cls.supervisor = User.objects.get(username="supervisor")
        cls.jefe = User.objects.get(username="jefe")
        cls.maquina = Maquina.objects.first()

    def crear_alerta(self, usuario, descripcion="Ruido en el motor"):
        return Alerta.objects.create(maquina=self.maquina, descripcion=descripcion, usuario=usuario)

    def datos_parada(self, inicio="2026-10-07T23:50", fin="2026-10-08T00:20", motivo="Limpieza"):
        return {"maquina": self.maquina.pk, "inicio": inicio, "fin": fin, "motivo": motivo}


class Caso1ValidacionesTests(BasePlanta):
    def test_rechaza_descripcion_vacia_o_solo_espacios(self):
        self.client.force_login(self.operario1)
        for descripcion in ["", "    "]:
            r = self.client.post(reverse("planta:crear_alerta"),
                                 {"maquina": self.maquina.pk, "descripcion": descripcion})
            self.assertEqual(r.status_code, 400)
        self.assertEqual(Alerta.objects.count(), 0)

    def test_rechaza_motivo_de_parada_vacio(self):
        self.client.force_login(self.supervisor)
        r = self.client.post(reverse("planta:crear_parada"), self.datos_parada(motivo="   "))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Parada.objects.count(), 0)

    def test_rechaza_fin_igual_o_anterior_al_inicio(self):
        self.client.force_login(self.supervisor)
        for fin in ["2026-10-08T10:00", "2026-10-08T09:59"]:
            r = self.client.post(reverse("planta:crear_parada"),
                                 self.datos_parada(inicio="2026-10-08T10:00", fin=fin))
            self.assertEqual(r.status_code, 400)
            self.assertContains(r, "posterior al inicio", status_code=400)
        self.assertEqual(Parada.objects.count(), 0)

    def test_rechaza_motivo_de_cancelacion_vacio(self):
        parada = Parada.objects.create(maquina=self.maquina, inicio="2026-10-08T10:00-05:00",
                                       fin="2026-10-08T10:30-05:00", motivo="X", usuario=self.supervisor)
        self.client.force_login(self.jefe)
        self.client.post(reverse("planta:cancelar_parada", args=[parada.pk]), {"motivo": "  "})
        parada.refresh_from_db()
        self.assertFalse(parada.cancelada)


class Caso2DuracionTests(BasePlanta):
    def test_parada_que_cruza_medianoche_dura_30_minutos(self):
        self.client.force_login(self.supervisor)
        r = self.client.post(reverse("planta:crear_parada"), self.datos_parada())
        self.assertEqual(r.status_code, 302)
        parada = Parada.objects.get()
        self.assertEqual(parada.duracion_minutos, 30)
        pagina = self.client.get(reverse("planta:inicio"))
        self.assertContains(pagina, "<td>30</td>", html=True)


class Caso3PermisosTests(BasePlanta):
    def test_operario_y_jefe_no_pueden_editar_alerta_con_peticion_manual(self):
        alerta = self.crear_alerta(self.operario1, "Original")
        for usuario in [self.operario1, self.jefe]:
            self.client.force_login(usuario)
            r = self.client.post(reverse("planta:editar_alerta", args=[alerta.pk]),
                                 {"maquina": self.maquina.pk, "descripcion": "Modificada"})
            self.assertEqual(r.status_code, 403)
        alerta.refresh_from_db()
        self.assertEqual(alerta.descripcion, "Original")

    def test_supervisor_si_puede_editar_alerta(self):
        alerta = self.crear_alerta(self.operario1, "Original")
        self.client.force_login(self.supervisor)
        r = self.client.post(reverse("planta:editar_alerta", args=[alerta.pk]),
                             {"maquina": self.maquina.pk, "descripcion": "Corregida"})
        self.assertEqual(r.status_code, 302)
        alerta.refresh_from_db()
        self.assertEqual(alerta.descripcion, "Corregida")

    def test_restricciones_de_paradas_por_rol(self):
        parada = Parada.objects.create(maquina=self.maquina, inicio="2026-10-08T10:00-05:00",
                                       fin="2026-10-08T10:30-05:00", motivo="X", usuario=self.supervisor)
        # Operario y jefe no registran paradas.
        for usuario in [self.operario1, self.jefe]:
            self.client.force_login(usuario)
            r = self.client.post(reverse("planta:crear_parada"), self.datos_parada())
            self.assertEqual(r.status_code, 403)
        # Operario y supervisor no cancelan paradas.
        for usuario in [self.operario1, self.supervisor]:
            self.client.force_login(usuario)
            r = self.client.post(reverse("planta:cancelar_parada", args=[parada.pk]), {"motivo": "x"})
            self.assertEqual(r.status_code, 403)
        # Supervisor y jefe no crean alertas.
        for usuario in [self.supervisor, self.jefe]:
            self.client.force_login(usuario)
            r = self.client.post(reverse("planta:crear_alerta"),
                                 {"maquina": self.maquina.pk, "descripcion": "x"})
            self.assertEqual(r.status_code, 403)
        self.assertEqual(Parada.objects.count(), 1)
        self.assertEqual(Alerta.objects.count(), 0)
        parada.refresh_from_db()
        self.assertFalse(parada.cancelada)

    def test_requiere_usuario_autenticado(self):
        r = self.client.get(reverse("planta:inicio"))
        self.assertRedirects(r, reverse("login") + "?next=/")
        r = self.client.post(reverse("planta:crear_alerta"),
                             {"maquina": self.maquina.pk, "descripcion": "x"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Alerta.objects.count(), 0)

    def test_rechaza_post_sin_token_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.operario1)
        r = cliente.post(reverse("planta:crear_alerta"), {"maquina": self.maquina.pk, "descripcion": "x"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Alerta.objects.count(), 0)


class Caso4CancelacionTests(BasePlanta):
    def test_cancelar_dos_veces_conserva_la_primera_cancelacion(self):
        parada = Parada.objects.create(maquina=self.maquina, inicio="2026-10-08T10:00-05:00",
                                       fin="2026-10-08T10:30-05:00", motivo="X", usuario=self.supervisor)
        url = reverse("planta:cancelar_parada", args=[parada.pk])
        self.client.force_login(self.jefe)
        self.client.post(url, {"motivo": "Registro duplicado"})
        parada.refresh_from_db()
        primera = (parada.cancelada_por_id, parada.cancelada_en, parada.motivo_cancelacion)

        # Segundo intento, incluso por otro usuario con el mismo permiso.
        otro_jefe = get_user_model().objects.create_user("jefe2", password="x")
        otro_jefe.groups.set(self.jefe.groups.all())
        self.client.force_login(otro_jefe)
        r = self.client.post(url, {"motivo": "Otro motivo"}, follow=True)
        self.assertContains(r, "ya estaba cancelada")

        parada.refresh_from_db()
        self.assertEqual((parada.cancelada_por_id, parada.cancelada_en, parada.motivo_cancelacion), primera)
        self.assertEqual(primera[0], self.jefe.pk)
        self.assertEqual(Parada.objects.count(), 1)


class Caso5VolumenYVisibilidadTests(BasePlanta):
    def test_10_alertas_5_paradas_y_cada_operario_ve_solo_las_suyas(self):
        call_command("crear_demo", "--con-datos", stdout=StringIO())
        self.assertEqual(Alerta.objects.count(), 10)
        self.assertEqual(Parada.objects.count(), 5)

        esperado = {self.operario1: 6, self.operario2: 4, self.supervisor: 10, self.jefe: 10}
        for usuario, cantidad in esperado.items():
            self.client.force_login(usuario)
            r = self.client.get(reverse("planta:inicio"))
            self.assertEqual(r.status_code, 200)
            alertas = list(r.context["alertas"])
            self.assertEqual(len(alertas), cantidad)
            if usuario in (self.operario1, self.operario2):
                self.assertTrue(all(a.usuario_id == usuario.pk for a in alertas))
                self.assertNotIn("paradas", r.context)  # el operario no ve paradas

        self.client.force_login(self.jefe)
        r = self.client.get(reverse("planta:inicio"))
        self.assertEqual(len(r.context["paradas"]), 5)
        self.assertContains(r, "<td>30</td>", html=True)  # la parada de 23:50 a 00:20
