from django.urls import path
from . import views

urlpatterns = [
   
    path('', views.index, name='index'),
    path('menu/', views.menu, name='menu'),
    path('nosotros/', views.nosotros, name='nosotros'),
    path('contacto/', views.contacto, name='contacto'),

   
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro, name='registro'),

   
    path('carrito/', views.carrito, name='carrito'),
    path('procesar-pedido/', views.procesar_pedido, name='procesar_pedido'),
    path('resumen-pago/', views.resumen_pago, name='resumen_pago'),
    path('confirmacion/', views.confirmacion, name='confirmacion'),
    path('pago/', views.simulacion_pago, name='simulacion_pago'),

    # Usuario
    path('perfil/', views.perfil, name='perfil'),
    path('mis-pedidos/', views.mis_pedidos, name='mis_pedidos'),

    # Admin
    path('panel-admin/', views.panel_admin, name='panel_admin'),
    path('panel-admin/configuracion/', views.guardar_configuracion, name='guardar_configuracion'),
    path('panel-admin/pedido/<int:pedido_id>/estado/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('panel-admin/pedido/<int:pedido_id>/editar/', views.pedido_editar, name='pedido_editar'),
    path('panel-admin/cliente/<int:cliente_id>/', views.cliente_detalle, name='cliente_detalle'),

    # Gestión de productos (panel propio)
    path('panel-admin/producto/nuevo/', views.producto_nuevo, name='producto_nuevo'),
    path('panel-admin/producto/<int:producto_id>/editar/', views.producto_editar, name='producto_editar'),
    path('panel-admin/producto/<int:producto_id>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
]