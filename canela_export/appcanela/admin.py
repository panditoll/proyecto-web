from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Pedido, ItemPedido, Producto, PerfilCliente, ConfiguracionTienda


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'disponible')
    list_editable = ('precio', 'disponible')
    list_filter = ('categoria', 'disponible')
    search_fields = ('nombre',)
    # El precio usa los validadores del modelo (1 a 50.000): si se escribe
    # un valor fuera de rango o con letras, el admin de Django lo rechaza solo.


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_cliente', 'usuario', 'correo_invitado',
                    'metodo_pago', 'total', 'estado', 'creado_en')
    list_filter = ('estado', 'metodo_pago', 'creado_en')
    # Permite buscar pedidos por cliente registrado o por correo de invitado
    search_fields = ('nombre_cliente', 'correo_invitado', 'usuario__username')


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'nombre', 'precio', 'cantidad')


# --- Clientes en el panel de Django ---

# Inline para ver/editar el perfil del cliente dentro de la ficha del usuario
class PerfilClienteInline(admin.StackedInline):
    model = PerfilCliente
    can_delete = False
    verbose_name_plural = "Perfil de cliente"


# Reemplazamos el admin de User para que muestre el perfil y marque a los clientes
class CustomUserAdmin(UserAdmin):
    inlines = (PerfilClienteInline,)
    list_display = ('username', 'email', 'first_name', 'is_staff', 'date_joined')


# Re-registramos User con el admin personalizado
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# También registramos PerfilCliente por separado para verlo como lista de clientes
@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ('user', 'telefono', 'fecha_nacimiento')
    search_fields = ('user__username', 'user__email', 'telefono')


@admin.register(ConfiguracionTienda)
class ConfiguracionTiendaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'hora_apertura', 'hora_cierre')

    def has_add_permission(self, request):
        # Solo debe existir una configuración (singleton)
        return not ConfiguracionTienda.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
