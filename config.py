import os
import warnings
from datetime import timedelta

class Config:
    """Configuración base"""
    
    # ========================================
    # GENERAL
    # ========================================
    SECRET_KEY = os.getenv('SECRET_KEY', 'clave-secreta-desarrollo-2025-CAMBIAR-EN-PRODUCCION')
    
    # ========================================
    # BASE DE DATOS
    # ========================================
    # Render proporciona DATABASE_URL automáticamente para PostgreSQL
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Fix para Render: postgres:// -> postgresql://
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # Usar PostgreSQL en producción, SQLite en desarrollo
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///portafolio.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Pool de conexiones para PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20
    }
    
    # ========================================
    # SESIÓN
    # ========================================
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE = True  # HTTPS en producción
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # ========================================
    # EMAIL (Gmail)
    # ========================================
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    
    # Sender con validación
    _mail_user = os.getenv('MAIL_USERNAME')
    MAIL_DEFAULT_SENDER = (
        'INVENTECH - Fiscalía La Libertad', 
        _mail_user if _mail_user else 'noreply@inventech.gob.pe'
    )
    
    MAIL_MAX_EMAILS = None
    MAIL_ASCII_ATTACHMENTS = False
    
    # ========================================
    # WHATSAPP BUSINESS API
    # ========================================
    WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
    WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN', 'inventech_webhook_2024_secure')
    
    # ========================================
    # UPLOADS Y ARCHIVOS
    # ========================================
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}
    
    # ========================================
    # SCHEDULER (APScheduler)
    # ========================================
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = 'America/Lima'
    
    # ========================================
    # VALIDACIÓN
    # ========================================
    @classmethod
    def validate_email_config(cls):
        """Valida configuración de email"""
        if not cls.MAIL_USERNAME or not cls.MAIL_PASSWORD:
            warnings.warn(
                '\n'
                '⚠️  ADVERTENCIA: Configuración de email incompleta\n'
                '   Las notificaciones NO funcionarán.\n'
                '   Configure en Render:\n'
                '   - MAIL_USERNAME=tu_correo@gmail.com\n'
                '   - MAIL_PASSWORD=tu_app_password\n',
                RuntimeWarning,
                stacklevel=2
            )
            return False
        return True
    
    @classmethod
    def validate_whatsapp_config(cls):
        """Valida configuración de WhatsApp"""
        if not cls.WHATSAPP_PHONE_NUMBER_ID or not cls.WHATSAPP_ACCESS_TOKEN:
            warnings.warn(
                '\n'
                '⚠️  ADVERTENCIA: WhatsApp Business no configurado\n'
                '   Configure en Render:\n'
                '   - WHATSAPP_PHONE_NUMBER_ID=123456789\n'
                '   - WHATSAPP_ACCESS_TOKEN=EAAG...\n',
                RuntimeWarning,
                stacklevel=2
            )
            return False
        return True


class DevelopmentConfig(Config):
    """Desarrollo"""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False  # HTTP en desarrollo


class ProductionConfig(Config):
    """Producción"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # Solo HTTPS


# Exportar configuración según entorno
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}