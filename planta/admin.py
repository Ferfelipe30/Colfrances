from django.contrib import admin

from .models import Alerta, Maquina, Parada


@admin.register(Maquina)
class MaquinaAdmin(admin.ModelAdmin):
    list_display = ["nombre"]


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ["id", "maquina", "descripcion", "usuario", "fecha"]
    list_filter = ["maquina", "usuario"]


@admin.register(Parada)
class ParadaAdmin(admin.ModelAdmin):
    list_display = ["id", "maquina", "inicio", "fin", "duracion_minutos", "usuario", "cancelada_en"]
    list_filter = ["maquina"]

    def has_delete_permission(self, request, obj=None):
        return False  # las paradas no se borran, se cancelan
