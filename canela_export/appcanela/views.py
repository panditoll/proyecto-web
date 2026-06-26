from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from .models import Pedido, ItemPedido, Producto, PerfilCliente, ConfiguracionTienda

# Dominios de correo aceptados (proveedores conocidos)
DOMINIOS_CORREO_VALIDOS = {
    "gmail.com", "hotmail.com", "outlook.com", "outlook.es", "hotmail.es",
    "yahoo.com", "yahoo.es", "live.com", "icloud.com", "me.com",
    "protonmail.com", "proton.me", "duocuc.cl", "gmail.cl",
}


def correo_valido(correo):
    """
    Valida que el correo tenga formato correcto Y que su dominio (después del @)
    sea uno de los proveedores conocidos. Devuelve True/False.
    """
    correo = (correo or "").strip().lower()
    try:
        validate_email(correo)
    except ValidationError:
        return False
    if "@" not in correo:
        return False
    dominio = correo.rsplit("@", 1)[1]
    return dominio in DOMINIOS_CORREO_VALIDOS

def index(request):
    return render(request, 'appcanela/index.html')

def menu(request):
    categoria = (request.GET.get("categoria") or "todos").strip()

    productos_qs = Producto.objects.filter(disponible=True).order_by("id")
    categorias_validas = ["clasicos", "chocolate", "premium", "especiales"]
    if categoria in categorias_validas:
        productos_qs = productos_qs.filter(categoria=categoria)

    paginador = Paginator(productos_qs, 10)
    pagina = paginador.get_page(request.GET.get("p"))

    return render(request, 'appcanela/menu.html', {
        'productos': pagina,
        'categoria_actual': categoria,
    })

def nosotros(request):
    return render(request, 'appcanela/nosotros.html')


@require_POST
def contacto(request):
    """
    Procesa el formulario de contacto. Simula el envío de un correo
    (con EMAIL_BACKEND de consola, el correo se imprime en la terminal)
    y muestra un mensaje de agradecimiento al usuario.
    """
    nombre = (request.POST.get("nombre") or "").strip()
    correo = (request.POST.get("correo") or "").strip()
    tipo = (request.POST.get("tipo_consulta") or "").strip()
    mensaje = (request.POST.get("mensaje") or "").strip()

    # Validación básica
    if not nombre or not mensaje:
        messages.error(request, "Por favor completa tu nombre y mensaje.")
        return redirect("/nosotros/#contacto")
    if not correo_valido(correo):
        messages.error(request, "Usa un correo válido de un proveedor conocido (ej: gmail.com, hotmail.com).")
        return redirect("/nosotros/#contacto")

    # Simulación de envío de correo (se imprime en consola)
    cuerpo = (
        f"Nueva consulta de contacto\n"
        f"Nombre: {nombre}\n"
        f"Correo: {correo}\n"
        f"Tipo: {tipo}\n"
        f"Mensaje: {mensaje}\n"
    )
    try:
        send_mail(
            subject=f"Contacto Cinnarolls — {nombre}",
            message=cuerpo,
            from_email=None,
            recipient_list=["contacto@cinnarolls.cl"],
            fail_silently=True,
        )
    except Exception:
        pass  # aunque falle el envío, no rompemos la experiencia del usuario

    messages.success(
        request,
        "¡Muchas gracias por escribirnos! Hemos recibido tu mensaje y te "
        "responderemos a la brevedad."
    )
    return redirect("/nosotros/#contacto")

def carrito(request):
    return render(request, 'appcanela/carrito.html')

def login_view(request):
    if request.method == "POST":
        correo = request.POST.get("correo")
        password = request.POST.get("password")
        try:
            user_obj = User.objects.get(email=correo)
        except User.DoesNotExist:
            messages.error(request, "Usuario no encontrado")
            return redirect("login")
        user = authenticate(request, username=user_obj.username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get("next", "index"))
        else:
            messages.error(request, "Contraseña incorrecta")
    return render(request, 'appcanela/login.html')

@require_POST
def logout_view(request):
    logout(request)
    return redirect("index")

