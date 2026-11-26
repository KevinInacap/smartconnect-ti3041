from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Credencial, Intento, Participacion, PermisoPunto, Persona, PuntoAcceso, Terreno, Vivienda
from .politica import administra_vivienda, identidad, intentos_visibles, terrenos_visibles, visibles
from .serializers import (
    AsignacionSerializer, FiltrosHistorialSerializer, InicioSesionSerializer, IntentoSerializer,
    ParticipacionSerializer, PersonaSerializer, PuntoSerializer, RegistroUsuarioSerializer,
    SolicitudSerializer, TerrenoSerializer, TokensInicioSesionSerializer, ViviendaSerializer,
)


class Conflicto(APIException):
    status_code = status.HTTP_409_CONFLICT


SIN_SESION = OpenApiResponse(OpenApiTypes.OBJECT, "El token de acceso falta, expiró o es inválido.")
VIVIENDA_NO_ENCONTRADA = OpenApiResponse(OpenApiTypes.OBJECT, "La vivienda no está disponible para esta consulta.")


@extend_schema_view(post=extend_schema(
    request=InicioSesionSerializer,
    responses={
        200: OpenApiResponse(TokensInicioSesionSerializer, "Credenciales verificadas."),
        400: OpenApiResponse(OpenApiTypes.OBJECT, "Falta el nombre de usuario o la contraseña."),
        401: OpenApiResponse(OpenApiTypes.OBJECT, "Credenciales inválidas o cuenta inactiva."),
    },
))
class InicioSesion(TokenObtainPairView):
    serializer_class = InicioSesionSerializer


class RegistrarUsuario(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        description="Crea una cuenta estándar para iniciar sesión. La vinculación con una persona "
                    "y los permisos residenciales se gestionan por separado.",
        request=RegistroUsuarioSerializer,
        responses={
            201: OpenApiResponse(RegistroUsuarioSerializer, "Cuenta creada."),
            400: OpenApiResponse(OpenApiTypes.OBJECT, "Nombre de usuario duplicado o datos inválidos."),
        },
    )
    @transaction.atomic
    def post(self, request):
        registro = RegistroUsuarioSerializer(data=request.data)
        registro.is_valid(raise_exception=True)
        registro.save()
        return Response(registro.data, status=status.HTTP_201_CREATED)


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

    @extend_schema(
        description="Requiere el rol propietario_administrador en esta vivienda, incluso si la cuenta es operadora.",
        request=AsignacionSerializer,
        responses={
            201: OpenApiResponse(ParticipacionSerializer, "Participación creada."),
            400: OpenApiResponse(OpenApiTypes.OBJECT, "Persona o rol de destino inválido."),
            401: SIN_SESION,
            403: OpenApiResponse(OpenApiTypes.OBJECT, "La cuenta carece del rol requerido en esta vivienda."),
            404: VIVIENDA_NO_ENCONTRADA,
            409: OpenApiResponse(OpenApiTypes.OBJECT, "La persona ya está vinculada a la vivienda."),
        },
    )
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

    @extend_schema(
        description="El operador y los administradores correspondientes ven todos los vínculos. "
                    "Los demás residentes ven su propio vínculo.",
        responses={200: ParticipacionSerializer(many=True), 401: SIN_SESION, 404: VIVIENDA_NO_ENCONTRADA},
    )
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
    @extend_schema(
        description="Para app, envía `cerca`. Para RFID, envía `uid` desde una cuenta operadora. "
                    "La respuesta indica la decisión en `permitido` y `motivo`.",
        request=SolicitudSerializer,
        responses={
            201: OpenApiResponse(IntentoSerializer, "Intento guardado. La decisión puede ser autorizada o denegada."),
            400: OpenApiResponse(OpenApiTypes.OBJECT, "Punto, medio o datos del medio inválidos."),
            401: SIN_SESION,
            403: OpenApiResponse(OpenApiTypes.OBJECT, "El lector RFID requiere una cuenta operadora."),
        },
    )
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
    @extend_schema(
        description="El operador ve todos los intentos. Las demás cuentas ven sus intentos propios "
                    "y los de los terrenos que administran.",
        parameters=[FiltrosHistorialSerializer],
        responses={
            200: IntentoSerializer(many=True),
            400: OpenApiResponse(OpenApiTypes.OBJECT, "Filtro inválido."),
            401: SIN_SESION,
        },
    )
    def get(self, request):
        filtros = FiltrosHistorialSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        registros = intentos_visibles(request.user).select_related("punto")
        campos = {"persona": "persona_id", "terreno": "punto__terreno_id", "punto": "punto_id", "fecha": "fecha__date"}
        for campo, valor in filtros.validated_data.items():
            registros = registros.filter(**{campos[campo]: valor})
        return Response(IntentoSerializer(registros, many=True).data)
