from app import create_app, db
from app.models import Usuario, Persona, ServicioAfectado

app = create_app()

with app.app_context():
    # Eliminar todas las tablas
    print("🗑️  Eliminando tablas...")
    db.drop_all()
    print("✅ Tablas eliminadas")
    
    # Crear todas las tablas
    print("🔨 Creando tablas...")
    db.create_all()
    print("✅ Tablas creadas")
    
    # Crear usuarios iniciales
    print("👥 Creando usuarios...")
    
    admin = Usuario(username='admin', rol='gerente')
    admin.set_password('admin123')
    
    jefe = Usuario(username='jefe_ti', rol='jefe_ti')
    jefe.set_password('jefe123')
    
    tec = Usuario(username='tecnico', rol='tecnico')
    tec.set_password('tec123')
    
    db.session.add_all([admin, jefe, tec])
    db.session.commit()
    
    # ✅ CREAR SERVICIOS AFECTADOS PREDETERMINADOS
    print("🌐 Creando catálogo de servicios...")
    
    servicios = [
        ServicioAfectado(nombre='Correo Electrónico', descripcion='Servicio de correo institucional', icono='envelope', activo=True),
        ServicioAfectado(nombre='VPN', descripcion='Red Privada Virtual', icono='shield-alt', activo=True),
        ServicioAfectado(nombre='Internet', descripcion='Conectividad a Internet', icono='globe', activo=True),
        ServicioAfectado(nombre='Impresión', descripcion='Servicios de impresión', icono='print', activo=True),
        ServicioAfectado(nombre='Telefonía IP', descripcion='Sistema telefónico VoIP', icono='phone', activo=True),
        ServicioAfectado(nombre='Intranet', descripcion='Portal interno institucional', icono='building', activo=True),
        ServicioAfectado(nombre='Sistema de Gestión', descripcion='ERP/CRM Institucional', icono='tasks', activo=True),
        ServicioAfectado(nombre='Base de Datos', descripcion='Servidores de bases de datos', icono='database', activo=True),
        ServicioAfectado(nombre='Backup', descripcion='Sistema de respaldos', icono='save', activo=True),
        ServicioAfectado(nombre='Active Directory', descripcion='Autenticación y directorio', icono='users-cog', activo=True),
    ]
    
    db.session.add_all(servicios)
    db.session.commit()
    
    print("✅ Base de datos creada")
    print("✓ Usuarios creados: admin/admin123, jefe_ti/jefe123, tecnico/tec123")
    print(f"✓ {len(servicios)} servicios afectados registrados")