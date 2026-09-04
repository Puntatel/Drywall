import math
from django.apps import apps

# Coeficientes técnicos netos base por m² (Sin desperdicio previo en las matrices)
COEF_MURO_SIMPLE = {'placa': 1.05 / 2.88, 'cinta': 1.5, 'masilla': 1.6}
COEF_MURO_DOBLE = {'placa': 2.10 / 2.88, 'cinta': 3.0, 'masilla': 3.2}
COEF_CIELORRASO = {'placa': 1.05 / 2.88, 'cinta': 1.4, 'masilla': 1.5}

def consolidar_proyecto_completo(proyecto_id, desperdicio_porcentaje=10):
    """Suma todos los ambientes, calcula perfilería y fijaciones geométricas reales y empaqueta en cajas comerciales."""
    Proyecto = apps.get_model('calculador', 'Proyecto')
    Material = apps.get_model('calculador', 'Material')
    
    proyecto = Proyecto.objects.prefetch_related('ambientes').get(id=proyecto_id)
    
    try:
        factor_desperdicio_dinamico = 1.0 + (float(desperdicio_porcentaje) / 100.0)
    except (ValueError, TypeError):
        factor_desperdicio_dinamico = 1.10
        
    # Inicializadores netos puros
    neto_placas = {'ST': 0.0, 'RH': 0.0, 'RF': 0.0}
    neto_perfiles = {'35_montante': 0.0, '35_solera': 0.0, '70_montante': 0.0, '70_solera': 0.0, '100_montante': 0.0, '100_solera': 0.0}
    neto_t1, neto_t2, neto_cinta, neto_masilla, neto_fijacion, neto_aislante, total_mo, area_total_neta = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    
    for amb in proyecto.ambientes.all():
        largo_muro = float(amb.largo)
        alto_ancho_muro = float(amb.alto_ancho)
        area_bruta = largo_muro * alto_ancho_muro
        est_tipo = str(amb.tipo_estructura).upper().strip()
        
        desc = (amb.puertas * 1.6) + (amb.ventanas * 1.2) if 'CIELO' not in est_tipo else 0
        area_neta = max(0.1, area_bruta - desc)
        area_total_neta += area_neta
        
        if 'SIMPLE' in est_tipo:
            coef = COEF_MURO_SIMPLE
        elif 'DOBLE' in est_tipo:
            coef = COEF_MURO_DOBLE
        else:
            coef = COEF_CIELORRASO
        
        # 1. PLACAS Y PASTAS (Cómputo neto directo)
        tipo_placa_key = str(amb.tipo_placa).upper().strip()
        if tipo_placa_key not in neto_placas:
            tipo_placa_key = 'ST'
            
        neto_placas[tipo_placa_key] += area_neta * coef['placa']
        neto_cinta += area_neta * coef['cinta']
        neto_masilla += area_neta * coef['masilla']
        
        if amb.con_aislacion:
            neto_aislante += area_neta * 1.05
            
        # 2. PERFILERÍA Y FIJACIONES (Geometría física real de la estructura)
        perfil_clean = str(amb.medida_perfil).replace("mm", "").strip()
        key_montante = f"{perfil_clean}_montante"
        key_solera = f"{perfil_clean}_solera"
        
        if 'CIELO' in est_tipo:
            metros_solera = (largo_muro + alto_ancho_muro) * 2
            barras_montante = ((largo_muro / 0.4) * alto_ancho_muro) / 3
            
            fijaciones = metros_solera / 0.60
            t1_tornillos = area_neta * 4.0
            t2_tornillos = area_neta * 14.0
        else:
            metros_solera = largo_muro * 2
            cantidad_montantes = (largo_muro / 0.4) + 1
            barras_montante = (cantidad_montantes * alto_ancho_muro) / 3
            
            fijaciones = metros_solera / 0.60
            t1_tornillos = cantidad_montantes * 2.0
            factor_t2 = 34.0 if 'DOBLE' in est_tipo else 17.0
            t2_tornillos = area_neta * factor_t2

        # Acumulamos los valores netos puros
        neto_perfiles[key_montante] += barras_montante
        neto_perfiles[key_solera] += metros_solera / 3
        neto_fijacion += fijaciones
        neto_t1 += t1_tornillos
        neto_t2 += t2_tornillos
        
        total_mo += float(amb.costo_mano_obra_m2 or 0) * area_neta

    # --- INGENIERÍA DE CONVERSIÓN COMERCIAL CON MERMAS UNIFICADAS ---
    empaquetados = [
        ('Placa Yeso ST (2.88 m²)', math.ceil(neto_placas['ST'] * factor_desperdicio_dinamico), 'st', 'PLACA', None),
        ('Placa Yeso RH - Humedad', math.ceil(neto_placas['RH'] * factor_desperdicio_dinamico), 'rh', 'PLACA', None),
        ('Placa Yeso RF - Fuego', math.ceil(neto_placas['RF'] * factor_desperdicio_dinamico), 'rf', 'PLACA', None),
        
        ('Montante de 35 mm (3m)', math.ceil(neto_perfiles['35_montante'] * factor_desperdicio_dinamico), 'montante', 'PERFIL', '35'),
        ('Solera de 35 mm (3m)', math.ceil(neto_perfiles['35_solera'] * factor_desperdicio_dinamico), 'solera', 'PERFIL', '35'),
        ('Montante de 70 mm (3m)', math.ceil(neto_perfiles['70_montante'] * factor_desperdicio_dinamico), 'montante', 'PERFIL', '70'),
        ('Solera de 70 mm (3m)', math.ceil(neto_perfiles['70_solera'] * factor_desperdicio_dinamico), 'solera', 'PERFIL', '70'),
        ('Montante de 100 mm (3m)', math.ceil(neto_perfiles['100_montante'] * factor_desperdicio_dinamico), 'montante', 'PERFIL', '100'),
        ('Solera de 100 mm (3m)', math.ceil(neto_perfiles['100_solera'] * factor_desperdicio_dinamico), 'solera', 'PERFIL', '100'),
        
        ('Rollo de Cinta de Papel (75 m)', math.ceil((neto_cinta * factor_desperdicio_dinamico) / 75), 'cinta', 'MASILLA', None),
        ('Balde de Masilla Lista (32 KG)', math.ceil((neto_masilla * factor_desperdicio_dinamico) / 32), 'masilla', 'MASILLA', None),
        
        ('Caja de Tornillos T1 Metal/Metal (x100 uds)', math.ceil((neto_t1 * factor_desperdicio_dinamico) / 100), 't1', 'FIJACION', None),
        ('Caja de Tornillos T2 Punta Aguja (x100 uds)', math.ceil((neto_t2 * factor_desperdicio_dinamico) / 100), 't2', 'T2', None),
        ('Fijaciones Tarugo + Tornillo Nº6 (x100 uds)', math.ceil((neto_fijacion * factor_desperdicio_dinamico) / 100), 'fijacion', 'FIJACION', None),
        
        ('Aislación Térmica / Lana de Vidrio (m²)', math.ceil(neto_aislante * factor_desperdicio_dinamico), 'aisla', 'MASILLA', None),
    ]

    items_finales = []
    costo_materiales = 0.0

    for nombre_vis, cant_paquetes, kw, cat, mm in empaquetados:
        if cant_paquetes == 0: 
            continue
        
        m_db = None
        from django.db.models import Q
        
        if cat == 'PERFIL':
            mm_string = str(mm).replace("mm", "").strip()
            letra_clave = kw.lower() if kw else ""
            m_db = Material.objects.all().filter(categoria='PERFIL', medida_mm=mm_string).filter(nombre__icontains=letra_clave).first()
            if not m_db:
                m_db = Material.objects.all().filter(categoria='PERFIL', nombre__icontains=mm_string).filter(nombre__icontains=letra_clave).first()
            if not m_db:
                m_db = Material.objects.all().filter(categoria='PERFIL', medida_mm=mm_string).first()
            if not m_db:
                m_db = Material.objects.all().filter(categoria='PERFIL', nombre__icontains=mm_string).first()
                
        elif cat == 'PLACA':
            CATEGORIA_REAL = "PLACA"
            if kw == 'rh':
                m_db = Material.objects.all().filter(categoria=CATEGORIA_REAL).filter(
                    Q(nombre__icontains='humedad') | Q(nombre__icontains='rh') | Q(nombre__icontains='verde') | Q(nombre__icontains='hidro')
                ).first()
            elif kw == 'rf':
                # --- NUEVA CORRECCIÓN COMPLETA PARA TU ARCHIVO: BUSCADOR ELÁSTICO DE PLACAS RF ---
                m_db = Material.objects.all().filter(categoria=CATEGORIA_REAL).filter(
                    Q(nombre__icontains='fuego') | Q(nombre__icontains='rf') | Q(nombre__icontains='rosa') | Q(nombre__icontains='ignifuga') | Q(nombre__icontains='resistente al fuego')
                ).first()
                if not m_db:
                    m_db = Material.objects.all().filter(nombre__icontains='rf').first()
            elif kw == 'st':
                m_db = Material.objects.all().filter(categoria=CATEGORIA_REAL).filter(
                    Q(nombre__icontains='estándar') | Q(nombre__icontains='estandar') | Q(nombre__icontains='st') | Q(nombre__icontains='común') | Q(nombre__icontains='comun')
                ).exclude(
                    Q(nombre__icontains='humedad') | Q(nombre__icontains='rh') | Q(nombre__icontains='fuego') | Q(nombre__icontains='rf') | Q(nombre__icontains='verde') | Q(nombre__icontains='rosa')
                ).first()
        else:
            m_db = Material.objects.all().filter(nombre__icontains=kw).first()

        if m_db and m_db.precio_unitario is not None:
            precio = float(m_db.precio_unitario)
            nombre_final_comercial = m_db.nombre
            unidad_comercial = m_db.unidad_medida if m_db.unidad_medida else 'Unidades'
        else:
            precio = 0.0
            nombre_final_comercial = nombre_vis
            unidad_comercial = 'm²' if kw == 'aisla' else 'Unidades'
            
        subtotal = precio * cant_paquetes
        costo_materiales += subtotal
        
        items_finales.append({
            'material': nombre_final_comercial,
            'cantidad': cant_paquetes,
            'unidad': unidad_comercial,
            'precio_unitario': round(precio, 2),
            'subtotal': round(subtotal, 2)
        })

    if area_total_neta > 0:
        precio_m2_promedio = round(total_mo / area_total_neta, 2) if total_mo > 0 else 0.0
        items_finales.append({
            'material': 'Mano de Obra Consolidada',
            'cantidad': round(area_total_neta, 2),
            'unidad': 'm²',
            'precio_unitario': precio_m2_promedio,
            'subtotal': round(total_mo, 2)
        })

    return {
        'materiales_lista': items_finales,
        'total_presupuesto': round(costo_materiales + total_mo, 2),
        'area_neta_total': round(area_total_neta, 2),
        'costo_materiales_solo': round(costo_materiales, 2),
        'costo_mo_solo': round(total_mo, 2)
    }