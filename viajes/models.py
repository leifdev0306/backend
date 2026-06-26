from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

# ---------- Mixin de auditoría ----------
class AuditMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='%(class)s_created')
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='%(class)s_updated')
    class Meta:
        abstract = True

# ---------- Provincia ----------
class Provincia(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(max_length=10, unique=True)
    def __str__(self):
        return self.nombre

# ---------- Entidad (agencia) ----------
class Entidad(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='entidad')
    nombre = models.CharField(max_length=200)
    provincia = models.ForeignKey(Provincia, on_delete=models.SET_NULL, null=True)
    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.nombre

# ---------- Conductor ----------
class Conductor(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='conductores')
    nombre = models.CharField(max_length=100)
    carnet = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    licencia = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.nombre} ({self.carnet})"

# ---------- Vehículo ----------
class Vehiculo(models.Model):
    TIPO_CHOICES = (('bus', 'Bus'), ('minibus', 'Minibús'), ('auto', 'Auto'))
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='vehiculos')
    placa = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    capacidad = models.PositiveIntegerField()
    modelo = models.CharField(max_length=100)
    año = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.placa} - {self.modelo}"

# ---------- Ruta (origen-destino) ----------
class Ruta(models.Model):
    origen = models.ForeignKey(Provincia, on_delete=models.CASCADE, related_name='rutas_origen')
    destino = models.ForeignKey(Provincia, on_delete=models.CASCADE, related_name='rutas_destino')
    distancia_km = models.PositiveIntegerField()
    duracion_estimada = models.DurationField()
    activa = models.BooleanField(default=True)
    class Meta:
        unique_together = ('origen', 'destino')
    def __str__(self):
        return f"{self.origen} → {self.destino}"

# ---------- Viaje (principal) ----------
class Viaje(AuditMixin):
    ESTADO_CHOICES = (
        ('programado', 'Programado'),
        ('activo', 'Activo'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    )
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='viajes')
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE)
    conductor = models.ForeignKey(Conductor, on_delete=models.SET_NULL, null=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True)
    fecha_salida = models.DateTimeField()
    fecha_llegada_estimada = models.DateTimeField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    asientos_totales = models.PositiveIntegerField()
    asientos_disponibles = models.PositiveIntegerField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='programado')
    descripcion = models.TextField(blank=True)
    imagen_url = models.URLField(blank=True)

    class Meta:
        ordering = ['fecha_salida']
        indexes = [models.Index(fields=['fecha_salida', 'estado'])]

    def __str__(self):
        return f"{self.ruta} - {self.fecha_salida}"

    def actualizar_asientos(self, cambio):
        nuevo = self.asientos_disponibles + cambio
        if nuevo < 0 or nuevo > self.asientos_totales:
            raise ValueError("Cantidad de asientos inválida")
        self.asientos_disponibles = nuevo
        self.save(update_fields=['asientos_disponibles'])

# ---------- Reserva (incluye cancelación por token) ----------
class Reserva(AuditMixin):
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
    )
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name='reservas')
    nombre_cliente = models.CharField(max_length=100)
    carnet_cliente = models.CharField(max_length=20, db_index=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    asientos_reservados = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    token_cancelacion = models.CharField(max_length=64, unique=True, blank=True, null=True)

    def confirmar(self):
        if self.estado != 'pendiente':
            raise ValueError("Solo reservas pendientes pueden confirmarse")
        self.estado = 'confirmada'
        self.save()

    def cancelar(self, devolver_asientos=True):
        if self.estado == 'cancelada':
            return
        if devolver_asientos:
            self.viaje.actualizar_asientos(self.asientos_reservados)
        self.estado = 'cancelada'
        self.save()

# ---------- Puntuacion (calificación de viaje) ----------
class Puntuacion(AuditMixin):
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name='puntuaciones')
    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE, related_name='puntuacion')
    puntuacion = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

# ---------- Notificacion (para usuarios o entidades) ----------
class Notificacion(AuditMixin):
    TIPO_CHOICES = (
        ('info', 'Información'),
        ('alerta', 'Alerta'),
        ('promocion', 'Promoción'),
    )
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='notificaciones', null=True, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones', null=True, blank=True)
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='info')
    leida = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(auto_now_add=True)

# ---------- Liquidacion Mensual (financiero por entidad) ----------
class LiquidacionMensual(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='liquidaciones')
    mes = models.DateField()  # primer día del mes
    total_ingresos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_viajes = models.PositiveIntegerField(default=0)
    total_pasajeros = models.PositiveIntegerField(default=0)
    comision = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    neto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_calculo = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('entidad', 'mes')

# ---------- Configuracion (global o por entidad) ----------
class Configuracion(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='configuraciones', null=True, blank=True)
    clave = models.CharField(max_length=100)
    valor = models.TextField()
    descripcion = models.CharField(max_length=200, blank=True)

# ---------- Promocion (para home screen) ----------
class Promocion(models.Model):
    TIPO_CHOICES = (
        ('descuento', 'Descuento'),
        ('destacado', 'Destacado'),
        ('oferta', 'Oferta especial'),
    )
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='promociones')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name='promociones', null=True, blank=True)
    imagen_url = models.URLField(blank=True)
    activa = models.BooleanField(default=True)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    prioridad = models.PositiveIntegerField(default=0)  # para ordenar

    class Meta:
        ordering = ['-prioridad', 'fecha_inicio']