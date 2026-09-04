import math
from .models import Material

class DrywallEngine:
    COEF_MURO_SIMPLE = {
        'placa': 1.05 / 2.88, 'montante': 2.4 / 3, 'solera': 0.9 / 3,
        't1': 12, 't2': 17, 'cinta': 1.6, 'masilla': 1.6, 'fijacion': 4
    }
    COEF_MURO_DOBLE = {
        'placa': 2.10 / 2.88, 'montante': 2.4 / 3, 'solera': 0.9 / 3,
        't1': 12, 't2': 34, 'cinta': 3.2, 'masilla': 3.2, 'fijacion': 4
    }
    COEF_CIELORRASO = {
        'placa': 1.05 / 2.88, 'montante': 3.0 / 3, 'solera': 0.8 / 3,
        't1': 14, 't2': 17, 'cinta': 1.6, 'masilla': 1.6, 'fijacion': 6
    }

    @classmethod
    def obtener_coeficientes(cls, tipo_estructura):
        if tipo_estructura == 'MURO_SIMPLE': return cls.COEF_MURO_SIMPLE
        if tipo_estructura == 'MURO_DOBLE': return cls.COEF_MURO_DOBLE
        return cls.COEF_CIELORRASO

    # Modifica la firma del método calcular para recibir 'con_aislacion':
@classmethod
def calcular(cls, largo, alto_ancho, tipo_estructura, medida_perfil, puertas=0, ventanas=0, mano_obra_m2=0.0, con_aislacion=False):
    area_bruta = largo * alto_ancho
    
    area_descontar = 0
    if tipo_estructura in ['MURO_SIMPLE', 'MURO_DOBLE']:
        area_descontar = (puertas * 1.60) + (ventanas * 1.20)
    
    area_neta = max(0.1, area_bruta - area_descontar)
    coef = cls.obtener_coeficientes(tipo_estructura)
    
    mapeo_materiales = [
        ('Placa de Yeso (2.88 m²)', 'placa'),
        (f'Montante / Perfil vertical ({medida_perfil} mm x 3m)', 'montante'),
        (f'Solera / Canal horizontal ({medida_perfil} mm x 3m)', 'solera'),
        ('Tornillo T1 (Metal-Metal)', 't1'),
        ('Tornillo T2 (Placa-Metal)', 't2'),
        ('Cinta de papel (Metros)', 'cinta'),
        ('Masilla lista (KG)', 'masilla'),
        ('Fijaciones (Tarugo + Tornillo)', 'fijacion'),
    ]

    cantidades_raw = {
        'placa': math.ceil(area_neta * coef['placa']),
        'montante': math.ceil(area_neta * coef['montante']),
        'solera': math.ceil(area_neta * coef['solera']),
        't1': math.ceil(area_neta * coef['t1']),
        't2': math.ceil(area_neta * coef['t2']),
        'cinta': round(area_neta * coef['cinta'], 2),
        'masilla': round(area_neta * coef['masilla'], 2),
        'fijacion': math.ceil(area_neta * coef['fijacion']),
    }

    # NUEVA LÓGICA: Si se activa, añadimos la lana de vidrio al mapeo y cantidades
    if con_aislacion:
        mapeo_materiales.append(('Aislación Térmica / Lana de Vidrio (m²)', 'aislante'))
        cantidades_raw['aislante'] = math.ceil(area_neta * 1.05)

    materiales_db = list(Material.objects.all())
    detalles_cotizacion = []
    costo_total = 0

    for nombre_visible, clave_busqueda in mapeo_materiales:
        cant = cantidades_raw[clave_busqueda]
        material_db = None

        if clave_busqueda in ['montante', 'solera']:
            material_db = next((m for m in materiales_db if m.categoria == 'PERFIL' and m.medida_mm == medida_perfil and clave_busqueda in m.nombre.lower()), None)
        
        if not material_db:
            material_db = next((m for m in materiales_db if clave_busqueda in m.nombre.lower()), None)

        precio = material_db.precio_unitario if material_db else 0
        subtotal = float(precio) * cant
        costo_total += subtotal

        detalles_cotizacion.append({
            'material': nombre_visible,
            'cantidad': cant,
            'precio_unitario': precio,
            'subtotal': round(subtotal, 2)
        })

    if mano_obra_m2 > 0:
        subtotal_mo = float(mano_obra_m2) * area_neta
        costo_total += subtotal_mo
        detalles_cotizacion.append({
            'material': 'Mano de Obra (Instalación y Acabado)',
            'cantidad': round(area_neta, 2),
            'precio_unitario': round(mano_obra_m2, 2),
            'subtotal': round(subtotal_mo, 2)
        })

    return {
        'area_bruta': round(area_bruta, 2),
        'area_descontada': round(area_descontar, 2),
        'area_neta': round(area_neta, 2),
        'items': detalles_cotizacion,
        'total_presupuesto': round(costo_total, 2)
    }

