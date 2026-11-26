from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from residencial.views import Historial, PersonaViewSet, PuntoViewSet, SolicitarAcceso, TerrenoViewSet, ViviendaViewSet

router = DefaultRouter()
router.register("personas", PersonaViewSet)
router.register("terrenos", TerrenoViewSet)
router.register("viviendas", ViviendaViewSet)
router.register("puntos-acceso", PuntoViewSet)

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="docs")),
    path("admin/", admin.site.urls),
    path("api/token/", TokenObtainPairView.as_view()),
    path("api/token/refresh/", TokenRefreshView.as_view()),
    path("api/accesos/solicitudes/", SolicitarAcceso.as_view()),
    path("api/historial/", Historial.as_view()),
    path("api/esquema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/", include(router.urls)),
]
