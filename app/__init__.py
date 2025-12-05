import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from config import config

db = SQLAlchemy()
mail = Mail()

def create_app(config_name=None):
    """Factory para crear aplicación Flask"""
    
    app = Flask(__name__)
    
    # Determinar entorno
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'production')
    
    # Cargar configuración
    app.config.from_object(config[config_name])
    
    # Validar configuraciones críticas
    config[config_name].validate_email_config()
    config[config_name].validate_whatsapp_config()
    
    # Inicializar extensiones
    db.init_app(app)
    mail.init_app(app)
    
    with app.app_context():
        # Registrar blueprints
        from app.routes import bp
        app.register_blueprint(bp)
        
        # Crear tablas (solo si no existen)
        try:
            db.create_all()
            print(f"✅ Base de datos inicializada ({config_name})")
        except Exception as e:
            print(f"⚠️  Error al crear tablas: {e}")
        
        # Iniciar scheduler solo en producción
        if config_name == 'production' or os.getenv('ENABLE_SCHEDULER') == 'true':
            try:
                from app.scheduler import iniciar_scheduler
                iniciar_scheduler(app)
                print("✅ Scheduler iniciado")
            except ImportError:
                print("⚠️  Scheduler no disponible")
            except Exception as e:
                print(f"⚠️  Error al iniciar scheduler: {e}")
    
    # Log de configuración
    print(f"\n{'='*50}")
    print(f"🚀 INVENTECH - Fiscalía La Libertad")
    print(f"{'='*50}")
    print(f"Entorno: {config_name.upper()}")
    print(f"Base de datos: {'PostgreSQL' if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite'}")
    print(f"Email: {'✅ Configurado' if app.config['MAIL_USERNAME'] else '❌ No configurado'}")
    print(f"WhatsApp: {'✅ Configurado' if app.config['WHATSAPP_PHONE_NUMBER_ID'] else '❌ No configurado'}")
    print(f"{'='*50}\n")
    
    return app
