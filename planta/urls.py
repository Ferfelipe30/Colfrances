from django.urls import path

from . import views

app_name = "planta"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("alertas/crear/", views.crear_alerta, name="crear_alerta"),
    path("alertas/<int:pk>/editar/", views.editar_alerta, name="editar_alerta"),
    path("paradas/crear/", views.crear_parada, name="crear_parada"),
    path("paradas/<int:pk>/cancelar/", views.cancelar_parada, name="cancelar_parada"),
]
