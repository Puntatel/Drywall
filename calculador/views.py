import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse,HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

from .models import Proyecto, Ambiente, DatosEmpresa
from .utils import consolidar_proyecto_completo
from .reports import generar_pdf_presupuesto

logger = logging.getLogger(__name__)

@login_required
def panel_calculadora(request):
    """Pantalla de inicio: Tablero multi-empresa."""
    if request.method == 'POST':
        cliente = request.POST.get('cliente', '').strip()
        if not cliente:
            return HttpResponseBadRequest("El nombre del cliente es obligatorio.")
        proyecto = Proyecto.objects.create(nombre_cliente=cliente, usuario=request.user)
        return redirect('gestion_ambientes', proyecto_id=proyecto.id)
        
    proyectos = Proyecto.objects.filter(usuario=request.user).order_by('-fecha_creacion')[:5]
    return render(request, 'calculador/index.html', {'proyectos': proyectos})


@login_required
def gestion_ambientes_view(request, proyecto_id):
    """Carga de habitaciones con desperdicio ajustable."""
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, usuario=request.user)
    
    if request.method == 'POST':
        if 'agregar_ambiente' in request.POST:
            try:
                mo_val = float(request.POST.get('mano_obra') or 0)
                largo_val = float(request.POST.get('largo') or 0)
                alto_val = float(request.POST.get('alto_ancho') or 0)
                puertas_val = int(request.POST.get('puertas') or 0)
                ventanas_val = int(request.POST.get('ventanas') or 0)
                aislacion_val = request.POST.get('aislacion') == 'on'

                Ambiente.objects.create(
                    proyecto=proyecto,
                    nombre_zona=request.POST.get('nombre_zona', 'Zona sin nombre'),
                    tipo_estructura=request.POST.get('tipo_estructura'),
                    tipo_placa=request.POST.get('tipo_placa'),
                    largo=largo_val,
                    alto_ancho=alto_val,
                    medida_perfil=request.POST.get('medida_perfil'),
                    puertas=puertas_val,
                    ventanas=ventanas_val,
                    costo_mano_obra_m2=mo_val,
                    con_aislacion=aislacion_val
                )
                return redirect('gestion_ambientes', proyecto_id=proyecto.id)
            except Exception as e:
                logger.error(f"Fallo al insertar ambiente: {e}")
                return redirect('gestion_ambientes', proyecto_id=proyecto.id)
            
        elif 'eliminar_ambiente' in request.POST:
            ambiente_id = request.POST.get('ambiente_id')
            ambiente_a_borrar = get_object_or_404(Ambiente, id=ambiente_id, proyecto=proyecto)
            ambiente_a_borrar.delete()
            return redirect('gestion_ambientes', proyecto_id=proyecto.id)

    desperdicio_query = request.GET.get('desperdicio', '10')
    resultados = consolidar_proyecto_completo(proyecto.id, desperdicio_porcentaje=desperdicio_query) if proyecto.ambientes.exists() else None

    return render(request, 'calculador/proyecto_detalle.html', {
        'proyecto': proyecto,
        'resultados': resultados
    })


@login_required
def configuracion_perfil_view(request):
    """Pantalla para que cada cliente gestione de forma autónoma su marca e identidad."""
    perfil, created = DatosEmpresa.objects.get_or_create(usuario=request.user)
    mensaje = None

    if request.method == 'POST':
        perfil.nombre_comercial = request.POST.get('nombre_comercial', '').strip()
        perfil.nit_rut = request.POST.get('nit_rut', '').strip()
        perfil.leyenda_comercial = request.POST.get('leyenda_comercial', '').strip()
        
        # PROCESAMIENTO SEGURO DEL ARCHIVO DE IMAGEN
        if request.FILES.get('logo'):
            perfil.logo = request.FILES['logo']  # Guarda la imagen física en el disco
            
        perfil.save()
        mensaje = "¡Identidad comercial actualizada correctamente!"

    return render(request, 'calculador/perfil.html', {
        'perfil': perfil,
        'mensaje': mensaje
    })


@login_required
def exportar_pdf_view(request, proyecto_id):
    """Llama al módulo externo de reportes para emitir el PDF comercial neto."""
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, usuario=request.user)
    desperdicio_query = request.GET.get('desperdicio', '10')
    resultados = consolidar_proyecto_completo(proyecto.id, desperdicio_porcentaje=desperdicio_query)
    
    return generar_pdf_presupuesto(proyecto, resultados, desperdicio_query)


def registro_view(request):
    """Alta e inicio automático de nuevas constructoras."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            DatosEmpresa.objects.create(usuario=usuario, nombre_comercial=f"Empresa de {usuario.username}")
            login(request, usuario)
            return redirect('panel_calculadora')
    else:
        form = UserCreationForm()
    return render(request, 'calculador/registration/registro.html', {'form': form})
import csv
@login_required
def exportar_excel_view(request, proyecto_id):
    """Genera un archivo plano compatible con Excel (.csv) con el desglose de materiales."""
    proyecto = get_object_or_404(Proyecto, id=proyecto_id, usuario=request.user)
    
    # Capturamos el desperdicio del navegador para que coincida con la pantalla
    desperdicio_query = request.GET.get('desperdicio', '10')
    resultados = consolidar_proyecto_completo(proyecto.id, desperdicio_porcentaje=desperdicio_query)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Materiales_Obra_{proyecto.id}.csv"'
    
    # Configuración de escritura segura para Excel en español
    writer = csv.writer(response, delimiter=';')
    
    # 1. Encabezado del Presupuesto
    writer.writerow(['PRESUPUESTO GENERAL DE MATERIALES - DRYWALL'])
    writer.writerow([f'Cliente / Obra:', proyecto.nombre_cliente])
    writer.writerow([f'Superficie Neta Total:', f"{resultados['area_neta_total']} m2"])
    writer.writerow([f'Mermas Aplicadas:', f"{desperdicio_query}%"])
    writer.writerow([])  # Fila en blanco de separación

    # 2. Tabla de Insumos
    writer.writerow(['Descripcion Insumo Comercial', 'Cantidad', 'Formato Venta', 'Precio Unitario', 'Subtotal'])
    
    for item in resultados['materiales_lista']:
        # Quitamos caracteres especiales de moneda para que Excel pueda sumar los números de forma nativa
        writer.writerow([
            item['material'],
            item['cantidad'],
            item['unidad'],
            str(item['precio_unitario']).replace('.', ','),
            str(item['subtotal']).replace('.', ',')
        ])
        
    writer.writerow([])
    writer.writerow(['VALOR TOTAL DEL PRESUPUESTO', '', '', '', str(resultados['total_presupuesto']).replace('.', ',')])
    
    return response