def registro(request):
    if request.method == "POST":
        nombre = (request.POST.get("nombre") or "").strip()
        correo = (request.POST.get("correo") or "").strip()
        telefono = (request.POST.get("telefono") or "").strip()
        fecha = request.POST.get("fecha_nacimiento")
        password = request.POST.get("password") or ""
        username = correo

        # Validar nombre: obligatorio y largo razonable
        if not nombre:
            messages.error(request, "El nombre es obligatorio.")
            return redirect("registro")
        if len(nombre) > 100:
            messages.error(request, "El nombre es demasiado largo (máximo 100 caracteres).")
            return redirect("registro")

        # Validar correo: obligatorio y de un proveedor conocido (gmail, hotmail, etc.)
        if not correo:
            messages.error(request, "El correo es obligatorio.")
            return redirect("registro")
        if not correo_valido(correo):
            messages.error(request, "Usa un correo válido de un proveedor conocido (ej: gmail.com, hotmail.com, outlook.com).")
            return redirect("registro")
        if len(correo) > 254:
            messages.error(request, "El correo es demasiado largo.")
            return redirect("registro")

        # Validar teléfono: opcional, pero si viene debe ser +569 + 8 dígitos
        if telefono:
            solo_digitos = telefono.replace("+", "")
            if not (solo_digitos.startswith("569") and solo_digitos[3:].isdigit() and len(solo_digitos) == 11):
                messages.error(request, "El teléfono debe tener 8 dígitos (formato +569 XXXXXXXX).")
                return redirect("registro")

        # Validar contraseña mínima
        if len(password) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
            return redirect("registro")

        if User.objects.filter(username=username).exists():
            messages.info(request, "El usuario ya existe")
            return redirect("registro")
        user = User.objects.create_user(
            username=username,
            email=correo,
            password=password,
            first_name=nombre
        )
        PerfilCliente.objects.create(
            user=user,
            telefono=telefono,
            fecha_nacimiento=fecha if fecha else None
        )
        login(request, user)
        return redirect("index")
    return render(request, 'appcanela/registro.html')

@require_POST
def procesar_pedido(request):
    # No se puede comprar fuera del horario de atención (aunque manipulen el HTML)
    config = ConfiguracionTienda.get()
    if not config.esta_abierto_ahora():
        messages.error(
            request,
            f"Estamos cerrados. Atendemos de {config.hora_apertura.strftime('%H:%M')} "
            f"a {config.hora_cierre.strftime('%H:%M')} ({config.dias_texto()})."
        )
        return redirect("carrito")

    metodo_pago = request.POST.get("metodo_pago")

    # El método de pago debe ser uno de los válidos definidos en el modelo
    metodos_validos = [clave for clave, _ in Pedido.PAGO_CHOICES]
    if metodo_pago not in metodos_validos:
        messages.error(request, "Método de pago inválido.")
        return redirect("carrito")

    try:
        subtotal = int(request.POST.get("subtotal", 0))
        total = int(request.POST.get("total", 0))
        num_items = int(request.POST.get("num_items", 0))
    except (ValueError, TypeError):
        messages.error(request, "Datos inválidos en el pedido.")
        return redirect("carrito")

    # Los montos no pueden ser negativos y debe haber al menos un producto
    if subtotal < 0 or total < 0 or num_items < 1:
        messages.error(request, "El pedido no tiene productos válidos.")
        return redirect("carrito")

    # Tope de productos distintos por pedido (evita loops gigantes maliciosos)
    MAX_ITEMS = 50
    if num_items > MAX_ITEMS:
        messages.error(request, f"Un pedido no puede tener más de {MAX_ITEMS} productos distintos.")
        return redirect("carrito")

    direccion = request.POST.get("direccion", "").strip()
    fecha_entrega = request.POST.get("fecha_entrega") or None
    correo_invitado = request.POST.get("correo_invitado", "").strip()
    nombre_invitado = request.POST.get("nombre_invitado", "").strip()

    # Validar dirección: obligatoria, entre 5 y 200 caracteres
    if len(direccion) < 5:
        messages.error(request, "La dirección de entrega es demasiado corta.")
        return redirect("carrito")
    if len(direccion) > 200:
        messages.error(request, "La dirección de entrega es demasiado larga (máximo 200 caracteres).")
        return redirect("carrito")

    # Validar correo del invitado (si no está logueado)
    if not request.user.is_authenticated:
        if not nombre_invitado:
            messages.error(request, "Debes ingresar tu nombre.")
            return redirect("carrito")
        if not correo_valido(correo_invitado):
            messages.error(request, "Usa un correo válido de un proveedor conocido (ej: gmail.com, hotmail.com).")
            return redirect("carrito")

    # Validar fecha de entrega en el servidor: debe ser válida, hoy o futura,
    # y un día en que la tienda atiende (según configuración del admin)
    if fecha_entrega:
        fecha_obj = parse_date(fecha_entrega)
        if fecha_obj is None:
            messages.error(request, "La fecha de entrega no es válida.")
            return redirect("carrito")
        if fecha_obj < timezone.localdate():
            messages.error(request, "La fecha de entrega no puede ser un día pasado.")
            return redirect("carrito")
        config = ConfiguracionTienda.get()
        if not config.atiende_en_dia(fecha_obj):
            messages.error(request, "No atendemos el día seleccionado. Por favor elige otro.")
            return redirect("carrito")
    else:
        messages.error(request, "Debes elegir una fecha de entrega.")
        return redirect("carrito")

    pedido = Pedido.objects.create(
        usuario=request.user if request.user.is_authenticated else None,
        nombre_cliente=request.user.first_name if request.user.is_authenticated else nombre_invitado,
        metodo_pago=metodo_pago,
        subtotal=subtotal,
        total=total,
        direccion_entrega=direccion,
        fecha_entrega=fecha_entrega,
        correo_invitado=correo_invitado if not request.user.is_authenticated else None,
    )
    for i in range(num_items):
        nombre = request.POST.get(f"item_nombre_{i}")
        precio = request.POST.get(f"item_precio_{i}")
        cantidad = request.POST.get(f"item_qty_{i}")
        # Solo creamos el item si los valores numéricos son realmente números
        if nombre and precio and cantidad:
            try:
                precio_int = int(precio)
                cantidad_int = int(cantidad)
            except (ValueError, TypeError):
                continue  # ignoramos un item corrupto en vez de romper todo el pedido
            if precio_int < 0 or cantidad_int < 1:
                continue
            # Recortamos el nombre por si excede el largo del campo
            ItemPedido.objects.create(
                pedido=pedido,
                nombre=nombre[:100],
                precio=precio_int,
                cantidad=cantidad_int,
            )
    request.session['ultimo_pedido_id'] = pedido.id
    return redirect("simulacion_pago")


