from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Credencial, Empleo, Intento, Participacion, PermisoPunto, Persona, PuntoAcceso, Terreno, Vivienda


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PruebaAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.duena = Persona.objects.get(codigo="duena")
        cls.luz = Persona.objects.get(codigo="trabajador")
        cls.norte = Terreno.objects.get(codigo="norte")
        cls.casa = Vivienda.objects.get(codigo="A-01")
        cls.depto = Vivienda.objects.get(codigo="S-02")
        cls.porton = PuntoAcceso.objects.get(codigo="N-01")

    def autenticar(self, usuario):
        cuenta = get_user_model().objects.get(username=usuario)
        token = RefreshToken.for_user(cuenta).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_cuatro_ciclos_crud_y_persistencia(self):
        self.autenticar("demo_operador")
        for ruta, datos, cambios in [
            ("personas", {"codigo": "nueva", "nombre": "Ana"}, {"nombre": "Ana Sol"}),
            ("terrenos", {"codigo": "oeste", "nombre": "Oeste", "administrador": self.duena.pk}, {"nombre": "Oeste Alto"}),
            ("viviendas", {"terreno": self.norte.pk, "codigo": "B-42", "tipo": "casa"}, {"tipo": "departamento"}),
            ("puntos-acceso", {"terreno": self.norte.pk, "codigo": "O-1", "nombre": "Patio"}, {"nombre": "Patio Este"}),
        ]:
            with self.subTest(ruta=ruta):
                base = f"/api/{ruta}/"
                creado = self.client.post(base, datos)
                self.assertEqual(creado.status_code, 201, creado.data)
                pk = creado.data["id"]
                url = f"{base}{pk}/"
                self.assertIn(pk, [fila["id"] for fila in self.client.get(base).data])
                self.assertEqual(self.client.get(url).status_code, 200)
                self.assertEqual(self.client.put(url, {**datos, **cambios}).status_code, 200)
                self.assertEqual(self.client.patch(url, cambios).status_code, 200)
                for campo, valor in cambios.items():
                    self.assertEqual(self.client.get(url).data[campo], valor)
                self.assertEqual(self.client.delete(url).status_code, 204)
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_jwt_login_renovacion_y_acceso(self):
        ruta = "/api/personas/"
        self.assertEqual(self.client.get(ruta).status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalido")
        self.assertEqual(self.client.get(ruta).status_code, 401)
        self.client.credentials()
        user = self.duena.cuenta
        user.set_password("SoloPruebaTemporal")
        user.save()
        tokens = self.client.post("/api/token/", {"username": user.username, "password": "SoloPruebaTemporal"})
        self.assertEqual(tokens.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + tokens.data["access"])
        self.assertEqual([p["id"] for p in self.client.get(ruta).data], [self.duena.pk])
        self.client.credentials()
        nuevo = self.client.post("/api/token/refresh/", {"refresh": tokens.data["refresh"]})
        self.assertEqual(nuevo.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + nuevo.data["access"])
        self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_registro_publico_guarda_la_cuenta_sin_privilegios(self):
        usuario = "registro.nuevo+1"
        clave = "  Sol y patio 28!  "
        credenciales = {"username": usuario, "password": clave}
        registro = self.client.post(
            "/api/usuarios/", {**credenciales, "is_staff": True, "is_superuser": True}, format="json"
        )
        self.assertEqual(registro.status_code, 201, registro.data)
        cuenta = get_user_model().objects.get(username=usuario)
        self.assertEqual(registro.data, {"id": cuenta.pk, "username": usuario})
        self.assertNotEqual(cuenta.password, clave)
        self.assertTrue(cuenta.check_password(clave))
        self.assertTrue(cuenta.is_active)
        self.assertFalse(cuenta.is_staff)
        self.assertFalse(cuenta.is_superuser)
        self.assertFalse(Persona.objects.filter(cuenta=cuenta).exists())

        login = self.client.post("/api/token/", credenciales, format="json")
        self.assertEqual(login.status_code, 200, login.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        viviendas = self.client.get("/api/viviendas/")
        self.assertEqual(viviendas.status_code, 200)
        self.assertEqual(viviendas.data, [])
        crear_persona = self.client.post("/api/personas/", {"codigo": "nueva-ficha", "nombre": "Nueva ficha"})
        self.assertEqual(crear_persona.status_code, 403)

    def test_registro_rechaza_datos_invalidos_y_conserva_la_cuenta_duplicada(self):
        usuarios = get_user_model().objects
        cuenta = usuarios.create_user("cuenta_existente", password="ClaveOriginal28!")
        total = usuarios.count()
        for datos, campo in [
            ({"password": "ClaveNueva28!"}, "username"),
            ({"username": "sin_clave"}, "password"),
            ({"username": "clave_vacia", "password": ""}, "password"),
            ({"username": "clave_corta", "password": "1234567"}, "password"),
            ({"username": "clave_larga", "password": "a" * 129}, "password"),
            ({"username": "nombre inválido", "password": "ClaveNueva28!"}, "username"),
            ({"username": "u" * 151, "password": "ClaveNueva28!"}, "username"),
            ({"username": cuenta.username, "password": "ClaveNueva28!"}, "username"),
            ({"username": "ｃuenta_existente", "password": "ClaveNueva28!"}, "username"),
        ]:
            with self.subTest(campo=campo, usuario=datos.get("username")):
                respuesta = self.client.post("/api/usuarios/", datos, format="json")
                self.assertEqual(respuesta.status_code, 400, respuesta.data)
                self.assertIn(campo, respuesta.data)
        self.assertEqual(usuarios.count(), total)
        cuenta.refresh_from_db()
        self.assertTrue(cuenta.check_password("ClaveOriginal28!"))
        self.assertFalse(cuenta.check_password("ClaveNueva28!"))

    def test_asignar_y_comprobar_estado_tras_cada_rechazo(self):
        self.autenticar("demo_duena")
        ruta = f"/api/viviendas/{self.casa.pk}/asignaciones/"
        body = {"persona": self.luz.pk, "rol": "arrendatario"}
        self.assertEqual(self.client.post(ruta, body).status_code, 201)
        antes = list(Participacion.objects.order_by("id").values())
        self.assertTrue(any(r["persona_id"] == self.luz.pk and r["rol"] == "arrendatario" for r in antes))
        for url, cambio, esperado in [
            (ruta, {"rol": "conviviente"}, 409),
            (f"/api/viviendas/{self.depto.pk}/asignaciones/", {}, 403),
            (ruta, {"rol": "propietario_administrador"}, 400),
        ]:
            self.assertEqual(self.client.post(url, {**body, **cambio}).status_code, esperado)
            self.assertEqual(list(Participacion.objects.order_by("id").values()), antes)
        self.autenticar("demo_gestora")
        self.assertEqual(self.client.post(ruta, body).status_code, 403)
        self.assertEqual(list(Participacion.objects.order_by("id").values()), antes)

    def test_alcance_y_baja_protegida(self):
        self.autenticar("demo_trabajador")
        self.assertEqual(self.client.post("/api/viviendas/inexistente/asignaciones/", {}).status_code, 404)
        self.assertEqual(self.client.get("/api/viviendas/").data, [])
        self.assertEqual([v["id"] for v in self.client.get("/api/terrenos/").data], [self.norte.pk])
        self.assertEqual(self.client.get(f"/api/viviendas/{self.depto.pk}/").status_code, 404)
        self.assertEqual(self.client.patch(f"/api/viviendas/{self.depto.pk}/", {"tipo": "casa"}).status_code, 403)
        self.autenticar("demo_operador")
        self.assertEqual(self.client.delete(f"/api/terrenos/{self.norte.pk}/").status_code, 409)
        self.assertTrue(Terreno.objects.filter(pk=self.norte.pk).exists())
        self.assertEqual(self.client.patch(f"/api/viviendas/{self.casa.pk}/", {"terreno": self.depto.terreno_id}).status_code, 400)

    def test_autoridad_territorial_de_creacion(self):
        self.autenticar("demo_gestora")
        body = {"terreno": self.norte.pk, "codigo": "C-02", "tipo": "casa"}
        self.assertEqual(self.client.post("/api/viviendas/", body).status_code, 201)
        ajeno = Terreno.objects.create(codigo="este", nombre="Este", administrador=self.duena)
        body["terreno"] = ajeno.pk
        self.assertEqual(self.client.post("/api/viviendas/", body).status_code, 403)
        self.assertFalse(Vivienda.objects.filter(terreno=ajeno).exists())

    def test_accesos_e_historial(self):
        self.autenticar("demo_trabajador")
        ruta = "/api/accesos/solicitudes/"
        app = {"punto": self.porton.pk, "medio": "app", "cerca": True}
        rfid = {"punto": self.porton.pk, "medio": "rfid", "uid": "DEMO-RFID-LUZ"}
        for datos, esperado in [(app, "autorizado"), ({**app, "cerca": False}, "fuera_de_proximidad"),
                                ({**app, "punto": PuntoAcceso.objects.get(codigo="N-02").pk}, "sin_permiso_punto")]:
            resultado = self.client.post(ruta, datos, format="json")
            self.assertEqual(resultado.status_code, 201)
            self.assertEqual(resultado.data["motivo"], esperado)
            self.assertEqual(resultado.data["permitido"], esperado == "autorizado")
        self.assertEqual(self.client.post(ruta, rfid).status_code, 403)
        self.autenticar("demo_operador")
        conocido = self.client.post(ruta, rfid)
        self.assertEqual(conocido.data["persona"], self.luz.pk)
        self.assertTrue(conocido.data["permitido"])
        desconocido = self.client.post(ruta, {**rfid, "uid": "NO-REGISTRADA"})
        self.assertIsNone(desconocido.data["persona"])
        self.assertEqual(desconocido.data["motivo"], "credencial_desconocida")
        self.assertEqual(len(desconocido.data["huella"]), 64)
        self.assertEqual(Intento.objects.count(), 5)
        filtros = {"persona": self.luz.pk, "terreno": self.norte.pk, "punto": self.porton.pk,
                   "fecha": timezone.localdate().isoformat()}
        self.assertEqual(len(self.client.get("/api/historial/", filtros).data), 3)
        self.autenticar("demo_residente")
        self.assertEqual(self.client.get("/api/historial/").data, [])

    def test_arrendataria_entra_sin_administrar(self):
        vecina = Persona.objects.get(codigo="vecina")
        self.assertFalse(vecina.cuenta.is_staff)
        self.autenticar("demo_vecina")
        casa = f"/api/viviendas/{self.casa.pk}/asignaciones/"
        self.assertEqual([p["rol"] for p in self.client.get(casa).data], ["arrendatario"])
        intento = self.client.post("/api/accesos/solicitudes/",
                                   {"punto": self.porton.pk, "medio": "app", "cerca": True}, format="json")
        self.assertEqual(intento.status_code, 201)
        self.assertTrue(intento.data["permitido"])
        self.assertEqual(intento.data["persona"], vecina.pk)
        asignaciones = list(Participacion.objects.order_by("pk").values())
        self.assertEqual(self.client.post(casa, {"persona": self.luz.pk, "rol": "conviviente"}).status_code, 403)
        self.assertEqual(list(Participacion.objects.order_by("pk").values()), asignaciones)

    def test_revocacion_de_vinculo_y_tarjeta(self):
        self.autenticar("demo_operador")
        datos = {"punto": self.porton.pk, "medio": "rfid", "uid": "DEMO-RFID-LUZ"}
        Empleo.objects.filter(persona=self.luz).delete()
        self.assertEqual(self.client.post("/api/accesos/solicitudes/", datos).data["motivo"], "sin_vinculo_territorial")
        Credencial.objects.update(activa=False)
        self.assertEqual(self.client.post("/api/accesos/solicitudes/", datos).data["motivo"], "credencial_inactiva")

    def test_semilla_repetible(self):
        modelos = [Persona, Terreno, Vivienda, PuntoAcceso, Participacion, Empleo, Credencial, PermisoPunto]
        antes = [m.objects.count() for m in modelos]
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual([m.objects.count() for m in modelos], antes)

    def test_cuentas_de_aula_scarlett_entra_y_kevin_ve_el_resultado(self):
        call_command("seed_demo", aula=True, stdout=StringIO())
        login = self.client.post("/api/token/", {"username": "aula_scarlett", "password": "Scarlett-Aula-TI3041!"})
        self.assertEqual(login.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + login.data["access"])
        for codigo, permitido in [("N-01", True), ("N-02", False)]:
            punto = PuntoAcceso.objects.get(codigo=codigo, terreno=self.norte)
            intento = self.client.post("/api/accesos/solicitudes/",
                                       {"punto": punto.pk, "medio": "app", "cerca": True}, format="json")
            self.assertEqual(intento.status_code, 201)
            self.assertIs(intento.data["permitido"], permitido)
        intento_id = intento.data["id"]
        url = f"/api/viviendas/{self.casa.pk}/asignaciones/"
        body = {"persona": self.luz.pk, "rol": "conviviente"}
        self.assertEqual(self.client.post(url, body).status_code, 403)
        self.assertEqual(self.client.get("/api/historial/").data[0]["id"], intento_id)
        self.client.credentials()
        login = self.client.post("/api/token/", {"username": "aula_kevin", "password": "Kevin-Aula-TI3041!"})
        self.assertEqual(login.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + login.data["access"])
        self.assertEqual(self.client.post(url, body).status_code, 201)
        self.assertTrue(self.client.login(username="aula_kevin", password="Kevin-Aula-TI3041!"))
        self.assertContains(self.client.get(reverse("admin:residencial_intento_changelist")), "Scarlett (aula)")
        kevin = get_user_model().objects.get(username="aula_kevin")
        self.assertFalse(kevin.is_superuser)
        self.assertFalse(kevin.has_perm("residencial.change_intento"))

    def test_aula_es_explicita_y_conserva_las_claves_existentes(self):
        usuarios = get_user_model().objects
        self.assertFalse(usuarios.filter(username__startswith="aula_").exists())
        anteriores = dict(usuarios.values_list("username", "password"))
        call_command("seed_demo", aula=True, stdout=StringIO())
        scarlett = usuarios.get(username="aula_scarlett")
        scarlett.set_password("ElegidaParaLaPrueba")
        scarlett.save(update_fields=["password"])
        call_command("seed_demo", aula=True, stdout=StringIO())
        self.assertTrue(usuarios.get(pk=scarlett.pk).check_password("ElegidaParaLaPrueba"))
        self.assertEqual(dict(usuarios.filter(username__in=anteriores).values_list("username", "password")), anteriores)

    def test_aula_rechaza_una_cuenta_preexistente_sin_vinculo(self):
        usuarios = get_user_model().objects
        usuarios.create_user("aula_scarlett", password="PruebaDeColision")
        with self.assertRaises(CommandError):
            call_command("seed_demo", aula=True, stdout=StringIO())
        self.assertFalse(usuarios.filter(username="aula_kevin").exists())
        self.assertTrue(usuarios.get(username="aula_scarlett").check_password("PruebaDeColision"))
