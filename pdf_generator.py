from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from io import BytesIO
from datetime import datetime

# ====================================
# COLORES INSTITUCIONALES FISCALÍA
# ====================================
COLOR_PRINCIPAL = colors.HexColor('#2c3e50')      # Azul oscuro institucional
COLOR_DORADO = colors.HexColor('#d4af37')         # Dorado institucional
COLOR_DORADO_CLARO = colors.HexColor('#f4e4bc')   # Dorado claro para fondos
COLOR_GRIS_MEDIO = colors.HexColor('#dee2e6')     # Bordes
COLOR_TEXTO = colors.HexColor('#2c3e50')          # Texto principal


def generar_pdf_productos(productos):
    """
    Genera PDF profesional de productos con colores institucionales
    
    Args:
        productos: Lista de objetos Item (productos)
    
    Returns:
        BytesIO: Buffer con el PDF generado
    """
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=40,
        title='INVENTECH - Catálogo de Productos',  # ✅ Título del documento
        author='Sistema INVENTECH',                  # ✅ Autor
        subject='Catálogo de Productos - Fiscalía La Libertad'  # ✅ Asunto
    )
    
    styles = getSampleStyleSheet()
    
    # Estilo para título principal
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=COLOR_PRINCIPAL,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulo
    subtitulo_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_DORADO,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    elementos = []
    
    # ====================================
    # TÍTULO Y ENCABEZADO
    # ====================================
    elementos.append(Paragraph('CATÁLOGO DE PRODUCTOS', titulo_style))
    
    fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
    subtitulo_texto = f'Distrito Fiscal de La Libertad - Generado el {fecha_generacion}'
    elementos.append(Paragraph(subtitulo_texto, subtitulo_style))
    
    # Línea separadora dorada
    elementos.append(Spacer(1, 0.1*inch))
    
    # ====================================
    # TABLA RESUMEN
    # ====================================
    total = len(productos)
    aprobados = len([p for p in productos if p.estado == 'aprobado'])
    propuestos = len([p for p in productos if p.estado == 'propuesto'])
    
    datos_resumen = [
        ['RESUMEN GENERAL', ''],
        ['Total de Productos', str(total)],
        ['Aprobados', str(aprobados)],
        ['En Propuesta', str(propuestos)]
    ]
    
    tabla_resumen = Table(datos_resumen, colWidths=[3*inch, 2*inch])
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRINCIPAL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, -1), COLOR_DORADO_CLARO),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, COLOR_GRIS_MEDIO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 0.3*inch))
    
    # ====================================
    # TABLA PRINCIPAL DE PRODUCTOS
    # ====================================
    datos_tabla = [['CÓDIGO', 'NOMBRE', 'CATEGORÍA', 'ESTADO', 'FECHA']]
    
    for producto in productos:
        fecha_str = producto.fecha_creacion.strftime('%d/%m/%Y') if producto.fecha_creacion else '-'
        estado_upper = producto.estado.upper() if producto.estado else '-'
        
        datos_tabla.append([
            producto.codigo,
            producto.nombre[:35] + '...' if len(producto.nombre) > 35 else producto.nombre,
            producto.categoria or '-',
            estado_upper,
            fecha_str
        ])
    
    tabla_principal = Table(datos_tabla, colWidths=[0.9*inch, 2.2*inch, 1.3*inch, 1*inch, 0.9*inch])
    
    # Estilos base
    estilos_tabla = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRINCIPAL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_MEDIO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]
    
    # Filas alternas
    for i in range(1, len(datos_tabla)):
        if i % 2 == 0:
            estilos_tabla.append(('BACKGROUND', (0, i), (-1, i), COLOR_DORADO_CLARO))
        else:
            estilos_tabla.append(('BACKGROUND', (0, i), (-1, i), colors.white))
    
    tabla_principal.setStyle(TableStyle(estilos_tabla))
    elementos.append(tabla_principal)
    
    # ====================================
    # PIE DE PÁGINA
    # ====================================
    elementos.append(Spacer(1, 0.4*inch))
    
    pie_style = ParagraphStyle(
        'PieStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=COLOR_DORADO,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    pie = Paragraph(
        f"Documento generado automáticamente por INVENTECH - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        pie_style
    )
    elementos.append(pie)
    
    doc.build(elementos)
    buffer.seek(0)
    
    return buffer