def confirmacion(request):
    return render(request, 'appcanela/confirmacion.html')


def resumen_pago(request):
    # Página donde se eligen método de pago y datos de entrega antes de pagar.
    # El carrito vive en localStorage; el template lo lee con JS.
    return render(request, 'appcanela/resumen_pago.html')

@login_required
def perfil(request):
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-creado_en').prefetch_related('items')
    return render(request, 'appcanela/perfil.html', {'pedidos': pedidos})


@login_required
def mis_pedidos(request):
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-creado_en').prefetch_related('items')
    return render(request, 'appcanela/mis_pedidos.html', {'pedidos': pedidos})

@user_passes_test(lambda u: u.is_staff)
def panel_admin(request):
    hoy = timezone.now().date()
    pedidos_hoy = Pedido.objects.filter(creado_en__date=hoy)
    ventas_hoy = pedidos_hoy.aggregate(Sum("total"))["total__sum"] or 0

    # --- PEDIDOS: búsqueda + filtro por estado + paginación ---
    buscar = (request.GET.get("buscar") or "").strip()
    estado_filtro = (request.GET.get("estado") or "").strip()

    pedidos_qs = Pedido.objects.all().order_by("-creado_en").prefetch_related("items")

    if buscar:
        # Busca por nombre, correo de invitado, usuario o número de pedido
        filtro = Q(nombre_cliente__icontains=buscar) | \
                 Q(correo_invitado__icontains=buscar) | \
                 Q(usuario__username__icontains=buscar)
        if buscar.isdigit():
            filtro = filtro | Q(id=int(buscar))
        pedidos_qs = pedidos_qs.filter(filtro)

    if estado_filtro in ["pendiente", "preparando", "entregado", "cancelado"]:
        pedidos_qs = pedidos_qs.filter(estado=estado_filtro)

    paginador_pedidos = Paginator(pedidos_qs, 15)
    pagina_pedidos = paginador_pedidos.get_page(request.GET.get("pp"))

    # --- CLIENTES: búsqueda + paginación ---
    buscar_cliente = (request.GET.get("buscar_cliente") or "").strip()
    clientes_qs = (
        User.objects
        .filter(is_staff=False, is_superuser=False)
        .annotate(num_pedidos=Count("pedido"))
        .order_by("-date_joined")
    )
    if buscar_cliente:
        clientes_qs = clientes_qs.filter(
            Q(first_name__icontains=buscar_cliente) |
            Q(username__icontains=buscar_cliente) |
            Q(email__icontains=buscar_cliente)
        )
    paginador_clientes = Paginator(clientes_qs, 15)
    pagina_clientes = paginador_clientes.get_page(request.GET.get("pc"))

    context = {
        "pedidos_hoy_count": pedidos_hoy.count(),
        "ventas_hoy": ventas_hoy,
        "total_clientes": clientes_qs.count(),
        "productos": Producto.objects.all(),
        "ultimos_pedidos": Pedido.objects.order_by("-creado_en")[:5],
        "todos_pedidos": pagina_pedidos,          # página de pedidos
        "clientes": pagina_clientes,              # página de clientes
        "buscar": buscar,
        "estado_filtro": estado_filtro,
        "buscar_cliente": buscar_cliente,
        "config": ConfiguracionTienda.get(),
    }
    return render(request, 'appcanela/panel_admin.html', context)

