from app import create_app, db
from app.models import Usuario, Persona, ServicioAfectado

app = create_app()

with app.app_context():
    # IMPORTANTE: No usar drop_all() en producción
    # Solo crear tablas si no existen
    print("🔨 Creando tablas si no existen...")
    db.create_all()
    print("✅ Tablas verificadas/creadas")
    
    # Verificar si ya existen usuarios
    existing_users = Usuario.query.count()
    if existing_users == 0:
        print("👥 Creando usuarios iniciales...")
        
        admin = Usuario(username='admin', rol='gerente')
        admin.set_password('admin123')
        
        jefe = Usuario(username='jefe_ti', rol='jefe_ti')
        jefe.set_password('jefe123')
        
        tec = Usuario(username='tecnico', rol='tecnico')
        tec.set_password('tec123')
        
        db.session.add_all([admin, jefe, tec])
        db.session.commit()
        print("✅ Usuarios creados: admin/admin123, jefe_ti/jefe123, tecnico/tec123")
    else:
        print(f"ℹ️  Ya existen {existing_users} usuarios, omitiendo creación")
    
    # Verificar servicios afectados
    existing_services = ServicioAfectado.query.count()
    if existing_services == 0:
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
        print(f"✅ {len(servicios)} servicios afectados creados")
    else:
        print(f"ℹ️  Ya existen {existing_services} servicios, omitiendo creación")
    
    print("✅ Inicialización de base de datos completada")