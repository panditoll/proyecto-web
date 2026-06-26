from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.dateparse import parse_time

class PerfilCliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    # Tarjeta (solo últimos 4 dígitos, nunca el número completo)
    tarjeta_ultimos4 = models.CharField(max_length=4, blank=True, null=True)
    tarjeta_nombre = models.CharField(max_length=100, blank=True, null=True)
    tarjeta_vencimiento = models.CharField(max_length=5, blank=True, null=True)

    def __str__(self):
        return self.user.username

class Producto(models.Model):
    # Límites de precio reutilizados en el modelo, el admin y las vistas
    PRECIO_MIN = 1
    PRECIO_MAX = 50000

    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=50)
    precio = models.IntegerField(
        validators=[
            MinValueValidator(PRECIO_MIN),   # no permite 0 ni negativos
            MaxValueValidator(PRECIO_MAX),   # tope de $50.000
        ]
    )
    descripcion = models.TextField(blank=True, default="")
    imagen = models.ImageField(upload_to="productos/", blank=True, null=True)
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    def precio_clp(self):
        # 2500 -> "2.500" (formato de miles chileno)
        return f"{self.precio:,}".replace(",", ".")


class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('preparando', 'Preparando'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    PAGO_CHOICES = [
        ('credito', 'Crédito'),
        ('debito', 'Débito'),
        ('efectivo', 'Efectivo'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nombre_cliente = models.CharField(max_length=100, blank=True, null=True)
    metodo_pago = models.CharField(max_length=20, choices=PAGO_CHOICES)
    subtotal = models.IntegerField()
    total = models.IntegerField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    creado_en = models.DateTimeField(auto_now_add=True)
    direccion_entrega = models.CharField(max_length=200, blank=True, null=True)
    fecha_entrega = models.DateField(blank=True, null=True)
    correo_invitado = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"Pedido #{self.id}"

class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='items')
    nombre = models.CharField(max_length=100)
    precio = models.IntegerField()
    cantidad = models.IntegerField(default=1)


import datetime as _dt


class ConfiguracionTienda(models.Model):
    """
    Configuración global de la tienda (horario y días de atención).
    Se usa como singleton: siempre existe una sola fila (id=1).
    El admin la edita desde el panel propio.
    """
    hora_apertura = models.TimeField(default=_dt.time(9, 0))
    hora_cierre = models.TimeField(default=_dt.time(18, 0))

    # Días de atención (lunes a domingo). True = atiende ese día.
    atiende_lunes = models.BooleanField(default=True)
    atiende_martes = models.BooleanField(default=True)
    atiende_miercoles = models.BooleanField(default=True)
    atiende_jueves = models.BooleanField(default=True)
    atiende_viernes = models.BooleanField(default=True)
    atiende_sabado = models.BooleanField(default=True)
    atiende_domingo = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Configuración de la tienda"
        verbose_name_plural = "Configuración de la tienda"

    def __str__(self):
        return "Configuración de la tienda"

    @classmethod
    def get(cls):
        # Devuelve la única configuración; la crea con valores por defecto si no existe.
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def dias_atencion(self):
        # Lista de booleanos indexada por weekday() de Python (0=lunes ... 6=domingo)
        return [
            self.atiende_lunes, self.atiende_martes, self.atiende_miercoles,
            self.atiende_jueves, self.atiende_viernes, self.atiende_sabado,
            self.atiende_domingo,
        ]

    def dias_atencion_json(self):
        # Mismo dato como texto JSON válido para usar en JavaScript: "[true, false, ...]"
        import json
        return json.dumps(self.dias_atencion())

    def atiende_en_dia(self, fecha):
        # ¿La tienda atiende en esa fecha (según día de la semana)?
        return self.dias_atencion()[fecha.weekday()]

    def _to_time(self, valor):
        # Asegura que el valor sea datetime.time (por si quedó como texto en la BD)
        if isinstance(valor, str):
            return parse_time(valor)
        return valor

    def esta_abierto_ahora(self):
        # ¿Está abierto en este momento (día permitido y dentro del horario)?
        from django.utils import timezone
        ahora = timezone.localtime()
        if not self.atiende_en_dia(ahora.date()):
            return False
        apertura = self._to_time(self.hora_apertura)
        cierre = self._to_time(self.hora_cierre)
        if apertura is None or cierre is None:
            return True  # si la config está incompleta, no bloqueamos
        return apertura <= ahora.time() <= cierre

    def dias_texto(self):
        # Texto legible de los días que atiende, ej: "Lun, Mar, Mié"
        nombres = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        activos = [nombres[i] for i, v in enumerate(self.dias_atencion()) if v]
        return ", ".join(activos) if activos else "Ningún día"
