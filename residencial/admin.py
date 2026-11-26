from django.contrib import admin
from .models import Credencial, Empleo, Intento, Participacion, PermisoPunto, Persona, PuntoAcceso, Terreno, Vivienda

admin.site.register([Persona, Terreno, Vivienda, PuntoAcceso, Participacion, Empleo, PermisoPunto])


@admin.register(Credencial)
class CredencialAdmin(admin.ModelAdmin):
    list_display = ["persona", "activa"]
    readonly_fields = ["persona", "huella"]

    def has_add_permission(self, request):
        return False


@admin.register(Intento)
class IntentoAdmin(admin.ModelAdmin):
    list_display = ["fecha", "punto", "persona", "medio", "permitido", "motivo"]
    list_filter = ["permitido", "medio"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