@user_passes_test(lambda u: u.is_staff)
@require_POST
def cambiar_estado_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    nuevo_estado = request.POST.get("estado")
    if nuevo_estado in ["pendiente", "preparando", "entregado"]:
        pedido.estado = nuevo_estado
        pedido.save()
    return redirect("/panel-admin/?tab=pedidos")


CATEGORIAS_PRODUCTO = [
    ("clasicos", "Clásicos"),
    ("chocolate", "Chocolate"),
    ("premium", "Premium"),
    ("especiales", "Especiales"),
]

# Categorías válidas (solo las claves) para validar lo que llega del formulario
CATEGORIAS_VALIDAS = [clave for clave, _ in CATEGORIAS_PRODUCTO]

# Validación de imágenes de productos
IMAGEN_FORMATOS = {"image/jpeg", "image/png", "image/webp", "image/gif"}
IMAGEN_EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
IMAGEN_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def validar_imagen(archivo):
    """
    Verifica que el archivo subido sea una imagen real y de peso aceptable.
    Devuelve un mensaje de error (str) o None si está bien.
    """
    if not archivo:
        return None  # la imagen es opcional

    # 1) Peso máximo
    if archivo.size > IMAGEN_MAX_BYTES:
        return "La imagen no puede pesar más de 10 MB."

    # 2) Extensión del nombre
    import os as _os
    ext = _os.path.splitext(archivo.name)[1].lower()
    if ext not in IMAGEN_EXTENSIONES:
        return "Formato no permitido. Usa JPG, PNG, WEBP o GIF."

    # 3) Tipo de contenido declarado
    if getattr(archivo, "content_type", "") not in IMAGEN_FORMATOS:
        return "El archivo no es una imagen válida."

    # 4) Verificación real del contenido con Pillow (no solo confiar en el nombre)
    try:
        from PIL import Image
        archivo.seek(0)
        data = archivo.read()           # leemos los bytes una sola vez
        archivo.seek(0)                 # dejamos el puntero listo para guardar
        import io as _io
        img = Image.open(_io.BytesIO(data))
        img.verify()                    # valida que sea una imagen real
        # comprobar que el formato detectado esté entre los permitidos
        if img.format not in {"JPEG", "PNG", "WEBP", "GIF"}:
            return "Formato no permitido. Usa JPG, PNG, WEBP o GIF."
    except Exception:
        return "El archivo subido está dañado o no es una imagen real."

    return None


def validar_datos_producto(request):
    """
    Valida los datos del formulario de producto.
    Devuelve (datos, error):
      - Si todo está bien: (dict con los datos limpios, None)
      - Si hay un error: (None, "mensaje de error")
    Centraliza la validación para usarla en crear y editar.
    """
    nombre = (request.POST.get("nombre") or "").strip()
    categoria = (request.POST.get("categoria") or "").strip()
    precio_raw = (request.POST.get("precio") or "").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()

    # 1) El nombre no puede quedar vacío
    if not nombre:
        return None, "El nombre del producto es obligatorio."

    # 1b) El nombre no puede exceder el largo del campo (100)
    if len(nombre) > 100:
        return None, "El nombre es demasiado largo (máximo 100 caracteres)."

    # 1c) La descripción no puede ser excesiva
    if len(descripcion) > 500:
        return None, "La descripción es demasiado larga (máximo 500 caracteres)."

    # 2) La categoría debe ser una de las permitidas
    if categoria not in CATEGORIAS_VALIDAS:
        return None, "La categoría seleccionada no es válida."

    # 3) El precio debe ser un número entero (no letras ni símbolos)
    if not precio_raw.isdigit():
        return None, "El precio debe contener solo números, sin letras ni símbolos."

    precio = int(precio_raw)

    # 4) El precio debe estar dentro del rango permitido (1 a 50.000)
    if precio < Producto.PRECIO_MIN:
        return None, f"El precio debe ser mayor o igual a ${Producto.PRECIO_MIN}."
    if precio > Producto.PRECIO_MAX:
        return None, f"El precio no puede superar los ${Producto.PRECIO_MAX:,}".replace(",", ".") + "."

    datos = {
        "nombre": nombre,
        "categoria": categoria,
        "precio": precio,
        "descripcion": descripcion,
        "disponible": request.POST.get("estado") == "activo",
    }
    return datos, None


