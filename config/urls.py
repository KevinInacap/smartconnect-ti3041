from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from residencial.panel import historial_web

from residencial.views import (
    Historial, InicioSesion, PersonaViewSet, PuntoViewSet, RegistrarUsuario, SolicitarAcceso, TerrenoViewSet, ViviendaViewSet,
)

router = DefaultRouter()
router.register("personas", PersonaViewSet)
router.register("terrenos", TerrenoViewSet)
router.register("viviendas", ViviendaViewSet)
router.register("puntos-acceso", PuntoViewSet)

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="historial-web")),
    path("historial/", historial_web, name="historial-web"),
    path("historial/ingresar/", LoginView.as_view(template_name="residencial/ingresar.html",
         next_page=reverse_lazy("historial-web"), redirect_authenticated_user=True), name="ingresar-historial"),
    path("historial/salir/", LogoutView.as_view(next_page=reverse_lazy("ingresar-historial")), name="salir-historial"),
    path("admin/", admin.site.urls),
    path("api/usuarios/", RegistrarUsuario.as_view()),
    path("api/token/", InicioSesion.as_view()),
    path("api/token/refresh/", TokenRefreshView.as_view()),
    path("api/accesos/solicitudes/", SolicitarAcceso.as_view()),
    path("api/historial/", Historial.as_view()),
    path("api/esquema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/", include(router.urls)),
]
