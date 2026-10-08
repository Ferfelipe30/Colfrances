"""
Una sola página principal. Cada acción es una vista POST que valida el permiso
en el backend: ocultar un botón no basta, una petición manual también se rechaza (403).

Permisos (asignados a grupos con `python manage.py crear_demo`):
  Operario   -> add_alerta
  Supervisor -> view_alerta, change_alerta, add_parada, view_parada
  Jefe       -> view_alerta, view_parada, cancelar_parada
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .forms import AlertaForm, CancelarParadaForm, ParadaForm
from .models import Alerta, Parada


def alertas_visibles(usuario):
    """Supervisor y jefe ven todas las alertas; el operario solo las que reportó."""
    if usuario.has_perm("planta.view_alerta"):
        return Alerta.objects.all()
    if usuario.has_perm("planta.add_alerta"):
        return Alerta.objects.filter(usuario=usuario)
    return Alerta.objects.none()


def pagina_principal(request, status=200, **formularios):
    """Arma la página única. Recibe formularios con errores para mostrarlos."""
    usuario = request.user
    contexto = {
        "rol": ", ".join(usuario.groups.values_list("name", flat=True))
        or ("Administrador" if usuario.is_superuser else "Sin rol"),
        "alertas": alertas_visibles(usuario).select_related("maquina", "usuario"),
        "form_editar": formularios.get("form_editar"),
        "alerta_en_edicion": formularios.get("alerta_en_edicion"),
    }
    if usuario.has_perm("planta.add_alerta"):
        contexto["form_alerta"] = formularios.get("form_alerta") or AlertaForm()
    if usuario.has_perm("planta.add_parada"):
        contexto["form_parada"] = formularios.get("form_parada") or ParadaForm()
    if usuario.has_perm("planta.view_parada"):
        contexto["paradas"] = Parada.objects.select_related(
            "maquina", "usuario", "cancelada_por"
        )
    return render(request, "planta/inicio.html", contexto, status=status)


@login_required
def inicio(request):
    return pagina_principal(request)


@login_required
@permission_required("planta.add_alerta", raise_exception=True)
@require_POST
def crear_alerta(request):
    form = AlertaForm(request.POST)
    if form.is_valid():
        alerta = form.save(commit=False)
        alerta.usuario = request.user  # el usuario sale de la sesión, no del formulario
        alerta.save()
        messages.success(request, f"Alerta #{alerta.pk} registrada.")
        return redirect("planta:inicio")
    return pagina_principal(request, status=400, form_alerta=form)


@login_required
@permission_required("planta.change_alerta", raise_exception=True)
@require_http_methods(["GET", "POST"])
def editar_alerta(request, pk):
    alerta = get_object_or_404(Alerta, pk=pk)
    if request.method == "POST":
        form = AlertaForm(request.POST, instance=alerta)
        if form.is_valid():
            form.save()
            messages.success(request, f"Alerta #{alerta.pk} actualizada.")
            return redirect("planta:inicio")
        return pagina_principal(
            request, status=400, form_editar=form, alerta_en_edicion=alerta
        )
    form = AlertaForm(instance=alerta)
    return pagina_principal(request, form_editar=form, alerta_en_edicion=alerta)


@login_required
@permission_required("planta.add_parada", raise_exception=True)
@require_POST
def crear_parada(request):
    form = ParadaForm(request.POST)
    if form.is_valid():
        parada = form.save(commit=False)
        parada.usuario = request.user
        parada.save()
        messages.success(
            request,
            f"Parada #{parada.pk} registrada ({parada.duracion_minutos} minutos).",
        )
        return redirect("planta:inicio")
    return pagina_principal(request, status=400, form_parada=form)


@login_required
@permission_required("planta.cancelar_parada", raise_exception=True)
@require_POST
def cancelar_parada(request, pk):
    parada = get_object_or_404(Parada, pk=pk)
    if parada.cancelada:
        messages.warning(
            request,
            f"La parada #{parada.pk} ya estaba cancelada; se conserva la cancelación original.",
        )
        return redirect("planta:inicio")

    form = CancelarParadaForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Indique el motivo de la cancelación.")
        return redirect("planta:inicio")

    # UPDATE condicional: solo cambia la fila si todavía no está cancelada.
    # Si llegan dos cancelaciones al mismo tiempo, la segunda no actualiza nada.
    actualizadas = Parada.objects.filter(pk=parada.pk, cancelada_en__isnull=True).update(
        cancelada_por=request.user,
        cancelada_en=timezone.now(),
        motivo_cancelacion=form.cleaned_data["motivo"],
    )
    if actualizadas:
        messages.success(request, f"Parada #{parada.pk} cancelada.")
    else:
        messages.warning(
            request,
            f"La parada #{parada.pk} ya estaba cancelada; se conserva la cancelación original.",
        )
    return redirect("planta:inicio")
