# -*- coding: utf-8 -*-
from flask_mail import Message
from flask import current_app
from app import mail
import threading

def enviar_email_async(app, msg):
    """Envía email de forma asíncrona"""
    with app.app_context():
        try:
            mail.send(msg)
            print(f"✅ Email enviado correctamente")
        except Exception as e:
            print(f"❌ Error al enviar email: {str(e)}")

def enviar_notificacion_incidencia(app, tecnico, incidencia, item):
    """
    Envía notificación por email cuando se asigna una incidencia a un técnico
    """
    if not tecnico.persona or not tecnico.persona.correo:
        print(f"⚠️ Técnico {tecnico.username} no tiene correo registrado")
        return False
    
    try:
        msg = Message(
            subject=f'INVENTECH - Nueva Incidencia Asignada: {incidencia.titulo}',
            recipients=[tecnico.persona.correo]
        )
        
        # Determinar color según severidad
        color_severidad = {
            'critica': '#dc3545',
            'alta': '#ffc107',
            'media': '#17a2b8',
            'baja': '#28a745'
        }.get(incidencia.severidad, '#6c757d')
        
        msg.html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                            
                            <!-- ENCABEZADO -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); padding: 30px; text-align: center;">
                                    <h1 style="color: white; margin: 0; font-size: 24px; font-weight: bold;">
                                        🔔 Nueva Incidencia Asignada
                                    </h1>
                                    <p style="color: #ecf0f1; margin: 10px 0 0 0; font-size: 14px;">
                                        Sistema INVENTECH - Fiscalía de La Libertad
                                    </p>
                                </td>
                            </tr>
                            
                            <!-- CONTENIDO -->
                            <tr>
                                <td style="padding: 30px;">
                                    
                                    <!-- SALUDO -->
                                    <p style="color: #2c3e50; font-size: 16px; margin: 0 0 20px 0;">
                                        Hola <strong>{tecnico.persona.nombres}</strong>,
                                    </p>
                                    
                                    <p style="color: #555; font-size: 14px; line-height: 1.6; margin: 0 0 25px 0;">
                                        Se le ha asignado una nueva incidencia que requiere su atención inmediata.
                                    </p>
                                    
                                    <!-- TARJETA DE INCIDENCIA -->
                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8f9fa; border-left: 4px solid {color_severidad}; border-radius: 6px; margin-bottom: 25px;">
                                        <tr>
                                            <td style="padding: 20px;">
                                                
                                                <!-- TÍTULO -->
                                                <h2 style="color: #2c3e50; font-size: 18px; margin: 0 0 15px 0; font-weight: bold;">
                                                    {incidencia.titulo}
                                                </h2>
                                                
                                                <!-- BADGES -->
                                                <div style="margin-bottom: 15px;">
                                                    <span style="display: inline-block; background-color: {color_severidad}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: bold; margin-right: 8px;">
                                                        SEVERIDAD: {incidencia.severidad.upper()}
                                                    </span>
                                                    <span style="display: inline-block; background-color: #6c757d; color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                                                        TIPO: {incidencia.tipo.upper() if incidencia.tipo else 'NO ESPECIFICADO'}
                                                    </span>
                                                </div>
                                                
                                                <!-- DESCRIPCIÓN -->
                                                {f'<p style="color: #555; font-size: 14px; line-height: 1.6; margin: 0 0 15px 0; padding: 15px; background-color: white; border-radius: 4px;">{incidencia.descripcion}</p>' if incidencia.descripcion else ''}
                                                
                                                <!-- DETALLES -->
                                                <table width="100%" cellpadding="8" cellspacing="0" style="font-size: 13px;">
                                                    <tr>
                                                        <td style="color: #666; width: 40%;"><strong>📦 Item Afectado:</strong></td>
                                                        <td style="color: #2c3e50;"><strong>{item.codigo}</strong> - {item.nombre}</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="color: #666;"><strong>📅 Fecha de Incidencia:</strong></td>
                                                        <td style="color: #2c3e50;">{incidencia.fecha_incidencia.strftime('%d/%m/%Y %H:%M')}</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="color: #666;"><strong>👥 Usuarios Afectados:</strong></td>
                                                        <td style="color: #2c3e50;">{incidencia.usuarios_afectados or 'No especificado'}</td>
                                                    </tr>
                                                    {f'''<tr>
                                                        <td style="color: #666;"><strong>🔧 Servicios Afectados:</strong></td>
                                                        <td style="color: #2c3e50;">{incidencia.servicios_afectados}</td>
                                                    </tr>''' if incidencia.servicios_afectados else ''}
                                                </table>
                                                
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <!-- BOTÓN DE ACCIÓN -->
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td align="center" style="padding: 20px 0;">
                                                <a href="http://127.0.0.1:5000/incidencias" 
                                                   style="display: inline-block; background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; text-decoration: none; padding: 14px 35px; border-radius: 6px; font-weight: bold; font-size: 14px; box-shadow: 0 2px 8px rgba(40, 167, 69, 0.3);">
                                                    Ver Incidencia en el Sistema →
                                                </a>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <!-- NOTA IMPORTANTE -->
                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 6px; margin-top: 20px;">
                                        <tr>
                                            <td style="padding: 15px;">
                                                <p style="color: #856404; font-size: 13px; margin: 0; line-height: 1.6;">
                                                    <strong>⚠️ Importante:</strong> Por favor, atienda esta incidencia lo antes posible. El sistema calculará automáticamente las métricas de cumplimiento de SLA.
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                </td>
                            </tr>
                            
                            <!-- FOOTER -->
                            <tr>
                                <td style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #dee2e6;">
                                    <p style="color: #6c757d; font-size: 12px; margin: 0 0 8px 0;">
                                        Este es un mensaje automático del Sistema INVENTECH
                                    </p>
                                    <p style="color: #6c757d; font-size: 12px; margin: 0;">
                                        <strong>Fiscalía de La Libertad</strong> • Distrito Fiscal de La Libertad
                                    </p>
                                    <p style="color: #6c757d; font-size: 11px; margin: 8px 0 0 0;">
                                        Av. América Oeste 2470, Trujillo • (044) 608-600
                                    </p>
                                </td>
                            </tr>
                            
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        '''
        
        # Enviar en segundo plano
        thread = threading.Thread(target=enviar_email_async, args=(app, msg))
        thread.start()
        
        return True
        
    except Exception as e:
        print(f"❌ Error al preparar email: {str(e)}")
        return False


def enviar_notificacion_alerta_critica(app, alerta, item, destinatarios):
    """
    Envía notificación por email cuando se genera una alerta crítica
    
    Args:
        app: Instancia de Flask
        alerta: Objeto Alerta
        item: Objeto Item relacionado
        destinatarios: Lista de correos electrónicos
    """
    if not destinatarios:
        print("⚠️ No hay destinatarios para la notificación de alerta")
        return False
    
    try:
        msg = Message(
            subject=f'🚨 ALERTA CRÍTICA - {item.codigo}: {item.nombre}',
            recipients=destinatarios
        )
        
        # Determinar color según urgencia
        color_urgencia = {
            'critica': '#dc3545',
            'alta': '#ff6b6b',
            'media': '#ffc107',
            'baja': '#28a745'
        }.get(alerta.nivel_urgencia, '#6c757d')
        
        # Icono según urgencia
        icono_urgencia = {
            'critica': '🚨',
            'alta': '⚠️',
            'media': '⚡',
            'baja': 'ℹ️'
        }.get(alerta.nivel_urgencia, '🔔')
        
        msg.html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.15);">
                            
                            <!-- ENCABEZADO CRÍTICO -->
                            <tr>
                                <td style="background: linear-gradient(135deg, {color_urgencia} 0%, #a71d2a 100%); padding: 35px; text-align: center;">
                                    <div style="font-size: 48px; margin-bottom: 10px;">{icono_urgencia}</div>
                                    <h1 style="color: white; margin: 0; font-size: 26px; font-weight: bold; text-transform: uppercase;">
                                        ALERTA {alerta.nivel_urgencia.upper()}
                                    </h1>
                                    <p style="color: #fff; margin: 10px 0 0 0; font-size: 14px; opacity: 0.95;">
                                        Sistema INVENTECH - Requiere Atención Inmediata
                                    </p>
                                </td>
                            </tr>
                            
                            <!-- CONTENIDO -->
                            <tr>
                                <td style="padding: 30px;">
                                    
                                    <!-- MENSAJE DE URGENCIA -->
                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 6px; margin-bottom: 25px;">
                                        <tr>
                                            <td style="padding: 15px;">
                                                <p style="color: #856404; font-size: 14px; margin: 0; line-height: 1.6; font-weight: 600;">
                                                    ⚠️ Se ha generado una alerta automática que requiere su atención inmediata
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <!-- INFORMACIÓN DEL ITEM -->
                                    <h2 style="color: #2c3e50; font-size: 18px; margin: 0 0 15px 0; font-weight: bold; border-bottom: 2px solid #dee2e6; padding-bottom: 10px;">
                                        📦 Item Afectado
                                    </h2>
                                    
                                    <table width="100%" cellpadding="8" cellspacing="0" style="font-size: 14px; margin-bottom: 25px;">
                                        <tr>
                                            <td style="color: #666; width: 35%;"><strong>Código:</strong></td>
                                            <td style="color: #2c3e50; font-weight: bold;">{item.codigo}</td>
                                        </tr>
                                        <tr>
                                            <td style="color: #666;"><strong>Nombre:</strong></td>
                                            <td style="color: #2c3e50;">{item.nombre}</td>
                                        </tr>
                                        <tr>
                                            <td style="color: #666;"><strong>Tipo:</strong></td>
                                            <td style="color: #2c3e50; text-transform: capitalize;">{item.tipo}</td>
                                        </tr>
                                        <tr>
                                            <td style="color: #666;"><strong>Categoría:</strong></td>
                                            <td style="color: #2c3e50;">{item.categoria or 'No especificada'}</td>
                                        </tr>
                                    </table>
                                    
                                    <!-- DETALLES DE LA ALERTA -->
                                    <h2 style="color: #2c3e50; font-size: 18px; margin: 0 0 15px 0; font-weight: bold; border-bottom: 2px solid #dee2e6; padding-bottom: 10px;">
                                        🔔 Detalles de la Alerta
                                    </h2>
                                    
                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8f9fa; border-left: 4px solid {color_urgencia}; border-radius: 6px; margin-bottom: 25px;">
                                        <tr>
                                            <td style="padding: 20px;">
                                                <p style="color: #2c3e50; font-size: 14px; line-height: 1.8; margin: 0;">
                                                    {alerta.mensaje}
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <table width="100%" cellpadding="8" cellspacing="0" style="font-size: 13px; margin-bottom: 25px;">
                                        <tr>
                                            <td style="color: #666; width: 35%;"><strong>Nivel de Urgencia:</strong></td>
                                            <td>
                                                <span style="display: inline-block; background-color: {color_urgencia}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                                                    {alerta.nivel_urgencia.upper()}
                                                </span>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="color: #666;"><strong>Tipo de Alerta:</strong></td>
                                            <td style="color: #2c3e50; text-transform: capitalize;">{alerta.tipo.replace('_', ' ')}</td>
                                        </tr>
                                        <tr>
                                            <td style="color: #666;"><strong>Fecha de Creación:</strong></td>
                                            <td style="color: #2c3e50;">{alerta.fecha_creacion.strftime('%d/%m/%Y %H:%M:%S')}</td>
                                        </tr>
                                        {f'''<tr>
                                            <td style="color: #666;"><strong>Incidencias Pendientes:</strong></td>
                                            <td style="color: #dc3545; font-weight: bold;">{alerta.incidencias_pendientes}</td>
                                        </tr>''' if alerta.incidencias_pendientes > 0 else ''}
                                    </table>
                                    
                                    <!-- BOTONES DE ACCIÓN -->
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td align="center" style="padding: 20px 0;">
                                                <a href="http://127.0.0.1:5000/alertas" 
                                                   style="display: inline-block; background: linear-gradient(135deg, {color_urgencia} 0%, #a71d2a 100%); color: white; text-decoration: none; padding: 14px 35px; border-radius: 6px; font-weight: bold; font-size: 14px; box-shadow: 0 4px 12px rgba(220, 53, 69, 0.4); margin-right: 10px;">
                                                    🚨 Ver Alerta Ahora
                                                </a>
                                                <a href="http://127.0.0.1:5000/incidencias" 
                                                   style="display: inline-block; background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: white; text-decoration: none; padding: 14px 35px; border-radius: 6px; font-weight: bold; font-size: 14px; box-shadow: 0 4px 12px rgba(44, 62, 80, 0.4);">
                                                    📋 Ver Incidencias
                                                </a>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <!-- ACCIONES RECOMENDADAS -->
                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #e3f2fd; border-left: 4px solid #2196f3; border-radius: 6px; margin-top: 20px;">
                                        <tr>
                                            <td style="padding: 15px;">
                                                <p style="color: #1565c0; font-size: 13px; margin: 0 0 10px 0; font-weight: bold;">
                                                    💡 Acciones Recomendadas:
                                                </p>
                                                <ul style="color: #1976d2; font-size: 12px; margin: 0; padding-left: 20px; line-height: 1.8;">
                                                    <li>Revisar el estado actual del item en el sistema</li>
                                                    <li>Verificar las incidencias asociadas</li>
                                                    <li>Implementar medidas correctivas inmediatas</li>
                                                    <li>Documentar las acciones realizadas</li>
                                                    {f'<li style="font-weight: bold; color: #d32f2f;">Resolver las {alerta.incidencias_pendientes} incidencias pendientes</li>' if alerta.incidencias_pendientes > 0 else ''}
                                                </ul>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                </td>
                            </tr>
                            
                            <!-- FOOTER -->
                            <tr>
                                <td style="background-color: #2c3e50; padding: 20px; text-align: center;">
                                    <p style="color: #ecf0f1; font-size: 12px; margin: 0 0 8px 0;">
                                        Este es un mensaje automático generado por el Sistema INVENTECH
                                    </p>
                                    <p style="color: #bdc3c7; font-size: 12px; margin: 0;">
                                        <strong>Fiscalía de La Libertad</strong> • Distrito Fiscal de La Libertad
                                    </p>
                                    <p style="color: #95a5a6; font-size: 11px; margin: 8px 0 0 0;">
                                        Av. América Oeste 2470, Trujillo • (044) 608-600
                                    </p>
                                </td>
                            </tr>
                            
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        '''
        
        # Enviar en segundo plano
        thread = threading.Thread(target=enviar_email_async, args=(app, msg))
        thread.start()
        
        print(f"✅ Notificación de alerta enviada a {len(destinatarios)} destinatario(s)")
        return True
        
    except Exception as e:
        print(f"❌ Error al preparar notificación de alerta: {str(e)}")
        return False