from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .politica import intentos_visibles


@never_cache
@login_required(login_url="ingresar-historial")
@require_GET
def historial_web(request):
    registros = intentos_visibles(request.user).select_related("persona", "punto__terreno")[:50]
    plantilla = "residencial/registros.html" if request.GET.get("tabla") == "1" else "residencial/historial.html"
    return render(request, plantilla, {"registros": registros, "actualizado": timezone.now()})
