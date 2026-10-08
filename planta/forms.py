from django import forms

from .models import Alerta, Parada

FORMATO_FECHA_HORA = "%Y-%m-%dT%H:%M"  # formato que usa <input type="datetime-local">


class AlertaForm(forms.ModelForm):
    """Se usa para crear (operario) y para editar (supervisor)."""

    class Meta:
        model = Alerta
        fields = ["maquina", "descripcion"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 2, "cols": 50})}


class ParadaForm(forms.ModelForm):
    class Meta:
        model = Parada
        fields = ["maquina", "inicio", "fin", "motivo"]
        widgets = {
            "inicio": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format=FORMATO_FECHA_HORA
            ),
            "fin": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format=FORMATO_FECHA_HORA
            ),
            "motivo": forms.Textarea(attrs={"rows": 2, "cols": 50}),
        }


class CancelarParadaForm(forms.Form):
    # CharField quita los espacios por defecto: "   " cuenta como vacío.
    motivo = forms.CharField(label="Motivo de cancelación", max_length=500)
