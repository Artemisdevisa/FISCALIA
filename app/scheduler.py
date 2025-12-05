from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import atexit

scheduler = None

def iniciar_scheduler(app):
    """
    Inicia el scheduler de tareas automáticas
    """
    global scheduler
    
    if scheduler is not None:
        return scheduler
    
    scheduler = BackgroundScheduler(daemon=True)
    
    # Función wrapper para ejecutar con contexto de Flask
    def ejecutar_con_contexto():
        with app.app_context():
            from app.scheduler_service import ejecutar_tareas_programadas
            print("=" * 60)
            print("🤖 INVENTECH - Ejecutando Tareas Programadas")
            print("=" * 60)
            ejecutar_tareas_programadas()
            print("=" * 60)
    
    # Programar ejecución diaria a las 00:01
    scheduler.add_job(
        func=ejecutar_con_contexto,
        trigger=CronTrigger(hour=0, minute=1),
        id='generar_metricas_automaticas',
        name='Generar métricas automáticas mensuales',
        replace_existing=True
    )
    
    # Iniciar scheduler
    scheduler.start()
    
    # Detener scheduler cuando se cierre la aplicación
    atexit.register(lambda: scheduler.shutdown())
    
    print(f"✅ Scheduler iniciado exitosamente")
    print(f"⏰ Próxima ejecución: Mañana a las 00:01")
    print(f"📅 Tareas programadas: {len(scheduler.get_jobs())}")
    
    return scheduler