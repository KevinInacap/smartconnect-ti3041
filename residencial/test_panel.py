from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Empleo, Intento, PermisoPunto, Persona, PuntoAcceso, Terreno


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PruebasPanel(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.operador = usuarios.create_user("operador", is_staff=True)
        cls.admin = usuarios.create_user("administradora")
        cls.usuario = usuarios.create_user("trabajadora", password="clave-local-de-prueba")
        cls.sin_ficha = usuarios.create_user("sin-ficha")
        gestora = Persona.objects.create(cuenta=cls.admin, nombre="Gestora", codigo="gestora")
        cls.persona = Persona.objects.create(cuenta=cls.usuario, nombre="Luz", codigo="luz")
        norte = Terreno.objects.create(codigo="norte", nombre="Parque Norte", administrador=gestora)
        sur = Terreno.objects.create(codigo="sur", nombre="Parque Sur", administrador=cls.persona)
        cls.porton = PuntoAcceso.objects.create(terreno=norte, codigo="N-01", nombre="Portón norte")
        cls.servicio = PuntoAcceso.objects.create(terreno=norte, codigo="N-02", nombre="Servicio")
        cls.ajeno = PuntoAcceso.objects.create(terreno=sur, codigo="S-01", nombre="Portón sur")
        Empleo.objects.create(persona=cls.persona, terreno=norte)
        PermisoPunto.objects.create(persona=cls.persona, punto=cls.porton)

    def test_inicio_ingreso_y_salida(self):
        self.assertRedirects(self.client.get("/"), reverse("historial-web"), fetch_redirect_response=False)
        for url in ["/historial/", "/historial/?tabla=1"]:
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 302)
            self.assertTrue(respuesta.url.startswith(reverse("ingresar-historial")))
        respuesta = self.client.post(reverse("ingresar-historial"), {"username": "trabajadora", "password": "clave-local-de-prueba"}, follow=True)
        self.assertContains(respuesta, "Historial de accesos")
        self.assertContains(respuesta, "Todavía no hay intentos")
        self.assertContains(respuesta, reverse("docs"))
        self.assertRedirects(self.client.post(reverse("salir-historial")), reverse("ingresar-historial"))
        self.assertEqual(self.client.get(reverse("historial-web")).status_code, 302)

    def test_solicitudes_jwt_aparecen_con_el_mismo_id_y_motivo(self):
        cliente_api = APIClient()
        cliente_api.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.usuario).access_token}")
        self.client.force_login(self.usuario)
        for punto, decision, motivo in [
            (self.porton, "Autorizado", "autorizado"),
            (self.servicio, "Denegado", "sin_permiso_punto"),
        ]:
            respuesta = cliente_api.post("/api/accesos/solicitudes/", {"punto": punto.pk, "medio": "app", "cerca": True}, format="json")
            self.assertEqual(respuesta.status_code, 201)
            tabla = self.client.get(reverse("historial-web"), {"tabla": 1})
            self.assertContains(tabla, f"#{respuesta.data['id']}</code>")
            self.assertContains(tabla, decision)
            self.assertContains(tabla, motivo)
            self.assertContains(tabla, punto.codigo)
            self.assertContains(tabla, self.persona.nombre)
            self.assertContains(tabla, "Hora de Santiago")
            self.assertIn("no-store", tabla["Cache-Control"])

    def test_mismo_alcance_que_la_api(self):
        personal = Intento.objects.create(persona=self.persona, punto=self.porton, medio="app", permitido=True, motivo="autorizado")
        desconocido = Intento.objects.create(punto=self.servicio, medio="rfid", permitido=False, motivo="credencial_desconocida")
        sur = Intento.objects.create(punto=self.ajeno, medio="rfid", permitido=False, motivo="credencial_desconocida")
        for cuenta, esperados in [
            (self.usuario, [sur.pk, personal.pk]),
            (self.admin, [desconocido.pk, personal.pk]),
            (self.operador, [sur.pk, desconocido.pk, personal.pk]),
            (self.sin_ficha, []),
        ]:
            with self.subTest(cuenta=cuenta.username):
                self.client.force_login(cuenta)
                cliente_api = APIClient()
                cliente_api.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(cuenta).access_token}")
                ids = [fila["id"] for fila in cliente_api.get("/api/historial/").data]
                pagina = self.client.get(reverse("historial-web"))
                self.assertEqual(ids, esperados)
                self.assertEqual([r.pk for r in pagina.context["registros"]], ids)