@user_passes_test(lambda u: u.is_staff)
def producto_nuevo(request):
    if request.method == "POST":
        datos, error = validar_datos_producto(request)
        if error:
            # Si algo no validó, avisamos y volvemos a mostrar el formulario
            messages.error(request, error)
            return render(request, "appcanela/producto_form.html", {
                "accion": "Nuevo producto",
                "categorias": CATEGORIAS_PRODUCTO,
            })
        # Validar la imagen (formato y peso) antes de guardar
        imagen = request.FILES.get("imagen")
        error_img = validar_imagen(imagen)
        if error_img:
            messages.error(request, error_img)
            return render(request, "appcanela/producto_form.html", {
                "accion": "Nuevo producto",
                "categorias": CATEGORIAS_PRODUCTO,
            })
        Producto.objects.create(
            nombre=datos["nombre"],
            categoria=datos["categoria"],
            precio=datos["precio"],
            descripcion=datos["descripcion"],
            disponible=datos["disponible"],
            imagen=imagen,
        )
        messages.success(request, "Producto creado correctamente.")
        return redirect("/panel-admin/?tab=productos")
    return render(request, "appcanela/producto_form.html", {
        "accion": "Nuevo producto",
        "categorias": CATEGORIAS_PRODUCTO,
    })


@user_passes_test(lambda u: u.is_staff)
def producto_editar(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == "POST":
        datos, error = validar_datos_producto(request)
        if error:
            messages.error(request, error)
            return render(request, "appcanela/producto_form.html", {
                "accion": "Editar producto",
                "producto": producto,
                "categorias": CATEGORIAS_PRODUCTO,
            })
        producto.nombre = datos["nombre"]
        producto.categoria = datos["categoria"]
        producto.precio = datos["precio"]
        producto.descripcion = datos["descripcion"]
        producto.disponible = datos["disponible"]
        imagen = request.FILES.get("imagen")
        if imagen:
            error_img = validar_imagen(imagen)
            if error_img:
                messages.error(request, error_img)
                return render(request, "appcanela/producto_form.html", {
                    "accion": "Editar producto",
                    "producto": producto,
                    "categorias": CATEGORIAS_PRODUCTO,
                })
            producto.imagen = imagen
        producto.save()
        messages.success(request, "Producto actualizado correctamente.")
        return redirect("/panel-admin/?tab=productos")
    return render(request, "appcanela/producto_form.html", {
        "accion": "Editar producto",
        "producto": producto,
        "categorias": CATEGORIAS_PRODUCTO,
    })


@user_passes_test(lambda u: u.is_staff)
@require_POST
def producto_eliminar(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    producto.delete()
    return redirect("/panel-admin/?tab=productos")

def simulacion_pago(request):
    pedido_id = request.session.get('ultimo_pedido_id')
    pedido = get_object_or_404(Pedido, id=pedido_id) if pedido_id else None
    perfil = None
    if request.user.is_authenticated:
        perfil, _ = PerfilCliente.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        resultado = request.POST.get('resultado', 'aprobado')

        # Guardar tarjeta si es usuario registrado y pagó con tarjeta
        if request.user.is_authenticated and perfil and resultado == 'aprobado':
            guardar = request.POST.get('guardar_tarjeta')
            num = request.POST.get('num_tarjeta', '').replace(' ', '')
            if guardar and len(num) >= 4:
                perfil.tarjeta_ultimos4 = num[-4:]
                perfil.tarjeta_nombre = request.POST.get('nombre_tarjeta', '')
                perfil.tarjeta_vencimiento = request.POST.get('vencimiento', '')
                perfil.save()

        return render(request, 'appcanela/pago_resultado.html', {
            'pedido': pedido,
            'resultado': resultado,
        })

    return render(request, 'appcanela/simulacion_pago.html', {
        'pedido': pedido,
        'perfil': perfil,
    })

@user_passes_test(lambda u: u.is_staff)
@require_POST
def guardar_configuracion(request):
    """Guarda el horario y días de atención editados desde el panel admin."""
    config = ConfiguracionTienda.get()

    # Validar horas (vienen como "HH:MM")
    apertura = request.POST.get("hora_apertura")
    cierre = request.POST.get("hora_cierre")
    hora_ini = parse_time(apertura) if apertura else None
    hora_fin = parse_time(cierre) if cierre else None

    if not hora_ini or not hora_fin:
        messages.error(request, "Debes indicar una hora de apertura y de cierre válidas.")
        return redirect("/panel-admin/?tab=configuracion")
    if hora_ini >= hora_fin:
        messages.error(request, "La hora de apertura debe ser anterior a la de cierre.")
        return redirect("/panel-admin/?tab=configuracion")

    config.hora_apertura = hora_ini
    config.hora_cierre = hora_fin

    # Los checkboxes marcados llegan en el POST; los no marcados no aparecen.
    config.atiende_lunes = request.POST.get("atiende_lunes") == "on"
    config.atiende_martes = request.POST.get("atiende_martes") == "on"
    config.atiende_miercoles = request.POST.get("atiende_miercoles") == "on"
    config.atiende_jueves = request.POST.get("atiende_jueves") == "on"
    config.atiende_viernes = request.POST.get("atiende_viernes") == "on"
    config.atiende_sabado = request.POST.get("atiende_sabado") == "on"
    config.atiende_domingo = request.POST.get("atiende_domingo") == "on"
    config.save()

    messages.success(request, "Configuración de horario actualizada.")
    return redirect("/panel-admin/?tab=configuracion")


@user_passes_test(lambda u: u.is_staff)
def cliente_detalle(request, cliente_id):
    """Muestra el detalle de un cliente y su historial de pedidos."""
    cliente = get_object_or_404(User, id=cliente_id, is_staff=False, is_superuser=False)
    pedidos = Pedido.objects.filter(usuario=cliente).order_by("-creado_en").prefetch_related("items")
    total_gastado = pedidos.aggregate(Sum("total"))["total__sum"] or 0
    perfil = PerfilCliente.objects.filter(user=cliente).first()
    return render(request, "appcanela/cliente_detalle.html", {
        "cliente": cliente,
        "pedidos": pedidos,
        "total_gastado": total_gastado,
        "perfil": perfil,
    })


@user_passes_test(lambda u: u.is_staff)
def pedido_editar(request, pedido_id):
    """Permite al admin corregir dirección/fecha/estado, cancelar o borrar un pedido."""
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if request.method == "POST":
        accion = request.POST.get("accion")

        # Borrar el pedido por completo
        if accion == "borrar":
            pedido.delete()
            messages.success(request, "Pedido eliminado correctamente.")
            return redirect("/panel-admin/?tab=pedidos")

        # Cancelar el pedido (sin borrarlo)
        if accion == "cancelar":
            pedido.estado = "cancelado"
            pedido.save()
            messages.success(request, "Pedido cancelado.")
            return redirect("pedido_editar", pedido_id=pedido.id)

        # Guardar cambios de dirección, fecha y estado
        direccion = (request.POST.get("direccion_entrega") or "").strip()
        if direccion and (len(direccion) < 5 or len(direccion) > 200):
            messages.error(request, "La dirección debe tener entre 5 y 200 caracteres.")
            return redirect("pedido_editar", pedido_id=pedido.id)

        fecha = request.POST.get("fecha_entrega") or None
        if fecha:
            fecha_obj = parse_date(fecha)
            if fecha_obj is None:
                messages.error(request, "La fecha de entrega no es válida.")
                return redirect("pedido_editar", pedido_id=pedido.id)
            pedido.fecha_entrega = fecha_obj
        else:
            pedido.fecha_entrega = None

        estado = request.POST.get("estado")
        if estado in ["pendiente", "preparando", "entregado", "cancelado"]:
            pedido.estado = estado

        pedido.direccion_entrega = direccion
        pedido.save()
        messages.success(request, "Pedido actualizado correctamente.")
        return redirect("pedido_editar", pedido_id=pedido.id)

    return render(request, "appcanela/pedido_editar.html", {
        "pedido": pedido,
        "estados": Pedido.ESTADO_CHOICES,
    })
