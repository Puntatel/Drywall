import os
from datetime import datetime
from django.http import HttpResponse
from django.conf import settings

# Componentes ReportLab (Añadimos 'Image' para renderizar el archivo físico)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generar_pdf_presupuesto(proyecto, resultados, desperdicio_query):
    """Construye y retorna el archivo PDF adaptando el logotipo físico y datos comerciales."""
    try:
        perfil_empresa = proyecto.usuario.datosempresa
        nombre_pdf = perfil_empresa.nombre_comercial.upper()
        nit_pdf = f"NIT/RUT: {perfil_empresa.nit_rut}" if perfil_empresa.nit_rut else ""
        subtitulo_pdf = perfil_empresa.leyenda_comercial
        logo_objeto = perfil_empresa.logo if perfil_empresa.logo else None
    except Exception:
        nombre_pdf = "CONSTRUCTORA / CONTRATISTA"
        nit_pdf = "Presupuesto Comercial de Obra"
        subtitulo_pdf = "Soluciones en Construcción Seco / Drywall"
        logo_objeto = None

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Presupuesto_{proyecto.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = []
    
    styles = getSampleStyleSheet()
    company_style = ParagraphStyle('CompStyle', parent=styles['Normal'], fontSize=12, leading=16, textColor=colors.HexColor('#2c3e50'))
    meta_style = ParagraphStyle('MetaStyle', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#7f8c8d'), alignment=2)
    title_style = ParagraphStyle('TStyle', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#1a252f'), spaceBefore=14, spaceAfter=6)
    text_style = ParagraphStyle('TxtStyle', parent=styles['Normal'], fontSize=10, leading=14)
    table_text = ParagraphStyle('TableTxt', parent=styles['Normal'], fontSize=9, leading=12)
    legal_style = ParagraphStyle('LegalStyle', parent=styles['Normal'], fontSize=8, leading=12, textColor=colors.HexColor('#7f8c8d'))
    signature_style = ParagraphStyle('SigStyle', parent=styles['Normal'], fontSize=9, leading=13, alignment=1)

    # --- LÓGICA DE DETECCIÓN Y ESCALADO DEL LOGOTIPO ---
    # Creamos un contenedor de texto para la empresa por defecto
    bloque_empresa = Paragraph(f"<b>{nombre_pdf}</b><br/>{nit_pdf}<br/>{subtitulo_pdf}", company_style)
    
    # Si el usuario subió una imagen, verificamos que el archivo exista en el disco y rediseñamos la celda
    if logo_objeto and hasattr(logo_objeto, 'path'):
        ruta_fisica_logo = logo_objeto.path
        if os.path.exists(ruta_fisica_logo):
            try:
                # Cargamos la imagen y la escalamos a un ancho fijo de 80 puntos manteniendo la proporción de aspecto
                img_logo = Image(ruta_fisica_logo)
                aspecto = img_logo.imageHeight / img_logo.imageWidth
                img_logo.drawWidth = 80
                img_logo.drawHeight = 80 * aspecto
                
                # Juntamos el logo y los textos de la empresa en una pequeña tabla interna para la celda izquierda
                bloque_empresa = Table(
                    [[img_logo, Paragraph(f"<b>{nombre_pdf}</b><br/>{nit_pdf}<br/>{subtitulo_pdf}", company_style)]],
                    colWidths=[90, 164]
                )
                bloque_empresa.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0)
                ]))
            except Exception as e:
                # Si la imagen está corrupta o no se puede procesar, cae de forma segura en texto neutral
                pass

    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    cotizacion_html = f'<font size=14 color="#e74c3c"><b>COTIZACIÓN N° {proyecto.id:04d}</b></font><br/><b>Fecha de Emisión:</b> {fecha_actual}<br/><b>Ambientes:</b> {proyecto.ambientes.count()}'

    # Tabla principal del membrete superior (Ancho total 504 pt)
    header_table = Table([[bloque_empresa, Paragraph(cotizacion_html, meta_style)]], colWidths=[254, 250])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2c3e50'), spaceBefore=5, spaceAfter=15))
    
    story.append(Paragraph(f"<b>Cliente / Obra:</b> {proyecto.nombre_cliente}<br/><b>Superficie Neta Total:</b> {resultados['area_neta_total']} m² | <b>Mermas Aplicadas:</b> {desperdicio_query if 'desperidicio_query' in locals() else desperdicio_query}%", text_style))
    story.append(Spacer(1, 10))

    # Detalle de Ambientes (Ancho total 504 pt)
    story.append(Paragraph("DETALLE DE AMBIENTES / ZONAS INCLUIDAS", title_style))
    ambientes_data = [["Zona / Ambiente", "Estructura", "Placa", "Dimensiones", "Aper."]]
    for amb in proyecto.ambientes.all():
        ambientes_data.append([
            Paragraph(f"<b>{amb.nombre_zona}</b>", table_text),
            Paragraph(amb.get_tipo_estructura_display(), table_text),
            Paragraph(amb.get_tipo_placa_display(), table_text),
            Paragraph(f"{amb.largo:.2f} x {amb.alto_ancho:.2f} m", table_text),
            Paragraph(f"P: {amb.puertas} / V: {amb.ventanas}", table_text)
        ])
    tabla_ambientes = Table(ambientes_data, colWidths=[124, 130, 100, 90, 60])
    tabla_ambientes.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#34495e')), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dcdde1')), ('PADDING', (0,0), (-1,-1), 5), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(tabla_ambientes)
    story.append(Spacer(1, 15))

    # Consolidado de Materiales (Ancho total 504 pt)
    story.append(Paragraph("CONSOLIDADO GENERAL DE MATERIALES Y SERVICIOS", title_style))
    table_data = [["Descripción Insumo Comercial", "Cantidad", "Formato Venta", "Precio Unitario", "Subtotal"]]
    for item in resultados['materiales_lista']:
        table_data.append([
            item['material'], str(item['cantidad']), item['unidad'], f"$ {item['precio_unitario']:,.2f}", f"$ {item['subtotal']:,.2f}"
        ])
    table_data.append([Paragraph("<b>VALOR TOTAL DEL PRESUPUESTO</b>", text_style), "", "", "", f"$ {resultados['total_presupuesto']:,.2f}"])
    
    tabla = Table(table_data, colWidths=[204, 60, 80, 80, 80])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c3e50')), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#27ae60')), ('TEXTCOLOR', (0,-1), (-1,-1), colors.whitesmoke),
        ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#dcdde1')), ('PADDING', (0,0), (-1,-1), 6)
    ]))
    story.append(tabla)
    story.append(Spacer(1, 15))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#bdc3c7'), spaceBefore=5, spaceAfter=10))
    story.append(Paragraph("Al firmar este documento, el cliente manifiesta su conformidad. Oferta válida por 15 días.", legal_style))
    story.append(Spacer(1, 40))

    # Firmas paralelas (Ancho total 504 pt)
    firma_empresa_html = f"___________________________<br/><b>Por: {nombre_pdf}</b><br/>Representante Técnico"
    firma_cliente_html = f"___________________________<br/><b>Por: {proyecto.nombre_cliente}</b><br/>Aceptado por el Cliente"
    firmas_table = Table([[Paragraph(firma_empresa_html, signature_style), "", Paragraph(firma_cliente_html, signature_style)]], colWidths=[220, 64, 220])
    story.append(firmas_table)

    doc.build(story)
    return response