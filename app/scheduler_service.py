from app import db
from app.models import Item, Incidencia, Metrica, SLA
from datetime import datetime, timedelta
from calendar import monthrange

def generar_metricas_automaticas_mes_anterior():
    """
    Genera métricas automáticamente para TODOS los items del mes anterior
    Se ejecuta el día 1 de cada mes a las 00:01
    """
    
    # Obtener fecha del mes anterior
    hoy = datetime.utcnow()
    primer_dia_mes_actual = datetime(hoy.year, hoy.month, 1)
    ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(days=1)
    
    mes = ultimo_dia_mes_anterior.month
    anio = ultimo_dia_mes_anterior.year
    
    print(f"🔄 Generando métricas automáticas para {mes}/{anio}")
    
    # Obtener items ACTIVOS y NO REEMPLAZADOS
    items_reemplazados = db.session.query(Item.reemplaza_a_id).filter(
        Item.reemplaza_a_id.isnot(None)
    ).subquery()
    
    items = Item.query.filter(
        Item.estado == 'aprobado',
        Item.estado_operativo == 'activo',
        ~Item.id.in_(items_reemplazados)
    ).all()
    
    metricas_generadas = 0
    metricas_omitidas = 0
    
    for item in items:
        try:
            # Verificar si ya existe métrica para este mes
            metrica_existe = Metrica.query.filter_by(
                item_id=item.id,
                mes=mes,
                anio=anio
            ).first()
            
            if metrica_existe:
                print(f"  ⏭️  {item.codigo}: Ya existe métrica")
                metricas_omitidas += 1
                continue
            
            # Calcular rango de fechas del mes anterior
            primer_dia = datetime(anio, mes, 1)
            ultimo_dia_num = monthrange(anio, mes)[1]
            ultimo_dia = datetime(anio, mes, ultimo_dia_num, 23, 59, 59)
            
            # Contar incidencias del mes
            incidencias = Incidencia.query.filter(
                Incidencia.item_id == item.id,
                Incidencia.fecha_incidencia >= primer_dia,
                Incidencia.fecha_incidencia <= ultimo_dia
            ).count()
            
            # Obtener límite SLA
            sla = SLA.query.filter_by(item_id=item.id).first()
            
            if item.tipo == 'producto' and sla:
                limite = (sla.fallas_criticas_permitidas or 0) + (sla.fallas_menores_permitidas or 0)
            else:
                limite = 3
            
            # Calcular semáforo y porcentaje
            if incidencias == 0:
                semaforo = 'verde'
                porcentaje = 100
            elif incidencias <= limite:
                semaforo = 'amarillo'
                porcentaje = 100 - ((incidencias / limite) * 15)
                porcentaje = round(porcentaje, 1)
            else:
                semaforo = 'rojo'
                exceso = incidencias - limite
                porcentaje = max(0, 85 - (exceso * 15))
                porcentaje = round(porcentaje, 1)
            
            # Crear métrica
            metrica = Metrica(
                item_id=item.id,
                mes=mes,
                anio=anio,
                incidencias=incidencias,
                semaforo=semaforo,
                porcentaje_cumplimiento=porcentaje,
                registrado_por=1
            )
            
            db.session.add(metrica)
            metricas_generadas += 1
            
            print(f"  ✅ {item.codigo}: {incidencias} incidencias → {semaforo.upper()} {porcentaje}%")
            
        except Exception as e:
            print(f"  ❌ Error en {item.codigo}: {str(e)}")
            continue
    
    # Guardar todas las métricas
    try:
        db.session.commit()
        print(f"\n📊 RESUMEN:")
        print(f"   ✅ Generadas: {metricas_generadas}")
        print(f"   ⏭️  Omitidas: {metricas_omitidas}")
        print(f"   📅 Período: {mes}/{anio}")
        return {
            'success': True,
            'generadas': metricas_generadas,
            'omitidas': metricas_omitidas,
            'mes': mes,
            'anio': anio
        }
    except Exception as e:
        db.session.rollback()
        print(f"❌ ERROR al guardar métricas: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def ejecutar_tareas_programadas():
    """
    Ejecuta tareas programadas diarias
    """
    hoy = datetime.utcnow()
    
    print(f"🗓️  Fecha actual: {hoy.strftime('%d/%m/%Y %H:%M')}")
    
    # Si es día 1 del mes → Generar métricas
    if hoy.day == 1:
        print(f"✅ Es día 1 del mes → Generando métricas automáticas")
        resultado = generar_metricas_automaticas_mes_anterior()
        
        if resultado['success']:
            print(f"✅ Métricas generadas exitosamente")
        else:
            print(f"❌ Error generando métricas: {resultado.get('error')}")
    else:
        print(f"⏭️  Hoy es día {hoy.day} → No se generan métricas (solo día 1)")