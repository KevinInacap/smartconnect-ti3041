from django.db.models import Q
from .models import Participacion, Persona, PuntoAcceso, Terreno, Vivienda


def identidad(user):
    return getattr(user, "persona", None)


def terrenos_visibles(persona):
    return Terreno.objects.filter(
        Q(administrador=persona) | Q(viviendas__participaciones__persona=persona) |
        Q(empleos__persona=persona)
    ).distinct()


def visibles(modelo, user):
    base = modelo.objects.order_by("pk")
    if user.is_staff:
        return base
    persona = identidad(user)
    if persona is None:
        return base.none()
    if modelo is Persona:
        return base.filter(pk=persona.pk)
    if modelo is Terreno:
        return terrenos_visibles(persona).order_by("pk")
    if modelo is Vivienda:
        return base.filter(Q(terreno__administrador=persona) | Q(participaciones__persona=persona)).distinct()
    if modelo is PuntoAcceso:
        return base.filter(terreno__in=terrenos_visibles(persona))
    raise ValueError("Maestro desconocido")


def administra_vivienda(persona, vivienda):
    return persona is not None and Participacion.objects.filter(
        persona=persona, vivienda=vivienda, rol=Participacion.Rol.ADMIN
    ).exists()
