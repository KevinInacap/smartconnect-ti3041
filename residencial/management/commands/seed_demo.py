import os
import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from residencial.models import Credencial, Empleo, Participacion, PermisoPunto, Persona, PuntoAcceso, Terreno, Vivienda


class Command(BaseCommand):
    help = "Crea un conjunto de datos ficticios para la defensa local."

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get("SMARTCONNECT_DEMO_PASSWORD") or secrets.token_urlsafe(18)
        nuevos = []
        personas = {}
        for codigo, nombre in [
            ("operador", "Alex Operaciones"), ("gestora", "Inés Rojas"),
            ("duena", "Alba Soto"), ("residente", "Darío Vega"), ("trabajador", "Luz Mora"),
        ]:
            persona, _ = Persona.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
            username = f"demo_{codigo}"
            cuenta, creada = get_user_model().objects.get_or_create(username=username)
            if creada:
                cuenta.set_password(password)
                cuenta.is_staff = codigo == "operador"
                cuenta.save()
                nuevos.append(username)
            if not creada and persona.cuenta_id != cuenta.pk:
                raise ValueError(f"La cuenta {username} ya existe fuera de la semilla.")
            persona.cuenta = cuenta
            persona.save(update_fields=["cuenta"])
            personas[codigo] = persona
        norte, _ = Terreno.objects.get_or_create(codigo="norte", defaults={"nombre": "Parque Norte", "administrador": personas["gestora"]})
        sur, _ = Terreno.objects.get_or_create(codigo="sur", defaults={"nombre": "Mirador Sur", "administrador": personas["gestora"]})
        casa, _ = Vivienda.objects.get_or_create(terreno=norte, codigo="A-01", defaults={"tipo": "casa"})
        depto, _ = Vivienda.objects.get_or_create(terreno=sur, codigo="S-02", defaults={"tipo": "departamento"})
        for codigo, vivienda, rol in [
            ("duena", casa, Participacion.Rol.ADMIN),
            ("duena", depto, Participacion.Rol.ARRENDATARIO),
            ("residente", depto, Participacion.Rol.ADMIN),
        ]:
            Participacion.objects.get_or_create(persona=personas[codigo], vivienda=vivienda, defaults={"rol": rol})
        principal, _ = PuntoAcceso.objects.get_or_create(terreno=norte, codigo="N-01", defaults={"nombre": "Portón principal"})
        PuntoAcceso.objects.get_or_create(terreno=norte, codigo="N-02", defaults={"nombre": "Puerta de servicio"})
        PuntoAcceso.objects.get_or_create(terreno=sur, codigo="S-01", defaults={"nombre": "Vestíbulo"})
        Empleo.objects.get_or_create(persona=personas["trabajador"], terreno=norte)
        for codigo in ["duena", "trabajador"]:
            PermisoPunto.objects.get_or_create(persona=personas[codigo], punto=principal)
        Credencial.objects.get_or_create(huella=Credencial.identificar("DEMO-RFID-LUZ"), defaults={"persona": personas["trabajador"]})
        if nuevos:
            self.stdout.write("Cuentas nuevas: " + ", ".join(nuevos))
            if not os.environ.get("SMARTCONNECT_DEMO_PASSWORD"):
                self.stdout.write("Clave local de las cuentas nuevas: " + password)
        self.stdout.write(self.style.SUCCESS("Datos de demostración disponibles."))
