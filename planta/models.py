from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def validar_no_vacio(valor):
    """Rechaza textos vacíos o compuestos solo por espacios."""
    if not str(valor).strip():
        raise ValidationError("Este campo no puede estar vacío.")


class Maquina(models.Model):
    nombre = models.CharField("nombre", max_length=80, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "máquina"
        verbose_name_plural = "máquinas"

    def __str__(self):
        return self.nombre


class Alerta(models.Model):
    maquina = models.ForeignKey(
        Maquina, on_delete=models.PROTECT, related_name="alertas", verbose_name="máquina"
    )
    descripcion = models.TextField("descripción", validators=[validar_no_vacio])
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="alertas_reportadas",
        verbose_name="reportada por",
    )
    fecha = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "alerta"
        verbose_name_plural = "alertas"

    def __str__(self):
        return f"Alerta #{self.pk} - {self.maquina}"

    def save(self, *args, **kwargs):
        # Valida también cuando se guarda fuera de un formulario (shell, comandos).
        self.full_clean()
        super().save(*args, **kwargs)


class Parada(models.Model):
    maquina = models.ForeignKey(
        Maquina, on_delete=models.PROTECT, related_name="paradas", verbose_name="máquina"
    )
    inicio = models.DateTimeField("inicio")
    fin = models.DateTimeField("finalización")
    motivo = models.TextField("motivo", validators=[validar_no_vacio])
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="paradas_registradas",
        verbose_name="registrada por",
    )
    registrada_en = models.DateTimeField("registrada en", auto_now_add=True)

    # Cancelación: el registro nunca se borra, solo se marca.
    cancelada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="paradas_canceladas",
        verbose_name="cancelada por",
    )
    cancelada_en = models.DateTimeField("cancelada en", null=True, blank=True)
    motivo_cancelacion = models.TextField("motivo de cancelación", blank=True)

    class Meta:
        ordering = ["-inicio", "-id"]
        verbose_name = "parada"
        verbose_name_plural = "paradas"
        permissions = [("cancelar_parada", "Puede cancelar paradas")]

    def __str__(self):
        return f"Parada #{self.pk} - {self.maquina}"

    @property
    def cancelada(self):
        return self.cancelada_en is not None

    @property
    def duracion_minutos(self):
        # Se restan fechas completas (no solo horas): 23:50 -> 00:20 del día siguiente = 30.
        return int((self.fin - self.inicio).total_seconds() // 60)

    def clean(self):
        super().clean()
        if self.inicio and self.fin and self.fin <= self.inicio:
            raise ValidationError(
                {"fin": "La finalización debe ser posterior al inicio."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