def generar_pdf_servicios(servicios):
    """
    Genera PDF profesional de servicios con colores institucionales
    
    Args:
        servicios: Lista de objetos Item (servicios)
    
    Returns:
        BytesIO: Buffer con el PDF generado
    """
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=40,
        title='INVENTECH - Catálogo de Servicios',  # ✅ Título del documento
        author='Sistema INVENTECH',                  # ✅ Autor
        subject='Catálogo de Servicios - Fiscalía La Libertad'  # ✅ Asunto
    )
    
    styles = getSampleStyleSheet()
    
    # Estilo para título principal
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=COLOR_PRINCIPAL,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulo
    subtitulo_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_DORADO,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    elementos = []
    
    # ====================================
    # TÍTULO Y ENCABEZADO
    # ====================================
    elementos.append(Paragraph('CATÁLOGO DE SERVICIOS', titulo_style))
    
    fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
    subtitulo_texto = f'Distrito Fiscal de La Libertad - Generado el {fecha_generacion}'
    elementos.append(Paragraph(subtitulo_texto, subtitulo_style))
    
    # Línea separadora dorada
    elementos.append(Spacer(1, 0.1*inch))
    
    # ====================================
    # TABLA RESUMEN
    # ====================================
    total = len(servicios)
    aprobados = len([s for s in servicios if s.estado == 'aprobado'])
    propuestos = len([s for s in servicios if s.estado == 'propuesto'])
    
    datos_resumen = [
        ['RESUMEN GENERAL', ''],
        ['Total de Servicios', str(total)],
        ['Aprobados', str(aprobados)],
        ['En Propuesta', str(propuestos)]
    ]
    
    tabla_resumen = Table(datos_resumen, colWidths=[3*inch, 2*inch])
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRINCIPAL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, -1), COLOR_DORADO_CLARO),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_TEXTO),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, COLOR_GRIS_MEDIO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 0.3*inch))
    
    # ====================================
    # TABLA PRINCIPAL DE SERVICIOS
    # ====================================
    datos_tabla = [['CÓDIGO', 'NOMBRE', 'CATEGORÍA', 'ESTADO', 'FECHA']]
    
    for servicio in servicios:
        fecha_str = servicio.fecha_creacion.strftime('%d/%m/%Y') if servicio.fecha_creacion else '-'
        estado_upper = servicio.estado.upper() if servicio.estado else '-'
        
        datos_tabla.append([
            servicio.codigo,
            servicio.nombre[:35] + '...' if len(servicio.nombre) > 35 else servicio.nombre,
            servicio.categoria or '-',
            estado_upper,
            fecha_str
        ])
    
    tabla_principal = Table(datos_tabla, colWidths=[0.9*inch, 2.2*inch, 1.3*inch, 1*inch, 0.9*inch])
    
    # Estilos base
    estilos_tabla = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRINCIPAL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_MEDIO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]
    
    # Filas alternas
    for i in range(1, len(datos_tabla)):
        if i % 2 == 0:
            estilos_tabla.append(('BACKGROUND', (0, i), (-1, i), COLOR_DORADO_CLARO))
        else:
            estilos_tabla.append(('BACKGROUND', (0, i), (-1, i), colors.white))
    
    tabla_principal.setStyle(TableStyle(estilos_tabla))
    elementos.append(tabla_principal)
    
    # ====================================
    # PIE DE PÁGINA
    # ====================================
    elementos.append(Spacer(1, 0.4*inch))
    
    pie_style = ParagraphStyle(
        'PieStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=COLOR_DORADO,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    pie = Paragraph(
        f"Documento generado automáticamente por INVENTECH - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        pie_style
    )
    elementos.append(pie)
    
    doc.build(elementos)
    buffer.seek(0)
    
    return buffer


