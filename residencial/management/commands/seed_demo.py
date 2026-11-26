import os
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from residencial.models import Credencial, Empleo, Participacion, PermisoPunto, Persona, PuntoAcceso, Terreno, Vivienda


def cuenta_con_ficha(codigo, nombre, username, password, *, staff=False):
    persona, _ = Persona.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    cuenta, creada = get_user_model().objects.get_or_create(username=username)
    if creada:
        if persona.cuenta_id is not None:
            raise CommandError(f"La ficha {codigo} ya pertenece a otra cuenta.")
        cuenta.set_password(password)
        cuenta.is_staff = staff
        cuenta.save(update_fields=["password", "is_staff"])
        persona.cuenta = cuenta
        persona.save(update_fields=["cuenta"])
    elif persona.cuenta_id != cuenta.pk:
        raise CommandError(f"La cuenta {username} ya existe fuera de la semilla.")
    return persona, creada


class Command(BaseCommand):
    help = "Crea personas, viviendas y permisos ficticios para las pruebas locales."

    def add_arguments(self, parser):
        parser.add_argument("--aula", action="store_true",
                            help="Añade las cuentas de clase con claves públicas de ejemplo para el servidor local.")

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get("SMARTCONNECT_DEMO_PASSWORD") or secrets.token_urlsafe(18)
        nuevos = []
        personas = {}
        for codigo, nombre in [
            ("operador", "Alex Operaciones"), ("gestora", "Inés Rojas"),
            ("duena", "Alba Soto"), ("residente", "Darío Vega"), ("trabajador", "Luz Mora"),
            ("vecina", "Elena Vidal"),
        ]:
            username = f"demo_{codigo}"
            persona, creada = cuenta_con_ficha(codigo, nombre, username, password, staff=codigo == "operador")
            if creada:
                nuevos.append(username)
            personas[codigo] = persona
        norte, _ = Terreno.objects.get_or_create(codigo="norte", defaults={"nombre": "Parque Norte", "administrador": personas["gestora"]})
        sur, _ = Terreno.objects.get_or_create(codigo="sur", defaults={"nombre": "Mirador Sur", "administrador": personas["gestora"]})
        casa, _ = Vivienda.objects.get_or_create(terreno=norte, codigo="A-01", defaults={"tipo": "casa"})
        depto, _ = Vivienda.objects.get_or_create(terreno=sur, codigo="S-02", defaults={"tipo": "departamento"})
        for codigo, vivienda, rol in [
            ("duena", casa, Participacion.Rol.ADMIN),
            ("vecina", casa, Participacion.Rol.ARRENDATARIO),
            ("duena", depto, Participacion.Rol.ARRENDATARIO),
            ("residente", depto, Participacion.Rol.ADMIN),
        ]:
            Participacion.objects.get_or_create(persona=personas[codigo], vivienda=vivienda, defaults={"rol": rol})
        principal, _ = PuntoAcceso.objects.get_or_create(terreno=norte, codigo="N-01", defaults={"nombre": "Portón principal"})
        PuntoAcceso.objects.get_or_create(terreno=norte, codigo="N-02", defaults={"nombre": "Puerta de servicio"})
        PuntoAcceso.objects.get_or_create(terreno=sur, codigo="S-01", defaults={"nombre": "Vestíbulo"})
        Empleo.objects.get_or_create(persona=personas["trabajador"], terreno=norte)
        for codigo in ["duena", "trabajador", "vecina"]:
            PermisoPunto.objects.get_or_create(persona=personas[codigo], punto=principal)
        Credencial.objects.get_or_create(huella=Credencial.identificar("DEMO-RFID-LUZ"), defaults={"persona": personas["trabajador"]})
        if options["aula"]:
            kevin, creado = cuenta_con_ficha("aula-kevin", "Kevin (aula)", "aula_kevin",
                                             "Kevin-Aula-TI3041!", staff=True)
            if creado:
                lectura = Permission.objects.filter(content_type__app_label="residencial", codename__in=[
                    "view_persona", "view_terreno", "view_vivienda", "view_puntoacceso",
                    "view_participacion", "view_intento",
                ])
                kevin.cuenta.user_permissions.add(*lectura)
            scarlett, _ = cuenta_con_ficha("aula-scarlett", "Scarlett (aula)", "aula_scarlett",
                                           "Scarlett-Aula-TI3041!")
            for persona, rol in [(kevin, Participacion.Rol.ADMIN), (scarlett, Participacion.Rol.ARRENDATARIO)]:
                Participacion.objects.get_or_create(persona=persona, vivienda=casa, defaults={"rol": rol})
            PermisoPunto.objects.get_or_create(persona=scarlett, punto=principal)
            self.stdout.write("Cuentas de clase: aula_kevin (operador) y aula_scarlett (arrendataria).")
        if nuevos:
            self.stdout.write("Cuentas nuevas: " + ", ".join(nuevos))
            if not os.environ.get("SMARTCONNECT_DEMO_PASSWORD"):
                self.stdout.write("Clave local de las cuentas nuevas: " + password)
        self.stdout.write(self.style.SUCCESS("Datos de demostración disponibles."))
