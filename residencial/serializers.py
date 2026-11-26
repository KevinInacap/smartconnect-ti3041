from collections.abc import Mapping

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Intento, Participacion, Persona, PuntoAcceso, Terreno, Vivienda


Cuenta = get_user_model()


class RegistroUsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, max_length=128, trim_whitespace=False)

    class Meta:
        model = Cuenta
        fields = ["id", "username", "password"]

    def to_internal_value(self, data):
        if isinstance(data, Mapping) and isinstance(data.get("username"), str):
            data = data.copy()
            data["username"] = Cuenta.normalize_username(data["username"])
        return super().to_internal_value(data)

    def create(self, validated_data):
        return Cuenta.objects.create_user(**validated_data)


class InicioSesionSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].trim_whitespace = False

    def validate(self, attrs):
        attrs[self.username_field] = Cuenta.normalize_username(attrs[self.username_field])
        return super().validate(attrs)


class TokensInicioSesionSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Persona
        fields = ["id", "codigo", "nombre"]


class TerrenoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Terreno
        fields = ["id", "codigo", "nombre", "administrador"]


class EnTerrenoSerializer(serializers.ModelSerializer):
    def validate_terreno(self, terreno):
        if self.instance and self.instance.terreno_id != terreno.pk:
            raise serializers.ValidationError("El terreno se conserva para mantener vínculos e historial.")
        return terreno


class ViviendaSerializer(EnTerrenoSerializer):
    class Meta:
        model = Vivienda
        fields = ["id", "terreno", "codigo", "tipo"]


class PuntoSerializer(EnTerrenoSerializer):
    class Meta:
        model = PuntoAcceso
        fields = ["id", "terreno", "codigo", "nombre"]


class ParticipacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participacion
        fields = ["id", "persona", "vivienda", "rol", "creada"]
        read_only_fields = fields


class AsignacionSerializer(serializers.Serializer):
    persona = serializers.PrimaryKeyRelatedField(queryset=Persona.objects.all())
    rol = serializers.ChoiceField(choices=[Participacion.Rol.ARRENDATARIO, Participacion.Rol.CONVIVIENTE])


class ProximidadSimulada(serializers.BooleanField):
    # En formularios RFID, la ausencia de este campo también significa «omitido».
    default_empty_html = serializers.empty


class SolicitudSerializer(serializers.Serializer):
    punto = serializers.PrimaryKeyRelatedField(queryset=PuntoAcceso.objects.all())
    medio = serializers.ChoiceField(choices=["app", "rfid"])
    cerca = ProximidadSimulada(required=False)
    uid = serializers.CharField(max_length=128, required=False, write_only=True)

    def validate(self, attrs):
        app = attrs["medio"] == "app"
        if app and ("cerca" not in attrs or "uid" in attrs):
            raise serializers.ValidationError("Para app, envíe cerca y omita uid.")
        if not app and ("uid" not in attrs or "cerca" in attrs):
            raise serializers.ValidationError("Para RFID, envíe uid y omita cerca.")
        return attrs


class IntentoSerializer(serializers.ModelSerializer):
    terreno = serializers.IntegerField(source="punto.terreno_id", read_only=True)

    class Meta:
        model = Intento
        fields = ["id", "fecha", "punto", "terreno", "persona", "medio", "permitido", "motivo", "huella"]
        read_only_fields = fields


class FiltrosHistorialSerializer(serializers.Serializer):
    persona = serializers.IntegerField(min_value=1, required=False)
    terreno = serializers.IntegerField(min_value=1, required=False)
    punto = serializers.IntegerField(min_value=1, required=False)
    fecha = serializers.DateField(required=False)
