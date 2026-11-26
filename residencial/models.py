from django.conf import settings
from django.db import models
from django.utils.crypto import salted_hmac

PROTECT = models.PROTECT


class Persona(models.Model):
    codigo = models.SlugField(unique=True)
    nombre = models.CharField(max_length=100)
    cuenta = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="persona")

    def __str__(self):
        return self.nombre


class Terreno(models.Model):
    codigo = models.SlugField(unique=True)
    nombre = models.CharField(max_length=100)
    administrador = models.ForeignKey(Persona, on_delete=PROTECT, related_name="terrenos_administrados")

    def __str__(self):
        return self.nombre


class Vivienda(models.Model):
    class Tipo(models.TextChoices):
        CASA = "casa", "Casa"
        DEPTO = "departamento", "Departamento"

    terreno = models.ForeignKey(Terreno, on_delete=PROTECT, related_name="viviendas")
    codigo = models.CharField(max_length=40)
    tipo = models.CharField(max_length=15, choices=Tipo)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["terreno", "codigo"], name="vivienda_por_terreno")]

    def __str__(self):
        return f"{self.terreno} / {self.codigo}"


class PuntoAcceso(models.Model):
    terreno = models.ForeignKey(Terreno, on_delete=PROTECT, related_name="puntos")
    codigo = models.CharField(max_length=40)
    nombre = models.CharField(max_length=100)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["terreno", "codigo"], name="punto_por_terreno")]

    def __str__(self):
        return f"{self.terreno} / {self.nombre}"


class Participacion(models.Model):
    class Rol(models.TextChoices):
        ADMIN = "propietario_administrador", "Propietario administrador"
        PROPIETARIO = "propietario", "Propietario"
        ARRENDATARIO = "arrendatario", "Arrendatario"
        CONVIVIENTE = "conviviente", "Conviviente"

    persona = models.ForeignKey(Persona, on_delete=PROTECT, related_name="participaciones")
    vivienda = models.ForeignKey(Vivienda, on_delete=PROTECT, related_name="participaciones")
    rol = models.CharField(max_length=25, choices=Rol)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["persona", "vivienda"], name="participacion_unica")]


class Empleo(models.Model):
    persona = models.ForeignKey(Persona, on_delete=PROTECT, related_name="empleos")
    terreno = models.ForeignKey(Terreno, on_delete=PROTECT, related_name="empleos")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["persona", "terreno"], name="empleo_unico")]


class Credencial(models.Model):
    persona = models.ForeignKey(Persona, on_delete=PROTECT, related_name="credenciales")
    huella = models.CharField(max_length=64, unique=True, editable=False)
    activa = models.BooleanField(default=True)

    @staticmethod
    def identificar(uid):
        return salted_hmac("smartconnect.rfid.v1", uid, algorithm="sha256").hexdigest()


class PermisoPunto(models.Model):
    persona = models.ForeignKey(Persona, on_delete=PROTECT, related_name="permisos")
    punto = models.ForeignKey(PuntoAcceso, on_delete=PROTECT, related_name="permisos")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["persona", "punto"], name="permiso_punto_unico")]


class Intento(models.Model):
    persona = models.ForeignKey(Persona, null=True, on_delete=PROTECT, related_name="intentos")
    punto = models.ForeignKey(PuntoAcceso, on_delete=PROTECT, related_name="intentos")
    medio = models.CharField(max_length=4, choices=[("app", "App"), ("rfid", "RFID")])
    huella = models.CharField(max_length=64, blank=True)
    permitido = models.BooleanField()
    motivo = models.CharField(max_length=40)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