# ====================================
# GENERAR PDF DE HISTORIAL DE REEMPLAZOS
# ====================================

def generar_pdf_historial_reemplazos(item_actual, cadena_anterior, cadena_posterior):
    """
    Genera PDF profesional del historial completo de reemplazos de un item
    
    Args:
        item_actual: Diccionario con datos del item actual
        cadena_anterior: Lista de diccionarios de items anteriores
        cadena_posterior: Lista de diccionarios de items posteriores
    
    Returns:
        BytesIO: Buffer con el PDF generado
    """
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=40,
        title=f'INVENTECH - Historial de Reemplazos {item_actual["codigo"]}',
        author='Sistema INVENTECH',
        subject=f'Historial de Reemplazos - {item_actual["nombre"]}'
    )
    
    styles = getSampleStyleSheet()
    
    # Estilo para título principal
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=COLOR_PRINCIPAL,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulo
    subtitulo_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_DORADO,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para encabezados de sección
    seccion_style = ParagraphStyle(
        'SeccionStyle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=COLOR_PRINCIPAL,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    elementos = []
    
    # ====================================
    # TÍTULO Y ENCABEZADO
    # ====================================
    elementos.append(Paragraph('HISTORIAL DE REEMPLAZOS', titulo_style))
    
    fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
    subtitulo_texto = f'Distrito Fiscal de La Libertad - Generado el {fecha_generacion}'
    elementos.append(Paragraph(subtitulo_texto, subtitulo_style))
    
    # Línea separadora dorada
    elementos.append(Spacer(1, 0.1*inch))
    
    # ====================================
    # INFORMACIÓN DEL ITEM ACTUAL
    # ====================================
    elementos.append(Paragraph('ITEM ACTUAL', seccion_style))
    
    # Tabla de información del item actual
    datos_actual = [
        ['Código:', item_actual['codigo']],
        ['Nombre:', item_actual['nombre']],
        ['Tipo:', item_actual['tipo'].capitalize()],
        ['Categoría:', item_actual['categoria'] or '-'],
        ['Estado:', item_actual['estado'].upper()],
        ['Responsable:', item_actual['responsable'] or '-'],
        ['Fecha Registro:', item_actual['fecha_creacion'][:10] if item_actual.get('fecha_creacion') else '-']
    ]
    
    tabla_actual = Table(datos_actual, colWidths=[2*inch, 4*inch])
    tabla_actual.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), COLOR_DORADO_CLARO),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_MEDIO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elementos.append(tabla_actual)
    elementos.append(Spacer(1, 0.3*inch))
    
    # ====================================
    # VERSIONES ANTERIORES
    # ====================================
    if cadena_anterior:
        elementos.append(Paragraph(f'VERSIONES ANTERIORES ({len(cadena_anterior)})', seccion_style))
        elementos.append(Spacer(1, 0.1*inch))
        
        for idx, item in enumerate(reversed(cadena_anterior), 1):
            # Encabezado de versión
            datos_version = [[
                f'VERSIÓN #{idx}', 
                item['codigo'], 
                item['nombre'][:40] + '...' if len(item['nombre']) > 40 else item['nombre']
            ]]
            
            tabla_enc_version = Table(datos_version, colWidths=[1.2*inch, 1.5*inch, 3.3*inch])
            tabla_enc_version.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_GRIS_MEDIO),
                ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_TEXTO),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('ALIGN', (2, 0), (2, 0), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_MEDIO),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ]))
            
            elementos.append(tabla_enc_version)
            
            # ✅ CORRECCIÓN: Tabla de detalles con estructura correcta
            # Siempre 2 filas: info general + motivo (si existe)
            datos_detalle = [
                ['Categoría:', item['categoria'] or '-', 'Responsable:', item['responsable'] or '-'],
                ['Estado:', item['estado'].upper(), 'Fecha:', item['fecha_creacion'][:10] if item.get('fecha_creacion') else '-']
            ]
            
            tabla_detalle = Table(datos_detalle, colWidths=[1.5*inch, 1.7*inch, 1.5*inch, 1.3*inch])
            
            # Estilos base
            estilos_detalle = [
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('ALIGN', (3, 0), (3, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_MEDIO),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]
            
            tabla_detalle.setStyle(TableStyle(estilos_detalle))
            elementos.append(tabla_detalle)
            
            # ✅ MOTIVO EN TABLA SEPARADA (para evitar problemas de span)
            if item.get('motivo_reemplazo'):
                # Usar Paragraph para que el texto se ajuste automáticamente
                motivo_style = ParagraphStyle(
                    'MotivoStyle',
                    parent=styles['Normal'],
                    fontSize=8,
                    textColor=COLOR_TEXTO,
                    fontName='Helvetica',
                    leading=10
                )
                motivo_texto = item['motivo_reemplazo']
                motivo_paragraph = Paragraph(motivo_texto, motivo_style)
                
                datos_motivo = [['Motivo:', motivo_paragraph]]
                
                tabla_motivo = Table(datos_motivo, colWidths=[1.2*inch, 4.8*inch])
                tabla_motivo.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_MEDIO),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                elementos.append(tabla_motivo)
            
            elementos.append(Spacer(1, 0.15*inch))
    
    # ====================================
    # VERSIÓN ACTUAL (DESTACADA)
    # ====================================
    elementos.append(Paragraph(f'⭐ VERSIÓN ACTUAL', seccion_style))
    elementos.append(Spacer(1, 0.1*inch))
    
    numero_version_actual = len(cadena_anterior) + 1
    datos_version_actual = [[
        f'VERSIÓN #{numero_version_actual} - ACTUAL', 
        item_actual['codigo'], 
        item_actual['nombre'][:40] + '...' if len(item_actual['nombre']) > 40 else item_actual['nombre']
    ]]
    
    tabla_enc_actual = Table(datos_version_actual, colWidths=[1.2*inch, 1.5*inch, 3.3*inch])
    tabla_enc_actual.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRINCIPAL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 1, COLOR_DORADO),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ]))
    
    elementos.append(tabla_enc_actual)
    
    # Detalles destacados
    datos_detalle_actual = [
        ['Categoría:', item_actual['categoria'] or '-', 'Responsable:', item_actual['responsable'] or '-'],
        ['Estado:', item_actual['estado'].upper(), 'Fecha:', item_actual['fecha_creacion'][:10] if item_actual.get('fecha_creacion') else '-']
    ]
    
    tabla_detalle_actual = Table(datos_detalle_actual, colWidths=[1.5*inch, 1.7*inch, 1.5*inch, 1.3*inch])
    tabla_detalle_actual.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_DORADO_CLARO),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 1, COLOR_DORADO),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elementos.append(tabla_detalle_actual)
    
    # Motivo de la versión actual
    if item_actual.get('motivo_reemplazo'):
        # Usar Paragraph para que el texto se ajuste automáticamente
        motivo_style = ParagraphStyle(
            'MotivoStyle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=COLOR_TEXTO,
            fontName='Helvetica',
            leading=10
        )
        motivo_texto = item_actual['motivo_reemplazo']
        motivo_paragraph = Paragraph(motivo_texto, motivo_style)
        
        datos_motivo_actual = [['Motivo:', motivo_paragraph]]
        
        tabla_motivo_actual = Table(datos_motivo_actual, colWidths=[1.2*inch, 4.8*inch])
        tabla_motivo_actual.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_DORADO_CLARO),
            ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, COLOR_DORADO),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elementos.append(tabla_motivo_actual)
    
    elementos.append(Spacer(1, 0.3*inch))
    
    # ====================================
    # VERSIONES POSTERIORES
    # ====================================
    if cadena_posterior:
        elementos.append(Paragraph(f'VERSIONES POSTERIORES ({len(cadena_posterior)})', seccion_style))
        elementos.append(Spacer(1, 0.1*inch))
        
        for idx, item in enumerate(cadena_posterior, numero_version_actual + 1):
            # Encabezado de versión
            datos_version = [[
                f'VERSIÓN #{idx}', 
                item['codigo'], 
                item['nombre'][:40] + '...' if len(item['nombre']) > 40 else item['nombre']
            ]]
            
            tabla_enc_version = Table(datos_version, colWidths=[1.2*inch, 1.5*inch, 3.3*inch])
            tabla_enc_version.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d4edda')),
                ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_TEXTO),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('ALIGN', (2, 0), (2, 0), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_MEDIO),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ]))
            
            elementos.append(tabla_enc_version)
            
            # Detalles de la versión
            datos_detalle = [
                ['Categoría:', item['categoria'] or '-', 'Responsable:', item['responsable'] or '-'],
                ['Estado:', item['estado'].upper(), 'Fecha:', item['fecha_creacion'][:10] if item.get('fecha_creacion') else '-']
            ]
            
            tabla_detalle = Table(datos_detalle, colWidths=[1.5*inch, 1.7*inch, 1.5*inch, 1.3*inch])
            tabla_detalle.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('ALIGN', (3, 0), (3, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_MEDIO),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            elementos.append(tabla_detalle)
            
            # Motivo en tabla separada
            if item.get('motivo_reemplazo'):
                # Usar Paragraph para que el texto se ajuste automáticamente
                motivo_style = ParagraphStyle(
                    'MotivoStyle',
                    parent=styles['Normal'],
                    fontSize=8,
                    textColor=COLOR_TEXTO,
                    fontName='Helvetica',
                    leading=10
                )
                motivo_texto = item['motivo_reemplazo']
                motivo_paragraph = Paragraph(motivo_texto, motivo_style)
                
                datos_motivo = [['Motivo:', motivo_paragraph]]
                
                tabla_motivo = Table(datos_motivo, colWidths=[1.2*inch, 4.8*inch])
                tabla_motivo.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_TEXTO),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_MEDIO),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                elementos.append(tabla_motivo)
            
            elementos.append(Spacer(1, 0.15*inch))
    
    # ====================================
    # RESUMEN FINAL
    # ====================================
    elementos.append(Spacer(1, 0.2*inch))
    
    total_versiones = len(cadena_anterior) + 1 + len(cadena_posterior)
    
    resumen_parts = [f'<b>RESUMEN:</b> Esta cadena contiene <b>{total_versiones} versiones</b> en total.']
    if cadena_anterior:
        resumen_parts.append(f'Reemplazó a {len(cadena_anterior)} versión(es) anterior(es).')
    if cadena_posterior:
        resumen_parts.append(f'Ha sido reemplazado por {len(cadena_posterior)} versión(es) posterior(es).')
    else:
        resumen_parts.append('Es la versión más actual.')
    
    resumen_texto = ' '.join(resumen_parts)
    
    resumen_style = ParagraphStyle(
        'ResumenStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=COLOR_TEXTO,
        backColor=colors.HexColor('#e3f2fd'),
        borderPadding=10,
        borderWidth=1,
        borderColor=COLOR_PRINCIPAL,
        alignment=0
    )
    
    elementos.append(Paragraph(resumen_texto, resumen_style))
    
    # ====================================
    # PIE DE PÁGINA
    # ====================================
    elementos.append(Spacer(1, 0.3*inch))
    
    pie_texto = f'Documento generado automáticamente por INVENTECH - {fecha_generacion}'
    pie_style = ParagraphStyle(
        'PieStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=COLOR_DORADO,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    elementos.append(Paragraph(pie_texto, pie_style))
    
    # Construir documento
    doc.build(elementos)
    buffer.seek(0)
    
    return buffer