from django.contrib import admin
from .models import Cajero, PersonalJefatura, BitacoraAuditoria

@admin.register(Cajero)
class CajeroAdmin(admin.ModelAdmin):
    list_display = ('id_cajero', 'nombre', 'nombre_cajero', 'estado', 'ingreso')
    list_filter = ('estado',)
    search_fields = ('nombre', 'nombre_cajero', 'rut')

@admin.register(PersonalJefatura)
class PersonalJefaturaAdmin(admin.ModelAdmin):
    list_display = ('id_jefatura', 'nombre', 'apellido', 'cargo')
    list_filter = ('cargo',)
    exclude = ('password',)

@admin.register(BitacoraAuditoria)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'id_admin_responsable', 'id_cajero', 'accion')
    list_filter = ('accion',)
    search_fields = ('detalle',)
    readonly_fields = ('timestamp', 'id_admin_responsable', 'id_cajero', 'accion', 'detalle')
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
