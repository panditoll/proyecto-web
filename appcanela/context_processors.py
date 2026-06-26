from .models import ConfiguracionTienda


def configuracion_tienda(request):
    """
    Hace que la configuración de la tienda (horario, días, si está abierta)
    esté disponible en TODAS las plantillas sin tener que pasarla en cada vista.
    """
    config = ConfiguracionTienda.get()
    return {
        "tienda_config": config,
        "tienda_abierta": config.esta_abierto_ahora(),
    }
