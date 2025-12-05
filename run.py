import os
from app import create_app, db
from app.models import (
    Usuario, Item, SLA, Metrica, Alerta, Aprobacion, 
    Version, Persona, Incidencia, AlertaIncidencia, ServicioAfectado
)
from dotenv import load_dotenv

# Cargar variables de entorno solo en desarrollo
if os.getenv('FLASK_ENV') != 'production':
    load_dotenv()

# Crear aplicación según entorno
app = create_app(os.getenv('FLASK_ENV', 'production'))

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'Usuario': Usuario,
        'Item': Item,
        'SLA': SLA,
        'Metrica': Metrica,
        'Alerta': Alerta,
        'Aprobacion': Aprobacion,
        'Version': Version,
        'Persona': Persona,
        'Incidencia': Incidencia,
        'AlertaIncidencia': AlertaIncidencia,
        'ServicioAfectado': ServicioAfectado
    }

if __name__ == '__main__':
    # Configuración para desarrollo local
    if os.getenv('FLASK_ENV') == 'development':
        app.run(
            debug=True,
            host='127.0.0.1',
            port=5000,
            threaded=True
        )
    else:
        # Producción usa gunicorn (desde Procfile)
        port = int(os.getenv('PORT', 5000))
        app.run(host='0.0.0.0', port=port)