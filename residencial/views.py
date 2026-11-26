from django.db import transaction
from django.db.models import Q, ProtectedError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Credencial, Intento, Participacion, PermisoPunto, Persona, PuntoAcceso, Terreno, Vivienda
from .politica import administra_vivienda, identidad, terrenos_visibles, visibles
from .serializers import (
    AsignacionSerializer, FiltrosHistorialSerializer, IntentoSerializer, ParticipacionSerializer,
    PersonaSerializer, PuntoSerializer, SolicitudSerializer, TerrenoSerializer, ViviendaSerializer,
)


class Conflicto(APIException):
    status_code = status.HTTP_409_CONFLICT


class MaestroViewSet(viewsets.ModelViewSet):
    lookup_value_regex = r"[0-9]+"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        return visibles(self.queryset.model, self.request.user)

    def comprobar_escritura(self, terreno=None):
        user = self.request.user
        if user.is_staff:
            return
        persona = identidad(user)
        if terreno and persona and terreno.administrador_id == persona.pk:
            return
        raise PermissionDenied("La cuenta carece de autoridad para modificar este recurso.")

    def get_object(self):
        if self.action in {"update", "partial_update", "destroy"}:
            objeto = get_object_or_404(self.queryset, pk=self.kwargs["pk"])
            self.comprobar_escritura(getattr(objeto, "terreno", None))
            return objeto
        return super().get_object()

    def perform_create(self, serializer):
        self.comprobar_escritura(serializer.validated_data.get("terreno"))
        serializer.save()

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise Conflicto("El recurso tiene relaciones vigentes o historial asociado.") from None

    @transaction.atomic
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class PersonaViewSet(MaestroViewSet):
    queryset = Persona.objects.all()
    serializer_class = PersonaSerializer


class TerrenoViewSet(MaestroViewSet):
    queryset = Terreno.objects.all()
    serializer_class = TerrenoSerializer


class PuntoViewSet(MaestroViewSet):
    queryset = PuntoAcceso.objects.all()
    serializer_class = PuntoSerializer


class ViviendaViewSet(MaestroViewSet):
    queryset = Vivienda.objects.all()
    serializer_class = ViviendaSerializer

    @extend_schema(request=AsignacionSerializer, responses={201: ParticipacionSerializer})
    @action(detail=True, methods=["post"], url_path="asignaciones")
    def asignaciones(self, request, pk=None):
        vivienda = get_object_or_404(Vivienda, pk=pk)
        if not administra_vivienda(identidad(request.user), vivienda):
            raise PermissionDenied("Se requiere ser propietario administrador de esta vivienda.")
        entrada = AsignacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        vinculo, creado = Participacion.objects.get_or_create(
            persona=entrada.validated_data["persona"], vivienda=vivienda,
            defaults={"rol": entrada.validated_data["rol"]},
        )
        if not creado:
            raise Conflicto("La persona ya está vinculada a esta vivienda.")
        return Response(ParticipacionSerializer(vinculo).data, status=201)

    @extend_schema(responses=ParticipacionSerializer(many=True))
    @asignaciones.mapping.get
    def listar_asignaciones(self, request, pk=None):
        vivienda = self.get_object()
        persona = identidad(request.user)
        registros = vivienda.participaciones.order_by("pk")
        if not (request.user.is_staff or vivienda.terreno.administrador == persona
                or administra_vivienda(persona, vivienda)):
            registros = registros.filter(persona=persona)
        return Response(ParticipacionSerializer(registros, many=True).data)


class SolicitarAcceso(APIView):
    @extend_schema(request=SolicitudSerializer, responses={201: IntentoSerializer})
    @transaction.atomic
    def post(self, request):
        entrada = SolicitudSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        punto = datos["punto"]
        medio = datos["medio"]
        persona = identidad(request.user)
        huella = ""
        motivo = ""
        if medio == "rfid":
            if not request.user.is_staff:
                raise PermissionDenied("El lector RFID simulado requiere una cuenta de operación.")
            huella = Credencial.identificar(datos["uid"])
            credencial = Credencial.objects.filter(huella=huella).select_related("persona").first()
            persona = credencial.persona if credencial else None
            if not credencial:
                motivo = "credencial_desconocida"
            elif not credencial.activa:
                motivo = "credencial_inactiva"
        elif persona is None:
            motivo = "sin_persona"
        elif not datos["cerca"]:
            motivo = "fuera_de_proximidad"

        if not motivo:
            if not terrenos_visibles(persona).filter(pk=punto.terreno_id).exists():
                motivo = "sin_vinculo_territorial"
            elif not PermisoPunto.objects.filter(persona=persona, punto=punto).exists():
                motivo = "sin_permiso_punto"
        intento = Intento.objects.create(persona=persona, punto=punto, medio=medio, huella=huella,
                                         permitido=not motivo, motivo=motivo or "autorizado")
        return Response(IntentoSerializer(intento).data, status=201)


class Historial(APIView):
    @extend_schema(parameters=[FiltrosHistorialSerializer], responses=IntentoSerializer(many=True))
    def get(self, request):
        filtros = FiltrosHistorialSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        registros = Intento.objects.select_related("punto").order_by("-fecha", "-pk")
        if not request.user.is_staff:
            persona = identidad(request.user)
            if persona is None:
                registros = registros.none()
            else:
                registros = registros.filter(Q(persona=persona) | Q(punto__terreno__administrador=persona))
        campos = {"persona": "persona_id", "terreno": "punto__terreno_id", "punto": "punto_id", "fecha": "fecha__date"}
        for campo, valor in filtros.validated_data.items():
            registros = registros.filter(**{campos[campo]: valor})
        return Response(IntentoSerializer(registros, many=True).data)
