from django.db import models
from django.contrib.auth.models import User

class Material(models.Model):
    CATEGORIAS = [
        ('PLACA', 'Placas de Yeso'),
        ('PERFIL', 'Perfilería'),
        ('FIJACION', 'Fijaciones y Tornillos'),
        ('MASILLA', 'Masillas y Cintas'),
    ]
    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)
    medida_mm = models.CharField(max_length=10, blank=True, null=True)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio por bulto/unidad comercial")
    unidad_medida = models.CharField(max_length=20, help_text="Ej: Unidad, Rollo 75m, Balde 32kg, Caja x100")

    def __str__(self):
        return f"{self.nombre} ({self.medida_mm or 'N/A'}) - ${self.precio_unitario}"


class DatosEmpresa(models.Model):
    """Guarda la identidad comercial autónoma de cada cliente instalador (SaaS)."""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='datosempresa')
    nombre_comercial = models.CharField(max_length=100, default="Mi Empresa Drywall")
    nit_rut = models.CharField(max_length=50, blank=True, null=True)
    leyenda_comercial = models.CharField(max_length=150, default="Soluciones Técnicas de Construcción")
    logo = models.ImageField(upload_to='logos/', blank=True, null=True, help_text="Suba el logo de su empresa")

    def __str__(self):
        return f"Perfil: {self.nombre_comercial} ({self.usuario.username})"


class Proyecto(models.Model):
    # Vincula obligatoriamente el proyecto al usuario dueño de la sesión actual
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proyectos', null=True, blank=True)
    nombre_cliente = models.CharField(max_length=100)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Proyecto: {self.nombre_cliente} (ID: {self.id})"


class Ambiente(models.Model):
    TIPOS_ESTRUCTURA = [
        ('MURO_SIMPLE', 'Muro Cara Simple'),
        ('MURO_DOBLE', 'Muro Doble Cara (Divisorio)'),
        ('CIELORRASO', 'Cielorraso / Techo Suspendido'),
    ]
    TIPOS_PLACA = [
        ('ST', 'Estándar (Gris)'),
        ('RH', 'Resistente Humedad (Verde)'),
        ('RF', 'Resistente Fuego (Rosa)'),
    ]
    
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='ambientes')
    nombre_zona = models.CharField(max_length=100)
    tipo_estructura = models.CharField(max_length=20, choices=TIPOS_ESTRUCTURA)
    tipo_placa = models.CharField(max_length=5, choices=TIPOS_PLACA, default='ST')
    largo = models.FloatField()
    alto_ancho = models.FloatField()
    medida_perfil = models.CharField(max_length=10, choices=[('35', '35 mm'), ('70', '70 mm'), ('100', '100 mm')])
    puertas = models.IntegerField(default=0)
    ventanas = models.IntegerField(default=0)
    costo_mano_obra_m2 = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    con_aislacion = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre_zona} - {self.get_tipo_estructura_display()}"
