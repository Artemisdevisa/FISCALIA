# Imports de Flask
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from flask import current_app
from app.email_service import enviar_notificacion_incidencia, enviar_notificacion_alerta_critica 

# Imports de modelos
from app.models import (
    Usuario, Item, SLA, Metrica, Alerta, 
    Aprobacion, Persona, Version, Incidencia, AlertaIncidencia
)

# Imports de la app
from app import db

# Imports de SQLAlchemy
from sqlalchemy import func

# Imports estándar de Python
import os
from datetime import datetime
from functools import wraps

# ✅ Import del servicio de scheduler
from app.scheduler_service import generar_metricas_automaticas_mes_anterior



# ← AGREGAR ESTA FUNCIÓN
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

def jefe_o_gerente_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') not in ['jefe_ti', 'gerente']:
            return {'success': False, 'error': 'No autorizado'}, 403
        return f(*args, **kwargs)
    return decorated_function

bp = Blueprint('main', __name__)


@bp.context_processor
def inject_alertas_activas():
    """Inyecta el número de alertas activas en todos los templates"""
    if 'user_id' in session:
        alertas_activas = Alerta.query.filter_by(estado='activa').count()
        return {'alertas_activas': alertas_activas}
    return {'alertas_activas': 0}


@bp.route('/api/siguiente-codigo')
def siguiente_codigo():
    """API para obtener el siguiente código disponible (P01, P02... o S01, S02...)"""
    if 'user_id' not in session:
        return {'error': 'No autenticado'}, 401
    
    tipo = request.args.get('tipo', 'producto')  # 'producto' o 'servicio'
    
    # Obtener el último código usado de ese tipo
    prefijo = 'P' if tipo == 'producto' else 'S'
    
    ultimo_item = Item.query.filter(
        Item.codigo.like(f'{prefijo}%')
    ).order_by(Item.codigo.desc()).first()
    
    if ultimo_item:
        # Extraer el número del código (ej: P05 -> 05)
        ultimo_numero = int(ultimo_item.codigo[1:])
        siguiente_numero = ultimo_numero + 1
    else:
        # Primer código
        siguiente_numero = 1
    
    # Formatear código (ej: P01, S03)
    codigo_generado = f'{prefijo}{siguiente_numero:02d}'
    
    return {
        'success': True,
        'codigo': codigo_generado,
        'tipo': tipo
    }

@bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    return render_template('index.html')

# ====================================
# GESTIÓN DE USUARIOS Y PERSONAS
# ====================================

@bp.route('/usuarios')
def usuarios_lista():
    """Lista de todos los usuarios registrados"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Solo Jefe TI y Gerente pueden ver usuarios
    if session.get('rol') not in ['jefe_ti', 'gerente']:
        flash('No tienes permisos para acceder a la gestión de usuarios', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtener todos los usuarios con sus personas
    usuarios = Usuario.query.order_by(Usuario.id.desc()).all()
    
    # Estadísticas
    total_usuarios = Usuario.query.count()
    total_tecnicos = Usuario.query.filter_by(rol='tecnico').count()
    total_jefes = Usuario.query.filter_by(rol='jefe_ti').count()
    total_gerentes = Usuario.query.filter_by(rol='gerente').count()
    
    return render_template('usuarios_lista.html',
                         usuarios=usuarios,
                         total_usuarios=total_usuarios,
                         total_tecnicos=total_tecnicos,
                         total_jefes=total_jefes,
                         total_gerentes=total_gerentes)


@bp.route('/usuarios/registrar', methods=['GET', 'POST'])
def usuarios_registrar():
    """Registrar nuevo usuario con su información personal"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Solo Jefe TI y Gerente pueden registrar usuarios
    if session.get('rol') not in ['jefe_ti', 'gerente']:
        flash('No tienes permisos para registrar usuarios', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        # Datos de usuario
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        rol = request.form.get('rol')
        
        # Datos personales
        nombres = request.form.get('nombres')
        apellidos = request.form.get('apellidos')
        telefono = request.form.get('telefono')
        correo = request.form.get('correo')
        
        # Validaciones
        if not username or not password or not rol or not nombres or not apellidos:
            flash('Todos los campos obligatorios deben ser completados', 'warning')
            return redirect(url_for('main.usuarios_registrar'))
        
        if password != password_confirm:
            flash('Las contraseñas no coinciden', 'warning')
            return redirect(url_for('main.usuarios_registrar'))
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'warning')
            return redirect(url_for('main.usuarios_registrar'))
        
        # Verificar si el username ya existe
        existe_usuario = Usuario.query.filter_by(username=username).first()
        if existe_usuario:
            flash(f'El nombre de usuario "{username}" ya está registrado', 'warning')
            return redirect(url_for('main.usuarios_registrar'))
        
        # Verificar si el correo ya existe
        if correo:
            from app.models import Persona
            existe_correo = Persona.query.filter_by(correo=correo).first()
            if existe_correo:
                flash(f'El correo "{correo}" ya está registrado', 'warning')
                return redirect(url_for('main.usuarios_registrar'))
        
        try:
            # Crear usuario
            nuevo_usuario = Usuario(
                username=username,
                rol=rol
            )
            nuevo_usuario.set_password(password)
            
            db.session.add(nuevo_usuario)
            db.session.flush()  # Para obtener el ID
            
            # Crear persona
            from app.models import Persona
            nueva_persona = Persona(
                usuario_id=nuevo_usuario.id,
                nombres=nombres,
                apellidos=apellidos,
                telefono=telefono,
                correo=correo
            )
            
            db.session.add(nueva_persona)
            db.session.commit()
            
            flash(f'Usuario "{username}" registrado exitosamente como {rol}', 'success')
            return redirect(url_for('main.usuarios_lista'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar usuario: {str(e)}', 'danger')
            return redirect(url_for('main.usuarios_registrar'))
    
    # GET - Mostrar formulario
    return render_template('usuarios_registrar.html')


@bp.route('/usuarios/<int:id>')
def usuario_detalle(id):
    """Ver detalle de un usuario"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Solo Jefe TI y Gerente pueden ver detalles
    if session.get('rol') not in ['jefe_ti', 'gerente']:
        flash('No tienes permisos para ver esta información', 'danger')
        return redirect(url_for('main.dashboard'))
    
    usuario = Usuario.query.get_or_404(id)
    
    # Contar items creados por este usuario
    items_creados = Item.query.filter_by(creado_por=id).count()
    
    # Contar versiones creadas por este usuario
    versiones_creadas = Version.query.filter_by(usuario_id=id).count()
    
    # Contar aprobaciones (si es gerente)
    aprobaciones_realizadas = 0
    if usuario.rol == 'gerente':
        aprobaciones_realizadas = Aprobacion.query.filter_by(aprobador_id=id).count()
    
    return render_template('usuario_detalle.html',
                         usuario=usuario,
                         items_creados=items_creados,
                         versiones_creadas=versiones_creadas,
                         aprobaciones_realizadas=aprobaciones_realizadas)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Usuario.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['rol'] = user.rol
            return redirect(url_for('main.dashboard'))
        else:
            return render_template('login.html', error='Usuario o contraseña incorrectos')
    
    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))

@bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Estadísticas generales
    total_productos = Item.query.filter_by(tipo='producto', estado='aprobado').count()
    total_servicios = Item.query.filter_by(tipo='servicio', estado='aprobado').count()
    total_slas = SLA.query.count()
    
    # ✅ CORRECCIÓN: Items activos = aprobados + operativos
    items_activos = Item.query.filter_by(
        estado='aprobado',
        estado_operativo='activo'
    ).count()
    
    # Items pendientes de aprobación (solo para Gerente)
    items_pendientes = Aprobacion.query.filter_by(estado='pendiente').count()
    
    # Alertas activas
    alertas_lista = Alerta.query.filter_by(estado='activa').order_by(Alerta.fecha_creacion.desc()).limit(5).all()
    
    # ✅ CORRECCIÓN: Últimas métricas con JOIN correcto
    metricas_recientes = db.session.query(
        Item.id,
        Item.nombre,
        Item.tipo,
        Metrica.semaforo,
        Metrica.porcentaje_cumplimiento,
        Metrica.mes,
        Metrica.anio
    ).join(Metrica, Item.id == Metrica.item_id).filter(
        Item.estado == 'aprobado'
    ).order_by(Metrica.fecha_registro.desc()).limit(6).all()
    
    # Cumplimiento promedio de SLAs
    cumplimiento_promedio = db.session.query(
        func.avg(Metrica.porcentaje_cumplimiento)
    ).filter(Metrica.porcentaje_cumplimiento.isnot(None)).scalar() or 0
    
    return render_template('dashboard.html',
                         total_productos=total_productos,
                         total_servicios=total_servicios,
                         total_slas=total_slas,
                         items_activos=items_activos,
                         items_pendientes=items_pendientes,
                         alertas_lista=alertas_lista,
                         metricas_recientes=metricas_recientes,
                         cumplimiento_promedio=round(cumplimiento_promedio, 1))
@bp.route('/productos')
def productos():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Obtener filtros de búsqueda
    buscar = request.args.get('buscar', '')
    estado = request.args.get('estado', '')
    
    # Query base
    query = Item.query.filter_by(tipo='producto')
    
    # Aplicar filtros
    if buscar:
        query = query.filter(
            (Item.nombre.contains(buscar)) | 
            (Item.codigo.contains(buscar)) |
            (Item.categoria.contains(buscar))
        )
    
    if estado:
        query = query.filter_by(estado=estado)
    
    # Obtener productos
    productos = query.order_by(Item.fecha_creacion.desc()).all()
    
    # Estadísticas
    total_productos = Item.query.filter_by(tipo='producto').count()
    productos_activos = Item.query.filter_by(tipo='producto', estado='activo').count()
    productos_propuestos = Item.query.filter_by(tipo='producto', estado='propuesto').count()
    
    return render_template('productos_lista.html',
                         productos=productos,
                         total_productos=total_productos,
                         productos_activos=productos_activos,
                         productos_propuestos=productos_propuestos,
                         buscar=buscar,
                         estado=estado)

@bp.route('/producto/<int:id>')
def producto_detalle(id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    producto = Item.query.get_or_404(id)
    
    # Verificar que sea un producto
    if producto.tipo != 'producto':
        flash('El item solicitado no es un producto', 'warning')
        return redirect(url_for('main.productos'))
    
    # Obtener SLA si existe
    sla = SLA.query.filter_by(item_id=id).first()
    
    # Obtener últimas 3 versiones
    versiones = Version.query.filter_by(item_id=id).order_by(Version.fecha.desc()).limit(3).all()
    
    # Obtener métricas del último mes
    from datetime import datetime
    mes_actual = datetime.now().month
    anio_actual = datetime.now().year
    metrica_actual = Metrica.query.filter_by(
        item_id=id, 
        mes=mes_actual, 
        anio=anio_actual
    ).first()
    
    # ✅ La relación reemplazado_por ya está disponible automáticamente por SQLAlchemy
    # No necesitamos hacer query adicional, solo pasarlo al template
    
    return render_template('producto_detalle.html',
                         producto=producto,
                         sla=sla,
                         versiones=versiones,
                         metrica_actual=metrica_actual)


# Agregar al final del archivo routes.py

@bp.route('/servicios')
def servicios():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Obtener filtros de búsqueda
    buscar = request.args.get('buscar', '')
    estado = request.args.get('estado', '')
    
    # Query base
    query = Item.query.filter_by(tipo='servicio')
    
    # Aplicar filtros
    if buscar:
        query = query.filter(
            (Item.nombre.contains(buscar)) | 
            (Item.codigo.contains(buscar)) |
            (Item.categoria.contains(buscar))
        )
    
    if estado:
        query = query.filter_by(estado=estado)
    
    # Obtener servicios
    servicios = query.order_by(Item.fecha_creacion.desc()).all()
    
    # Estadísticas
    total_servicios = Item.query.filter_by(tipo='servicio').count()
    servicios_activos = Item.query.filter_by(tipo='servicio', estado='activo').count()
    servicios_propuestos = Item.query.filter_by(tipo='servicio', estado='propuesto').count()
    
    return render_template('servicios_lista.html',
                         servicios=servicios,
                         total_servicios=total_servicios,
                         servicios_activos=servicios_activos,
                         servicios_propuestos=servicios_propuestos,
                         buscar=buscar,
                         estado=estado)

@bp.route('/servicio/<int:id>')
def servicio_detalle(id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    servicio = Item.query.get_or_404(id)
    
    # Verificar que sea un servicio
    if servicio.tipo != 'servicio':
        flash('El item solicitado no es un servicio', 'warning')
        return redirect(url_for('main.servicios'))
    
    # Obtener SLA si existe
    sla = SLA.query.filter_by(item_id=id).first()
    
    # Obtener últimas 3 versiones
    from app.models import Version
    versiones = Version.query.filter_by(item_id=id).order_by(Version.fecha.desc()).limit(3).all()
    
    # Obtener métricas del último mes
    from datetime import datetime
    mes_actual = datetime.now().month
    anio_actual = datetime.now().year
    metrica_actual = Metrica.query.filter_by(
        item_id=id, 
        mes=mes_actual, 
        anio=anio_actual
    ).first()
    
    return render_template('servicio_detalle.html',
                         servicio=servicio,
                         sla=sla,
                         versiones=versiones,
                         metrica_actual=metrica_actual)

@bp.route('/item/crear', methods=['GET', 'POST'])
def item_crear():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    if session.get('rol') not in ['jefe_ti', 'gerente']:
        flash('No tienes permisos para crear items', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        # Datos básicos
        tipo = request.form.get('tipo')
        codigo = request.form.get('codigo')
        nombre = request.form.get('nombre')
        categoria = request.form.get('categoria')
        definicion = request.form.get('definicion')
        proposito = request.form.get('proposito')
        estado_actual = request.form.get('estado_actual')
        estado_objetivo = request.form.get('estado_objetivo')
        beneficio = request.form.get('beneficio')
        caso_uso = request.form.get('caso_uso')
        responsable = session.get('username')
        dependencias = request.form.get('dependencias')
        
        # ✅ CRÍTICO: Datos de reemplazo
        reemplaza_a_id = request.form.get('reemplaza_a_id')
        motivo_reemplazo = request.form.get('motivo_reemplazo')
        
        # ⚠️ CRÍTICO: Convertir a int o None
        if reemplaza_a_id and reemplaza_a_id.strip():
            reemplaza_a_id = int(reemplaza_a_id)
            print(f"✅ reemplaza_a_id recibido: {reemplaza_a_id}")
        else:
            reemplaza_a_id = None
            print("ℹ️ No se seleccionó item para reemplazar")
        
        # Validar código único
        existe = Item.query.filter_by(codigo=codigo).first()
        if existe:
            flash(f'⚠️ El código {codigo} ya existe. Recarga la página.', 'warning')
            return redirect(url_for('main.item_crear'))
        
        # Crear nuevo item
        nuevo_item = Item(
            codigo=codigo,
            nombre=nombre,
            tipo=tipo,
            categoria=categoria,
            definicion=definicion,
            proposito=proposito,
            estado_actual=estado_actual,
            estado_objetivo=estado_objetivo,
            beneficio=beneficio,
            caso_uso=caso_uso,
            responsable=responsable,
            dependencias=dependencias,
            estado='propuesto',           # ← Estado de aprobación
            estado_operativo='activo',     # ✅ NUEVO: Estado operativo activo por defecto
            creado_por=session.get('user_id'),
            # ⚠️ CRÍTICO: Asignar campos de reemplazo
            reemplaza_a_id=reemplaza_a_id,
            motivo_reemplazo=motivo_reemplazo if reemplaza_a_id else None,
            fecha_reemplazo=datetime.utcnow() if reemplaza_a_id else None
        )
        
        print(f"📝 Creando item con reemplaza_a_id={nuevo_item.reemplaza_a_id}")
        
        db.session.add(nuevo_item)
        db.session.flush()
        
        # Crear versión inicial
        razon_version = f'Registro inicial del {tipo} por {session.get("username")}'
        if reemplaza_a_id:
            item_anterior = Item.query.get(reemplaza_a_id)
            razon_version += f' - Reemplaza a {item_anterior.codigo}: {motivo_reemplazo}'
        
        version = Version(
            item_id=nuevo_item.id,
            numero_version=1,
            campo_modificado='Creación inicial',
            valor_anterior='',
            valor_nuevo='Item creado',
            razon_cambio=razon_version,
            usuario_id=session.get('user_id')
        )
        db.session.add(version)
        
        # ✅ OPCIONAL: Marcar item anterior como "reemplazado"
        if reemplaza_a_id:
            item_anterior = Item.query.get(reemplaza_a_id)
            # Puedes agregar un campo "estado_operativo" o similar
            # item_anterior.estado_operativo = 'reemplazado'
            
            # Crear alerta informativa
            alerta = Alerta(
                item_id=reemplaza_a_id,
                tipo='reemplazo',
                mensaje=f'Este item ha sido reemplazado por {nuevo_item.codigo} - {nuevo_item.nombre}',
                estado='activa'
            )
            db.session.add(alerta)
        
        # Aprobación
        if session.get('rol') == 'jefe_ti':
            gerente = Usuario.query.filter_by(rol='gerente').first()
            if gerente:
                aprobacion = Aprobacion(
                    item_id=nuevo_item.id,
                    aprobador_id=gerente.id,
                    estado='pendiente'
                )
                db.session.add(aprobacion)
                
                mensaje = f'✅ {tipo.capitalize()} "{nombre}" creado exitosamente.'
                if reemplaza_a_id:
                    mensaje += f' Reemplaza a {item_anterior.codigo}.'
                mensaje += ' Pendiente de aprobación del Gerente.'
                flash(mensaje, 'success')
        else:
            nuevo_item.estado = 'aprobado'
            mensaje = f'✅ {tipo.capitalize()} "{nombre}" creado y aprobado.'
            if reemplaza_a_id:
                mensaje += f' Reemplaza a {item_anterior.codigo}.'
            flash(mensaje, 'success')
        
        db.session.commit()
        
        if tipo == 'producto':
            return redirect(url_for('main.producto_detalle', id=nuevo_item.id))
        else:
            return redirect(url_for('main.servicio_detalle', id=nuevo_item.id))
    
    # GET - Obtener items disponibles para reemplazar
    items_disponibles = Item.query.filter_by(estado='activo').order_by(Item.tipo, Item.codigo).all()
    
    return render_template('item_crear.html', items_disponibles=items_disponibles)


@bp.route('/item/<int:id>/reemplazos')
def item_reemplazos(id):
    """Ver cadena de reemplazos de un item"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    item = Item.query.get_or_404(id)
    
    # Cadena hacia atrás (items que reemplazó)
    cadena_anterior = []
    item_temp = item
    while item_temp.reemplaza_a:
        cadena_anterior.append(item_temp.reemplaza_a)
        item_temp = item_temp.reemplaza_a
    
    # Item que reemplaza al actual (si existe)
    reemplazado_por = item.reemplazado_por
    
    return render_template('item_reemplazos.html',
                         item=item,
                         cadena_anterior=cadena_anterior,
                         reemplazado_por=reemplazado_por)


# En routes.py
@bp.route('/api/items-activos')
def items_activos():
    """API para obtener SOLO items APROBADOS y NO REEMPLAZADOS disponibles para reemplazo"""
    if 'user_id' not in session:
        return {'error': 'No autenticado'}, 401
    
    # ✅ CORRECCIÓN: Solo items APROBADOS que NO han sido reemplazados
    # Subconsulta: obtener IDs de items que ya fueron reemplazados
    items_reemplazados = db.session.query(Item.reemplaza_a_id).filter(
        Item.reemplaza_a_id.isnot(None)
    ).subquery()
    
    # Query principal: items aprobados que NO están en la lista de reemplazados
    items = Item.query.filter(
        Item.estado == 'aprobado',
        ~Item.id.in_(items_reemplazados)
    ).order_by(Item.tipo, Item.codigo).all()
    
    # Serializar
    items_json = []
    for item in items:
        items_json.append({
            'id': item.id,
            'codigo': item.codigo,
            'nombre': item.nombre,
            'tipo': item.tipo,
            'categoria': item.categoria,
            'estado': item.estado,
            'responsable': item.responsable,
            'fecha_creacion': item.fecha_creacion.strftime('%d/%m/%Y')
        })
    
    return {
        'success': True,
        'items': items_json,
        'total': len(items_json)
    }


# ====================================
# AGREGAR AL routes.py
# ====================================

@bp.route('/producto/<int:id>/editar', methods=['GET', 'POST'])
def producto_editar(id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    if session.get('rol') not in ['jefe_ti', 'gerente']:
        flash('No tienes permisos para editar productos', 'danger')
        return redirect(url_for('main.dashboard'))
    
    producto = Item.query.get_or_404(id)
    
    if producto.tipo != 'producto':
        flash('El item no es un producto', 'warning')
        return redirect(url_for('main.productos'))
    
    if request.method == 'POST':
        # Obtener valores actuales (antes de modificar)
        valores_anteriores = {
            'nombre': producto.nombre,
            'categoria': producto.categoria,
            'definicion': producto.definicion,
            'proposito': producto.proposito,
            'estado_actual': producto.estado_actual,
            'estado_objetivo': producto.estado_objetivo,
            'beneficio': producto.beneficio,
            'caso_uso': producto.caso_uso,
            'dependencias': producto.dependencias,
            'estado_operativo': producto.estado_operativo  # ✅ NUEVO
        }
        
        # Obtener nuevos valores del formulario
        nuevos_valores = {
            'nombre': request.form.get('nombre'),
            'categoria': request.form.get('categoria'),
            'definicion': request.form.get('definicion'),
            'proposito': request.form.get('proposito'),
            'estado_actual': request.form.get('estado_actual'),
            'estado_objetivo': request.form.get('estado_objetivo'),
            'beneficio': request.form.get('beneficio'),
            'caso_uso': request.form.get('caso_uso'),
            'dependencias': request.form.get('dependencias'),
            'estado_operativo': request.form.get('estado_operativo')  # ✅ NUEVO
        }
        
        # Detectar qué campos cambiaron
        campos_modificados = []
        for campo, valor_nuevo in nuevos_valores.items():
            valor_anterior = valores_anteriores[campo]
            if valor_nuevo != valor_anterior:
                campos_modificados.append({
                    'campo': campo,
                    'anterior': valor_anterior or '',
                    'nuevo': valor_nuevo or ''
                })
        
        # Si hay cambios, actualizar y crear versiones
        if campos_modificados:
            # Actualizar producto
            producto.nombre = nuevos_valores['nombre']
            producto.categoria = nuevos_valores['categoria']
            producto.definicion = nuevos_valores['definicion']
            producto.proposito = nuevos_valores['proposito']
            producto.estado_actual = nuevos_valores['estado_actual']
            producto.estado_objetivo = nuevos_valores['estado_objetivo']
            producto.beneficio = nuevos_valores['beneficio']
            producto.caso_uso = nuevos_valores['caso_uso']
            producto.dependencias = nuevos_valores['dependencias']
            producto.estado_operativo = nuevos_valores['estado_operativo']  # ✅ NUEVO
            
            # Obtener número de versión
            ultima_version = Version.query.filter_by(item_id=id).order_by(Version.numero_version.desc()).first()
            numero_version_base = (ultima_version.numero_version + 1) if ultima_version else 1
            
            # Crear una versión por cada campo modificado
            razon_general = request.form.get('razon_cambio', 'Actualización de información')
            
            for i, cambio in enumerate(campos_modificados):
                # Traducir nombre del campo a español
                nombres_campos = {
                    'nombre': 'Nombre',
                    'categoria': 'Categoría',
                    'definicion': 'Definición',
                    'proposito': 'Propósito',
                    'estado_actual': 'Estado Actual',
                    'estado_objetivo': 'Estado Objetivo',
                    'beneficio': 'Beneficio Esperado',
                    'caso_uso': 'Caso de Uso',
                    'dependencias': 'Dependencias',
                    'estado_operativo': 'Estado Operativo'  # ✅ NUEVO
                }
                
                campo_nombre = nombres_campos.get(cambio['campo'], cambio['campo'])
                
                version = Version(
                    item_id=id,
                    numero_version=numero_version_base + i,
                    campo_modificado=campo_nombre,
                    valor_anterior=cambio['anterior'][:500],
                    valor_nuevo=cambio['nuevo'][:500],
                    razon_cambio=razon_general,
                    usuario_id=session.get('user_id')
                )
                db.session.add(version)
            
            db.session.commit()
            flash(f'Producto actualizado exitosamente. {len(campos_modificados)} campo(s) modificado(s).', 'success')
        else:
            flash('No se detectaron cambios en el producto', 'info')
        
        return redirect(url_for('main.producto_detalle', id=id))
    
    return render_template('producto_editar.html', producto=producto)


@bp.route('/servicio/<int:id>/editar', methods=['GET', 'POST'])
def servicio_editar(id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    if session.get('rol') not in ['jefe_ti', 'gerente']:
        flash('No tienes permisos para editar servicios', 'danger')
        return redirect(url_for('main.dashboard'))
    
    servicio = Item.query.get_or_404(id)
    
    if servicio.tipo != 'servicio':
        flash('El item no es un servicio', 'warning')
        return redirect(url_for('main.servicios'))
    
    if request.method == 'POST':
        # Obtener valores actuales (antes de modificar)
        valores_anteriores = {
            'nombre': servicio.nombre,
            'categoria': servicio.categoria,
            'definicion': servicio.definicion,
            'proposito': servicio.proposito,
            'estado_actual': servicio.estado_actual,
            'estado_objetivo': servicio.estado_objetivo,
            'beneficio': servicio.beneficio,
            'caso_uso': servicio.caso_uso,
            'dependencias': servicio.dependencias,
            'estado_operativo': servicio.estado_operativo  # ✅ NUEVO
        }
        
        # Obtener nuevos valores del formulario
        nuevos_valores = {
            'nombre': request.form.get('nombre'),
            'categoria': request.form.get('categoria'),
            'definicion': request.form.get('definicion'),
            'proposito': request.form.get('proposito'),
            'estado_actual': request.form.get('estado_actual'),
            'estado_objetivo': request.form.get('estado_objetivo'),
            'beneficio': request.form.get('beneficio'),
            'caso_uso': request.form.get('caso_uso'),
            'dependencias': request.form.get('dependencias'),
            'estado_operativo': request.form.get('estado_operativo')  # ✅ NUEVO
        }
        
        # Detectar qué campos cambiaron
        campos_modificados = []
        for campo, valor_nuevo in nuevos_valores.items():
            valor_anterior = valores_anteriores[campo]
            if valor_nuevo != valor_anterior:
                campos_modificados.append({
                    'campo': campo,
                    'anterior': valor_anterior or '',
                    'nuevo': valor_nuevo or ''
                })
        
        # Si hay cambios, actualizar y crear versiones
        if campos_modificados:
            # Actualizar servicio
            servicio.nombre = nuevos_valores['nombre']
            servicio.categoria = nuevos_valores['categoria']
            servicio.definicion = nuevos_valores['definicion']
            servicio.proposito = nuevos_valores['proposito']
            servicio.estado_actual = nuevos_valores['estado_actual']
            servicio.estado_objetivo = nuevos_valores['estado_objetivo']
            servicio.beneficio = nuevos_valores['beneficio']
            servicio.caso_uso = nuevos_valores['caso_uso']
            servicio.dependencias = nuevos_valores['dependencias']
            servicio.estado_operativo = nuevos_valores['estado_operativo']  # ✅ NUEVO
            
            # Obtener número de versión
            ultima_version = Version.query.filter_by(item_id=id).order_by(Version.numero_version.desc()).first()
            numero_version_base = (ultima_version.numero_version + 1) if ultima_version else 1
            
            # Crear una versión por cada campo modificado
            razon_general = request.form.get('razon_cambio', 'Actualización de información')
            
            for i, cambio in enumerate(campos_modificados):
                # Traducir nombre del campo a español
                nombres_campos = {
                    'nombre': 'Nombre',
                    'categoria': 'Categoría',
                    'definicion': 'Definición',
                    'proposito': 'Propósito',
                    'estado_actual': 'Estado Actual',
                    'estado_objetivo': 'Estado Objetivo',
                    'beneficio': 'Beneficio Esperado',
                    'caso_uso': 'Caso de Uso',
                    'dependencias': 'Dependencias',
                    'estado_operativo': 'Estado Operativo'  # ✅ NUEVO
                }
                
                campo_nombre = nombres_campos.get(cambio['campo'], cambio['campo'])
                
                version = Version(
                    item_id=id,
                    numero_version=numero_version_base + i,
                    campo_modificado=campo_nombre,
                    valor_anterior=cambio['anterior'][:500],
                    valor_nuevo=cambio['nuevo'][:500],
                    razon_cambio=razon_general,
                    usuario_id=session.get('user_id')
                )
                db.session.add(version)
            
            db.session.commit()
            flash(f'Servicio actualizado exitosamente. {len(campos_modificados)} campo(s) modificado(s).', 'success')
        else:
            flash('No se detectaron cambios en el servicio', 'info')
        
        return redirect(url_for('main.servicio_detalle', id=id))
    
    return render_template('servicio_editar.html', servicio=servicio)


def generar_alerta_automatica(item_id, metrica_actual):
    """
    Sistema de alertas multinivel basado en historial de métricas
    ✅ MODIFICADO: Envía notificaciones cuando se generan alertas
    """
    from datetime import datetime, timedelta
    from sqlalchemy import and_
    
    item = Item.query.get(item_id)
    if not item:
        return
    
    # Obtener métricas de los últimos 3 meses
    fecha_limite = datetime.utcnow() - timedelta(days=90)
    metricas_historicas = Metrica.query.filter(
        and_(
            Metrica.item_id == item_id,
            Metrica.fecha_registro >= fecha_limite
        )
    ).order_by(Metrica.fecha_registro.desc()).limit(3).all()
    
    if not metricas_historicas:
        return
    
    alerta_generada = None
    
    # NIVEL 1: ALERTA INMEDIATA - ROJO PRIMERA VEZ
    if metrica_actual.semaforo == 'rojo':
        es_primer_rojo = True
        for m in metricas_historicas[1:]:
            if m.semaforo == 'rojo':
                es_primer_rojo = False
                break
        
        if es_primer_rojo:
            alerta = Alerta(
                item_id=item_id,
                tipo='rojo_inmediato',
                nivel_urgencia='critica',
                mensaje=f'🔴 CRÍTICO: {item.codigo} - {item.nombre} ha caído en estado ROJO. '
                        f'Incidencias: {metrica_actual.incidencias}. Cumplimiento: {metrica_actual.porcentaje_cumplimiento}%. '
                        f'Se requiere revisión inmediata y plan de acción correctiva.',
                estado='activa'
            )
            db.session.add(alerta)
            alerta_generada = alerta
    
    # NIVEL 2: AMARILLO PERSISTENTE
    if metrica_actual.semaforo == 'amarillo':
        if len(metricas_historicas) >= 2:
            metrica_anterior = metricas_historicas[1]
            if metrica_anterior.semaforo == 'amarillo':
                alerta = Alerta(
                    item_id=item_id,
                    tipo='amarillo_recurrente',
                    nivel_urgencia='media',
                    mensaje=f'⚠️ PREVENTIVO: {item.codigo} - {item.nombre} permanece en estado AMARILLO. '
                            f'Incidencias acumuladas: {metrica_actual.incidencias}. '
                            f'Se recomienda mantenimiento preventivo antes de que escale a crítico.',
                    estado='activa'
                )
                db.session.add(alerta)
                if not alerta_generada:
                    alerta_generada = alerta
    
    # NIVEL 3: ROJO SEGUNDO MES CONSECUTIVO
    if len(metricas_historicas) >= 2:
        if metrica_actual.semaforo == 'rojo' and metricas_historicas[1].semaforo == 'rojo':
            alerta = Alerta(
                item_id=item_id,
                tipo='rojo_mes2',
                nivel_urgencia='alta',
                mensaje=f'🔴 ESCALAMIENTO: {item.codigo} - {item.nombre} lleva 2 meses consecutivos en ROJO. '
                        f'Las acciones correctivas no han sido efectivas. '
                        f'Se requiere aprobación de reemplazo inmediato. '
                        f'Cumplimiento promedio: {(metrica_actual.porcentaje_cumplimiento + metricas_historicas[1].porcentaje_cumplimiento) // 2}%.',
                estado='activa'
            )
            db.session.add(alerta)
            if not alerta_generada:
                alerta_generada = alerta
    
    # NIVEL 4: ROJO TERCER MES CONSECUTIVO
    if len(metricas_historicas) >= 3:
        if (metrica_actual.semaforo == 'rojo' and 
            metricas_historicas[1].semaforo == 'rojo' and 
            metricas_historicas[2].semaforo == 'rojo'):
            alerta = Alerta(
                item_id=item_id,
                tipo='rojo_mes3',
                nivel_urgencia='critica',
                mensaje=f'🔴🔴🔴 CRÍTICO MÁXIMO: {item.codigo} - {item.nombre} lleva 3 meses en ROJO. '
                        f'El equipo/servicio es INACEPTABLE para operación. '
                        f'REEMPLAZO OBLIGATORIO INMEDIATO. '
                        f'Este item está comprometiendo seriamente la operación del área.',
                estado='activa'
            )
            db.session.add(alerta)
            if not alerta_generada:
                alerta_generada = alerta
    
    # NIVEL 5: INCIDENCIAS MASIVAS EN UN MES
    if metrica_actual.incidencias >= 5:
        alerta = Alerta(
            item_id=item_id,
            tipo='incidencias_masivas',
            nivel_urgencia='critica',
            mensaje=f'🔴 CRÍTICO: {item.codigo} - {item.nombre} registró {metrica_actual.incidencias} incidencias en el mes. '
                    f'Volumen anormal de fallas indica deterioro acelerado. '
                    f'Requiere diagnóstico técnico urgente y evaluación de reemplazo.',
            estado='activa'
        )
        db.session.add(alerta)
        if not alerta_generada:
            alerta_generada = alerta
    
    try:
        db.session.commit()
        
        # ✅ ENVIAR NOTIFICACIONES SI SE GENERÓ ALERTA
        if alerta_generada:
            enviar_notificaciones_alerta_critica(alerta_generada)
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al generar alertas: {e}")

@bp.route('/sla/editar/<int:item_id>', methods=['GET', 'POST'])
def sla_editar(item_id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Solo Jefe TI y Gerente pueden editar
    if session.get('rol') not in ['jefe_ti', 'gerente']:
        flash('No tienes permisos para editar SLAs', 'danger')
        return redirect(url_for('main.dashboard'))
    
    item = Item.query.get_or_404(item_id)
    
    # ✅ VALIDACIÓN CRÍTICA: Verificar si el item ha sido reemplazado
    item_reemplazo = Item.query.filter_by(reemplaza_a_id=item_id).first()
    if item_reemplazo:
        flash(f'⚠️ No se puede editar el SLA de este {item.tipo} porque ha sido REEMPLAZADO por {item_reemplazo.codigo} - {item_reemplazo.nombre}. '
              f'El item está inactivo y ya no está en operación.', 'warning')
        
        if item.tipo == 'producto':
            return redirect(url_for('main.producto_detalle', id=item_id))
        else:
            return redirect(url_for('main.servicio_detalle', id=item_id))
    
    sla = SLA.query.filter_by(item_id=item_id).first()
    
    if request.method == 'POST':
        # Si no existe SLA, crear uno nuevo
        if not sla:
            sla = SLA(item_id=item_id)
            db.session.add(sla)
        
        # Guardar valores anteriores para versión
        valores_anteriores = {}
        
        if item.tipo == 'servicio':
            # SLA para servicios
            valores_anteriores['disponibilidad'] = sla.disponibilidad
            valores_anteriores['velocidad_min'] = sla.velocidad_min
            valores_anteriores['latencia_max'] = sla.latencia_max
            
            sla.disponibilidad = float(request.form.get('disponibilidad', 0))
            sla.velocidad_min = int(request.form.get('velocidad_min', 0)) if request.form.get('velocidad_min') else None
            sla.latencia_max = int(request.form.get('latencia_max', 0)) if request.form.get('latencia_max') else None
            sla.tiempo_respuesta = int(request.form.get('tiempo_respuesta', 0)) if request.form.get('tiempo_respuesta') else None
            sla.tiempo_resolucion = int(request.form.get('tiempo_resolucion', 0)) if request.form.get('tiempo_resolucion') else None
            sla.capacidad_usuarios = int(request.form.get('capacidad_usuarios', 0)) if request.form.get('capacidad_usuarios') else None
            sla.horario = request.form.get('horario')
            
        else:  # producto
            # Especificaciones técnicas para productos
            valores_anteriores['fallas_criticas_permitidas'] = sla.fallas_criticas_permitidas if sla else None
            valores_anteriores['fallas_menores_permitidas'] = sla.fallas_menores_permitidas if sla else None
            
            sla.fallas_criticas_permitidas = int(request.form.get('fallas_criticas_permitidas', 0))
            sla.fallas_menores_permitidas = int(request.form.get('fallas_menores_permitidas', 0))
            sla.disponibilidad_esperada = float(request.form.get('disponibilidad_esperada', 99.5)) if request.form.get('disponibilidad_esperada') else None
            sla.tiempo_max_inactividad = float(request.form.get('tiempo_max_inactividad', 3.6)) if request.form.get('tiempo_max_inactividad') else None
            sla.vida_util = int(request.form.get('vida_util', 0)) if request.form.get('vida_util') else None
            sla.mantenimiento_preventivo = request.form.get('mantenimiento_preventivo')
            sla.caracteristicas = request.form.get('caracteristicas')
        
        db.session.commit()
        
        # Crear versión del cambio
        ultima_version = Version.query.filter_by(item_id=item_id).order_by(Version.numero_version.desc()).first()
        numero_version = (ultima_version.numero_version + 1) if ultima_version else 1
        
        version = Version(
            item_id=item_id,
            numero_version=numero_version,
            campo_modificado='SLA/Especificaciones Técnicas',
            valor_anterior=str(valores_anteriores),
            valor_nuevo='Actualizado',
            razon_cambio=request.form.get('razon_cambio', 'Actualización de SLA'),
            usuario_id=session.get('user_id')
        )
        db.session.add(version)
        db.session.commit()
        
        flash('SLA actualizado exitosamente', 'success')
        
        if item.tipo == 'producto':
            return redirect(url_for('main.producto_detalle', id=item_id))
        else:
            return redirect(url_for('main.servicio_detalle', id=item_id))
    
    # GET - Mostrar formulario
    return render_template('sla_editar.html', item=item, sla=sla)


# Agregar al final del archivo routes.py

@bp.route('/aprobaciones')
def aprobaciones_pendientes():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Solo Gerente puede ver aprobaciones
    if session.get('rol') != 'gerente':
        flash('No tienes permisos para acceder a las aprobaciones', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtener filtros
    estado_filtro = request.args.get('estado', 'pendiente')
    tipo_filtro = request.args.get('tipo', '')
    
    # Query base - aprobaciones del gerente actual
    query = Aprobacion.query.filter_by(aprobador_id=session.get('user_id'))
    
    # Aplicar filtros
    if estado_filtro:
        query = query.filter_by(estado=estado_filtro)
    
    aprobaciones_raw = query.order_by(Aprobacion.fecha_solicitud.desc()).all()
    
    # CREAR LISTA CON ITEMS Y SOLICITANTES
    aprobaciones = []
    for apr in aprobaciones_raw:
        item = Item.query.get(apr.item_id)
        if item:
            # Aplicar filtro de tipo si existe
            if tipo_filtro and item.tipo != tipo_filtro:
                continue
                
            solicitante = Usuario.query.get(item.creado_por)
            aprobaciones.append({
                'aprobacion': apr,
                'item': item,
                'solicitante': solicitante
            })
    
    # Estadísticas
    total_pendientes = Aprobacion.query.filter_by(
        aprobador_id=session.get('user_id'),
        estado='pendiente'
    ).count()
    
    total_aprobadas = Aprobacion.query.filter_by(
        aprobador_id=session.get('user_id'),
        estado='aprobado'
    ).count()
    
    total_rechazadas = Aprobacion.query.filter_by(
        aprobador_id=session.get('user_id'),
        estado='rechazado'
    ).count()
    
    return render_template('aprobaciones_pendientes.html',
                         aprobaciones=aprobaciones,
                         total_pendientes=total_pendientes,
                         total_aprobadas=total_aprobadas,
                         total_rechazadas=total_rechazadas,
                         estado_filtro=estado_filtro,
                         tipo_filtro=tipo_filtro)


@bp.route('/aprobacion/<int:id>')
def aprobacion_detalle(id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Solo Gerente puede ver detalles de aprobación
    if session.get('rol') != 'gerente':
        flash('No tienes permisos para acceder a esta aprobación', 'danger')
        return redirect(url_for('main.dashboard'))
    
    aprobacion = Aprobacion.query.get_or_404(id)
    
    # Verificar que la aprobación sea del gerente actual
    if aprobacion.aprobador_id != session.get('user_id'):
        flash('No tienes permisos para ver esta aprobación', 'danger')
        return redirect(url_for('main.aprobaciones_pendientes'))
    
    # Obtener item relacionado
    item = Item.query.get_or_404(aprobacion.item_id)
    
    # Obtener SLA si existe
    sla = SLA.query.filter_by(item_id=item.id).first()
    
    # Obtener usuario creador
    creador = Usuario.query.get(item.creado_por)
    
    # Obtener versiones del item
    versiones = Version.query.filter_by(item_id=item.id).order_by(Version.fecha.desc()).limit(5).all()
    
    return render_template('aprobacion_detalle.html',
                         aprobacion=aprobacion,
                         item=item,
                         sla=sla,
                         creador=creador,
                         versiones=versiones)


@bp.route('/aprobacion/<int:id>/decidir', methods=['POST'])
def aprobacion_decidir(id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Solo Gerente puede decidir
    if session.get('rol') != 'gerente':
        return {'success': False, 'error': 'No autorizado'}, 403
    
    aprobacion = Aprobacion.query.get_or_404(id)
    
    # Verificar que la aprobación sea del gerente actual
    if aprobacion.aprobador_id != session.get('user_id'):
        return {'success': False, 'error': 'No autorizado'}, 403
    
    # Obtener decisión
    decision = request.json.get('decision')  # 'aprobar' o 'rechazar'
    comentarios = request.json.get('comentarios', '')
    
    if decision not in ['aprobar', 'rechazar']:
        return {'success': False, 'error': 'Decisión inválida'}, 400
    
    # Actualizar aprobación
    from datetime import datetime
    aprobacion.estado = 'aprobado' if decision == 'aprobar' else 'rechazado'
    aprobacion.comentarios = comentarios
    aprobacion.fecha_respuesta = datetime.utcnow()
    
    # Si se aprueba, cambiar estado del item
    if decision == 'aprobar':
        item = Item.query.get(aprobacion.item_id)
        item.estado = 'aprobado'
        
        # Crear versión del cambio
        ultima_version = Version.query.filter_by(item_id=item.id).order_by(Version.numero_version.desc()).first()
        numero_version = (ultima_version.numero_version + 1) if ultima_version else 1
        
        version = Version(
            item_id=item.id,
            numero_version=numero_version,
            campo_modificado='Estado',
            valor_anterior='propuesto',
            valor_nuevo='aprobado',
            razon_cambio=f'Aprobado por Gerente: {comentarios}',
            usuario_id=session.get('user_id')
        )
        db.session.add(version)
    
    db.session.commit()
    
    return {'success': True, 'estado': aprobacion.estado}


@bp.route('/metricas/generar-automatico/<int:item_id>/<int:mes>/<int:anio>', methods=['POST'])
@login_required
def metrica_generar_automatico(item_id, mes, anio):
    """Generar métrica automáticamente basada en incidencias"""
    
    if session.get('rol') not in ['jefe_ti', 'gerente']:
        return {'success': False, 'error': 'No autorizado'}, 403
    
    # Verificar si ya existe
    metrica_existente = Metrica.query.filter_by(
        item_id=item_id,
        mes=mes,
        anio=anio
    ).first()
    
    if metrica_existente:
        return {'success': False, 'error': 'Ya existe métrica para este período'}, 400
    
    item = Item.query.get(item_id)
    if not item:
        return {'success': False, 'error': 'Item no encontrado'}, 404
    
    # ⚡ CONTAR INCIDENCIAS DEL MES AUTOMÁTICAMENTE
    from calendar import monthrange
    primer_dia = datetime(anio, mes, 1)
    ultimo_dia_num = monthrange(anio, mes)[1]
    ultimo_dia = datetime(anio, mes, ultimo_dia_num, 23, 59, 59)
    
    incidencias = Incidencia.query.filter(
        Incidencia.item_id == item_id,
        Incidencia.fecha_incidencia >= primer_dia,
        Incidencia.fecha_incidencia <= ultimo_dia
    ).count()
    
    # Calcular semáforo
    if item.tipo == 'producto':
        if incidencias == 0:
            semaforo = 'verde'
            porcentaje = 100
        elif incidencias <= 2:
            semaforo = 'amarillo'
            porcentaje = 85
        else:
            semaforo = 'rojo'
            porcentaje = 60
    else:
        # Para servicios: usar lógica simple por ahora
        if incidencias == 0:
            semaforo = 'verde'
            porcentaje = 100
        elif incidencias <= 2:
            semaforo = 'amarillo'
            porcentaje = 85
        else:
            semaforo = 'rojo'
            porcentaje = 60
    
    # Crear métrica
    metrica = Metrica(
        item_id=item_id,
        mes=mes,
        anio=anio,
        incidencias=incidencias,
        semaforo=semaforo,
        porcentaje_cumplimiento=porcentaje,
        registrado_por=session.get('user_id')
    )
    
    db.session.add(metrica)
    db.session.commit()
    
    # Generar alertas si aplica
    generar_alerta_automatica(item_id, metrica)
    
    return {
        'success': True,
        'incidencias': incidencias,
        'semaforo': semaforo,
        'porcentaje': porcentaje
    }

@bp.route('/alerta/<int:alerta_id>/resolver', methods=['POST'])
@login_required
@jefe_o_gerente_required
def resolver_alerta_con_incidencias(alerta_id):
    """Resuelve una alerta marcando incidencias específicas como resueltas"""
    try:
        data = request.get_json()
        incidencias_ids = data.get('incidencias_ids', [])
        
        alerta = Alerta.query.get_or_404(alerta_id)
        
        if alerta.estado == 'resuelta':
            return jsonify({'success': False, 'error': 'La alerta ya está resuelta'}), 400
        
        # Si no se seleccionaron incidencias, resolver la alerta manualmente
        if not incidencias_ids:
            alerta.estado = 'resuelta'
            alerta.fecha_resolucion = datetime.utcnow()
            alerta.resuelto_por = session.get('user_id')
            db.session.commit()
            
            return jsonify({
                'success': True,
                'mensaje': 'Alerta resuelta manualmente sin resolver incidencias'
            })
        
        # ✅ CORRECCIÓN: Resolver SOLO las incidencias seleccionadas
        incidencias_resueltas = []
        
        print(f"\n{'='*60}")
        print(f"🔍 INICIO DE RESOLUCIÓN - Alerta #{alerta_id}")
        print(f"{'='*60}")
        print(f"📥 IDs recibidas del frontend: {incidencias_ids}")
        print(f"📊 Estado inicial de la alerta:")
        print(f"   - incidencias_pendientes: {alerta.incidencias_pendientes}")
        print(f"   - incidencias_resueltas_count: {alerta.incidencias_resueltas_count}")
        
        # ✅ IMPORTANTE: Iterar SOLO sobre las IDs que el usuario seleccionó
        for inc_id in incidencias_ids:
            incidencia = Incidencia.query.get(inc_id)
            
            # ✅ VALIDAR: Solo resolver si existe, pertenece al item, y NO está resuelta
            if not incidencia:
                print(f"⚠️ Incidencia {inc_id} no encontrada")
                continue
            
            if incidencia.item_id != alerta.item_id:
                print(f"⚠️ Incidencia {inc_id} no pertenece al item de la alerta")
                continue
            
            if incidencia.estado == 'resuelta':
                print(f"⏭️ Incidencia {inc_id} ya está resuelta, omitiendo")
                continue
            
            # ✅ AHORA SÍ: Marcar como resuelta
            incidencia.estado = 'resuelta'
            incidencia.fecha_resolucion = datetime.utcnow()
            incidencia.resuelto_por = session.get('user_id')
            
            # Calcular tiempo de resolución
            if incidencia.fecha_incidencia:
                delta = incidencia.fecha_resolucion - incidencia.fecha_incidencia
                incidencia.tiempo_resolucion = int(delta.total_seconds() / 60)
            
            # Vincular incidencia con alerta
            relacion = AlertaIncidencia(
                alerta_id=alerta_id,
                incidencia_id=inc_id
            )
            db.session.add(relacion)
            incidencias_resueltas.append(incidencia.titulo)
            
            print(f"✅ Incidencia #{inc_id} resuelta: {incidencia.titulo}")
        
        print(f"\n{'='*60}")
        print(f"🔍 DIAGNÓSTICO ANTES DEL COMMIT")
        print(f"{'='*60}")
        print(f"📋 Incidencias procesadas en este ciclo: {len(incidencias_resueltas)}")
        print(f"📊 Contador ANTES de actualizar: {alerta.incidencias_resueltas_count}")
        print(f"🔗 Relaciones AlertaIncidencia en memoria: {len([r for r in db.session.new if isinstance(r, AlertaIncidencia)])}")
        
        # ✅ CRÍTICO: Actualizar contador de incidencias resueltas EN LA ALERTA
        alerta.incidencias_resueltas_count += len(incidencias_resueltas)
        
        print(f"➕ Incrementando contador en: {len(incidencias_resueltas)}")
        print(f"📊 Contador DESPUÉS de incrementar: {alerta.incidencias_resueltas_count}")
        
        # ✅ Commit ANTES de recalcular
        db.session.commit()
        
        print(f"\n{'='*60}")
        print(f"📊 DESPUÉS DEL COMMIT")
        print(f"{'='*60}")
        print(f"🔗 Relaciones AlertaIncidencia en BD: {AlertaIncidencia.query.filter_by(alerta_id=alerta_id).count()}")
        print(f"📊 Contador en BD: {Alerta.query.get(alerta_id).incidencias_resueltas_count}")
        
        # ✅ PASO 1: RECALCULAR SLA del item (UNA SOLA VEZ)
        if incidencias_resueltas:
            print(f"♻️ Recalculando SLA para item {alerta.item_id}")
            recalcular_sla_mes_actual(alerta.item_id)
            
            # ✅ PASO 2: RESOLVER alertas si ya no sobrepasa SLA
            resolver_alertas_si_vuelve_normal(alerta.item_id)
        
        # Actualizar estado de la alerta
        print(f"\n🔄 Ejecutando alerta.actualizar_estado_incidencias()...")
        alerta.actualizar_estado_incidencias()
        
        print(f"\n{'='*60}")
        print(f"✅ ESTADO FINAL")
        print(f"{'='*60}")
        print(f"📊 Contador final: {alerta.incidencias_resueltas_count}")
        print(f"📊 Incidencias pendientes: {alerta.incidencias_pendientes}")
        print(f"📊 Estado de la alerta: {alerta.estado}")
        print(f"{'='*60}\n")
        
        mensaje = f"✅ {len(incidencias_resueltas)} incidencia(s) resuelta(s) correctamente"
        if alerta.estado == 'resuelta':
            mensaje += ". La alerta se resolvió automáticamente."
        else:
            mensaje += f". Aún quedan {alerta.incidencias_pendientes - alerta.incidencias_resueltas_count} incidencia(s) pendiente(s)."
        
        return jsonify({
            'success': True,
            'mensaje': mensaje,
            'alerta_resuelta': alerta.estado == 'resuelta',
            'incidencias_resueltas': len(incidencias_resueltas),
            'incidencias_pendientes': alerta.incidencias_pendientes - alerta.incidencias_resueltas_count
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error en resolver_alerta_con_incidencias: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/alertas')
@login_required
def alertas():
    estado_filtro = request.args.get('estado', '')
    tipo_filtro = request.args.get('tipo', '')
    urgencia_filtro = request.args.get('urgencia', '')
    
    # ✅ CORRECCIÓN: Usar la relación definida en el modelo
    query = Alerta.query
    
    if estado_filtro:
        query = query.filter(Alerta.estado == estado_filtro)
    if tipo_filtro:
        query = query.filter(Alerta.tipo == tipo_filtro)
    if urgencia_filtro:
        query = query.filter(Alerta.nivel_urgencia == urgencia_filtro)
    
    # ✅ Obtener alertas con sus items relacionados
    alertas_raw = query.order_by(Alerta.fecha_creacion.desc()).all()
    
    # ✅ CREAR LISTA CON ESTRUCTURA CORRECTA
    alertas = []
    for alerta in alertas_raw:
        item = Item.query.get(alerta.item_id)
        if item:
            alertas.append({
                'alerta': alerta,
                'item': item
            })
    
    # Estadísticas
    total_alertas = Alerta.query.count()
    alertas_activas = Alerta.query.filter_by(estado='activa').count()
    alertas_resueltas = Alerta.query.filter_by(estado='resuelta').count()
    alertas_criticas = Alerta.query.filter_by(estado='activa', nivel_urgencia='critica').count()
    alertas_altas = Alerta.query.filter_by(estado='activa', nivel_urgencia='alta').count()
    
    return render_template('alertas.html',
                         alertas=alertas,
                         total_alertas=total_alertas,
                         alertas_activas=alertas_activas,
                         alertas_resueltas=alertas_resueltas,
                         alertas_criticas=alertas_criticas,
                         alertas_altas=alertas_altas,
                         estado_filtro=estado_filtro,
                         tipo_filtro=tipo_filtro,
                         urgencia_filtro=urgencia_filtro)


@bp.route('/metricas')
def metricas_lista():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Obtener filtros
    item_id = request.args.get('item_id', '')
    mes = request.args.get('mes', '')
    anio = request.args.get('anio', '')
    semaforo = request.args.get('semaforo', '')
    
    # Query base
    query = Metrica.query
    
    # Aplicar filtros
    if item_id:
        query = query.filter_by(item_id=int(item_id))
    if mes:
        query = query.filter_by(mes=int(mes))
    if anio:
        query = query.filter_by(anio=int(anio))
    if semaforo:
        query = query.filter_by(semaforo=semaforo)
    
    # Obtener métricas ordenadas
    metricas_raw = query.order_by(Metrica.anio.desc(), Metrica.mes.desc()).all()
    
    # CREAR LISTA CON ITEMS
    metricas = []
    for metrica in metricas_raw:
        item = Item.query.get(metrica.item_id)
        if item:
            metricas.append({
                'metrica': metrica,
                'item': item
            })
    
    # Estadísticas
    total_metricas = Metrica.query.count()
    metricas_verde = Metrica.query.filter_by(semaforo='verde').count()
    metricas_amarillo = Metrica.query.filter_by(semaforo='amarillo').count()
    metricas_rojo = Metrica.query.filter_by(semaforo='rojo').count()
    
    # Cumplimiento promedio
    cumplimiento_promedio = db.session.query(
        func.avg(Metrica.porcentaje_cumplimiento)
    ).filter(Metrica.porcentaje_cumplimiento.isnot(None)).scalar() or 0
    
    # ✅ CORRECCIÓN CRÍTICA: Items APROBADOS y ACTIVOS (NO REEMPLAZADOS)
    items_reemplazados = db.session.query(Item.reemplaza_a_id).filter(
        Item.reemplaza_a_id.isnot(None)
    ).subquery()
    
    items = Item.query.filter(
        Item.estado == 'aprobado',              # ← CORRECTO: estado de aprobación
        Item.estado_operativo == 'activo',      # ← CORRECTO: estado operativo
        ~Item.id.in_(items_reemplazados)        # ← CORRECTO: no reemplazados
    ).order_by(Item.tipo, Item.codigo).all()
    
    return render_template('metricas_lista.html',
                         metricas=metricas,
                         total_metricas=total_metricas,
                         metricas_verde=metricas_verde,
                         metricas_amarillo=metricas_amarillo,
                         metricas_rojo=metricas_rojo,
                         cumplimiento_promedio=round(cumplimiento_promedio, 1),
                         items=items,  # ← CORRECTO: Ahora pasa items filtrados correctamente
                         item_id=item_id,
                         mes=mes,
                         anio=anio,
                         semaforo=semaforo)


@bp.route('/metricas/<int:id>/eliminar', methods=['POST'])
def metrica_eliminar(id):
    if 'user_id' not in session:
        return {'success': False, 'error': 'No autenticado'}, 401
    
    # Solo Jefe TI y Gerente pueden eliminar
    if session.get('rol') not in ['jefe_ti', 'gerente']:
        return {'success': False, 'error': 'No autorizado'}, 403
    
    metrica = Metrica.query.get_or_404(id)
    db.session.delete(metrica)
    db.session.commit()
    
    return {'success': True}


@bp.route('/historial/<int:item_id>')
def historial(item_id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    item = Item.query.get_or_404(item_id)
    
    # Obtener todas las versiones
    versiones = Version.query.filter_by(item_id=item_id).order_by(Version.fecha.desc()).all()
    
    # Obtener historial de aprobaciones
    aprobaciones = Aprobacion.query.filter_by(item_id=item_id).order_by(Aprobacion.fecha_solicitud.desc()).all()
    
    # Obtener historial de métricas
    metricas = Metrica.query.filter_by(item_id=item_id).order_by(Metrica.anio.desc(), Metrica.mes.desc()).all()
    
    # Estadísticas del historial
    total_versiones = len(versiones)
    total_cambios = len([v for v in versiones if v.campo_modificado != 'Creación inicial'])
    
    # Usuarios que han modificado
    usuarios_ids = list(set([v.usuario_id for v in versiones if v.usuario_id]))
    usuarios = Usuario.query.filter(Usuario.id.in_(usuarios_ids)).all() if usuarios_ids else []
    
    return render_template('historial.html',
                         item=item,
                         versiones=versiones,
                         aprobaciones=aprobaciones,
                         metricas=metricas,
                         total_versiones=total_versiones,
                         total_cambios=total_cambios,
                         usuarios=usuarios)


@bp.route('/historial/<int:item_id>/comparar')
def historial_comparar(item_id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    version1_id = request.args.get('v1')
    version2_id = request.args.get('v2')
    
    if not version1_id or not version2_id:
        flash('Debe seleccionar dos versiones para comparar', 'warning')
        return redirect(url_for('main.historial', item_id=item_id))
    
    version1 = Version.query.get_or_404(version1_id)
    version2 = Version.query.get_or_404(version2_id)
    item = Item.query.get_or_404(item_id)
    
    return render_template('historial_comparar.html',
                         item=item,
                         version1=version1,
                         version2=version2)


# ====================================
# AGREGAR ESTAS RUTAS AL FINAL DE routes.py
# ====================================

# ====================================
# HISTORIAL DE REEMPLAZOS
# ====================================

@bp.route('/reemplazos')
def reemplazos():
    """Vista principal del historial de reemplazos"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    return render_template('item_reemplazos.html')


@bp.route('/api/items-reemplazos')
def api_items_reemplazos():
    """API: Obtener todos los items con información de reemplazos"""
    if 'user_id' not in session:
        return {'error': 'No autenticado'}, 401
    
    try:
        items = Item.query.order_by(Item.fecha_creacion.desc()).all()
        
        items_json = []
        for item in items:
            # Verificar si tiene reemplazo posterior
            tiene_reemplazo = Item.query.filter_by(reemplaza_a_id=item.id).first() is not None
            
            # Contar niveles en la cadena
            nivel_anterior = contar_nivel_anterior(item)
            nivel_posterior = contar_nivel_posterior(item)
            
            items_json.append({
                'id': item.id,
                'codigo': item.codigo,
                'nombre': item.nombre,
                'tipo': item.tipo,
                'categoria': item.categoria,
                'estado': item.estado,
                'responsable': item.responsable,
                'fecha_creacion': item.fecha_creacion.isoformat(),
                'reemplaza_a_id': item.reemplaza_a_id,
                'motivo_reemplazo': item.motivo_reemplazo,
                'tiene_reemplazo': tiene_reemplazo,
                'nivel_anterior': nivel_anterior,
                'nivel_posterior': nivel_posterior
            })
        
        return {
            'success': True,
            'items': items_json,
            'total': len(items_json)
        }
    
    except Exception as e:
        print(f"Error en api_items_reemplazos: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }, 500


@bp.route('/api/cadena-reemplazos/<int:item_id>')
def api_cadena_reemplazos(item_id):
    """API: Obtener la cadena completa de reemplazos de un item"""
    if 'user_id' not in session:
        return {'error': 'No autenticado'}, 401
    
    try:
        item_actual = Item.query.get_or_404(item_id)
        
        # ========================================
        # CONSTRUIR CADENA ANTERIOR (MÁS ANTIGUA)
        # ========================================
        cadena_anterior = []
        item_temp = item_actual
        contador_seguridad = 0
        
        print(f"🔍 Construyendo cadena ANTERIOR para item {item_actual.codigo}")
        
        while item_temp.reemplaza_a_id is not None and contador_seguridad < 50:
            contador_seguridad += 1
            print(f"  ↑ Item {item_temp.codigo} reemplaza a ID: {item_temp.reemplaza_a_id}")
            
            # Buscar el item que fue reemplazado
            item_ant = Item.query.get(item_temp.reemplaza_a_id)
            
            if not item_ant:
                print(f"  ⚠️ Item con ID {item_temp.reemplaza_a_id} no encontrado")
                break
                
            print(f"  ✅ Encontrado: {item_ant.codigo} - {item_ant.nombre}")
            
            cadena_anterior.append({
                'id': item_ant.id,
                'codigo': item_ant.codigo,
                'nombre': item_ant.nombre,
                'tipo': item_ant.tipo,
                'categoria': item_ant.categoria,
                'estado': item_ant.estado,
                'responsable': item_ant.responsable,
                'fecha_creacion': item_ant.fecha_creacion.isoformat() if item_ant.fecha_creacion else None,
                'motivo_reemplazo': item_temp.motivo_reemplazo,
                'fecha_reemplazo': item_temp.fecha_reemplazo.isoformat() if item_temp.fecha_reemplazo else None
            })
            
            item_temp = item_ant
        
        print(f"📊 Total items ANTERIORES encontrados: {len(cadena_anterior)}")
        
        # ========================================
        # CONSTRUIR CADENA POSTERIOR (MÁS NUEVA)
        # ========================================
        cadena_posterior = []
        item_temp = item_actual
        contador_seguridad = 0
        
        print(f"🔍 Construyendo cadena POSTERIOR para item {item_actual.codigo}")
        
        while contador_seguridad < 50:
            contador_seguridad += 1
            
            # Buscar items que reemplazan al actual
            item_post = Item.query.filter_by(reemplaza_a_id=item_temp.id).first()
            
            if not item_post:
                print(f"  ✅ No hay más items posteriores")
                break
                
            print(f"  ↓ {item_post.codigo} reemplaza a {item_temp.codigo}")
            
            cadena_posterior.append({
                'id': item_post.id,
                'codigo': item_post.codigo,
                'nombre': item_post.nombre,
                'tipo': item_post.tipo,
                'categoria': item_post.categoria,
                'estado': item_post.estado,
                'responsable': item_post.responsable,
                'fecha_creacion': item_post.fecha_creacion.isoformat() if item_post.fecha_creacion else None,
                'motivo_reemplazo': item_post.motivo_reemplazo,
                'fecha_reemplazo': item_post.fecha_reemplazo.isoformat() if item_post.fecha_reemplazo else None
            })
            
            item_temp = item_post
        
        print(f"📊 Total items POSTERIORES encontrados: {len(cadena_posterior)}")
        
        # ========================================
        # ITEM ACTUAL
        # ========================================
        item_actual_json = {
            'id': item_actual.id,
            'codigo': item_actual.codigo,
            'nombre': item_actual.nombre,
            'tipo': item_actual.tipo,
            'categoria': item_actual.categoria,
            'estado': item_actual.estado,
            'responsable': item_actual.responsable,
            'fecha_creacion': item_actual.fecha_creacion.isoformat() if item_actual.fecha_creacion else None,
            'motivo_reemplazo': item_actual.motivo_reemplazo,
            'fecha_reemplazo': item_actual.fecha_reemplazo.isoformat() if item_actual.fecha_reemplazo else None
        }
        
        total_versiones = len(cadena_anterior) + 1 + len(cadena_posterior)
        print(f"🎯 TOTAL VERSIONES EN CADENA: {total_versiones}")
        
        return {
            'success': True,
            'item_actual': item_actual_json,
            'cadena_anterior': cadena_anterior,
            'cadena_posterior': cadena_posterior,
            'total_versiones': total_versiones
        }
    
    except Exception as e:
        print(f"❌ ERROR en api_cadena_reemplazos: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e)
        }, 500


# ====================================
# FUNCIONES AUXILIARES
# ====================================

def contar_nivel_anterior(item):
    """Cuenta cuántos niveles anteriores tiene un item en su cadena de reemplazos"""
    contador = 0
    item_temp = item
    while item_temp.reemplaza_a:
        contador += 1
        item_temp = item_temp.reemplaza_a
        # Prevenir ciclos infinitos
        if contador > 50:
            break
    return contador


def contar_nivel_posterior(item):
    """Cuenta cuántos niveles posteriores tiene un item en su cadena de reemplazos"""
    contador = 0
    item_temp = item
    while True:
        item_post = Item.query.filter_by(reemplaza_a_id=item_temp.id).first()
        if not item_post:
            break
        contador += 1
        item_temp = item_post
        # Prevenir ciclos infinitos
        if contador > 50:
            break
    return contador

# ====================================
# AGREGAR AL FINAL DE app/routes.py
# Generar PDF del Historial de Reemplazos
# ====================================



@bp.route('/producto/<int:id>/historial')
def producto_historial(id):
    """Redirigir al historial del producto"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Verificar que sea un producto
    producto = Item.query.get_or_404(id)
    if producto.tipo != 'producto':
        flash('El item no es un producto', 'warning')
        return redirect(url_for('main.productos'))
    
    # Redirigir a la ruta genérica de historial
    return redirect(url_for('main.historial', item_id=id))


@bp.route('/servicio/<int:id>/historial')
def servicio_historial(id):
    """Redirigir al historial del servicio"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Verificar que sea un servicio
    servicio = Item.query.get_or_404(id)
    if servicio.tipo != 'servicio':
        flash('El item no es un servicio', 'warning')
        return redirect(url_for('main.servicios'))
    
    # Redirigir a la ruta genérica de historial
    return redirect(url_for('main.historial', item_id=id))


# ====================================
# GESTIÓN DE INCIDENCIAS
# ====================================
# ====================================
# INCIDENCIAS (4 RUTAS SOLAMENTE)
# ====================================

@bp.route('/incidencias')
@login_required
def incidencias_lista():
    """Lista todas las incidencias"""
    estado_filtro = request.args.get('estado', '')
    item_id = request.args.get('item_id', '')
    
    query = Incidencia.query
    
    if estado_filtro:
        query = query.filter_by(estado=estado_filtro)
    if item_id:
        query = query.filter_by(item_id=int(item_id))
    
    incidencias = query.order_by(Incidencia.fecha_incidencia.desc()).all()
    
    # Estadísticas
    total_incidencias = Incidencia.query.count()
    incidencias_abiertas = Incidencia.query.filter_by(estado='abierta').count()
    incidencias_proceso = Incidencia.query.filter_by(estado='en_proceso').count()
    incidencias_resueltas = Incidencia.query.filter_by(estado='resuelta').count()
    
    # Items activos
    items_reemplazados = db.session.query(Item.reemplaza_a_id).filter(
        Item.reemplaza_a_id.isnot(None)
    ).subquery()
    
    items = Item.query.filter(
        Item.estado == 'aprobado',
        Item.estado_operativo == 'activo',
        ~Item.id.in_(items_reemplazados)
    ).order_by(Item.codigo).all()
    
    # ✅ CARGAR SERVICIOS AFECTADOS
    from app.models import ServicioAfectado
    servicios_afectados = ServicioAfectado.query.filter_by(activo=True).order_by(ServicioAfectado.nombre).all()
    
    return render_template('incidencias_lista.html',
                         incidencias=incidencias,
                         total_incidencias=total_incidencias,
                         incidencias_abiertas=incidencias_abiertas,
                         incidencias_proceso=incidencias_proceso,
                         incidencias_resueltas=incidencias_resueltas,
                         items=items,
                         servicios_afectados=servicios_afectados,  # ✅ NUEVO
                         estado_filtro=estado_filtro,
                         item_id=item_id)


@bp.route('/incidencias/registrar', methods=['POST'])
@login_required
def incidencia_registrar():
    """Registrar nueva incidencia y recalcular SLA automáticamente"""
    item_id = request.form.get('item_id')
    titulo = request.form.get('titulo')
    descripcion = request.form.get('descripcion')
    tipo = request.form.get('tipo')
    severidad = request.form.get('severidad')
    usuarios_afectados = request.form.get('usuarios_afectados')
    
    # Obtener técnico asignado (opcional)
    tecnico_id = request.form.get('tecnico_id')
    enviar_email = request.form.get('enviar_email') == 'true'
    
    # Recibir servicios como lista
    servicios_seleccionados = request.form.getlist('servicios_afectados')
    servicios_afectados_str = ','.join(servicios_seleccionados) if servicios_seleccionados else None
    
    # Crear incidencia
    incidencia = Incidencia(
        item_id=item_id,
        titulo=titulo,
        descripcion=descripcion,
        tipo=tipo,
        severidad=severidad,
        usuarios_afectados=int(usuarios_afectados) if usuarios_afectados else None,
        servicios_afectados=servicios_afectados_str,
        estado='abierta',
        registrado_por=session.get('user_id')
    )
    
    db.session.add(incidencia)
    db.session.commit()
    
    # ⚡ PASO 1: RECALCULAR SLA DEL MES ACTUAL
    recalcular_sla_mes_actual(item_id)
    
    # ⚡ PASO 2: VERIFICAR SI SOBREPASA SLA Y GENERAR ALERTA
    alerta_generada = generar_alerta_si_sobrepasa_sla(item_id)
    
    # ✅ PASO 3: SI SE GENERÓ ALERTA, ENVIAR NOTIFICACIONES
    if alerta_generada:
        enviar_notificaciones_alerta_critica(alerta_generada)
    
    # ✅ PASO 4: ENVIAR EMAIL AL TÉCNICO SI SE SELECCIONÓ
    if tecnico_id and enviar_email:
        tecnico = Usuario.query.get(tecnico_id)
        if tecnico and tecnico.persona and tecnico.persona.correo:
            item = Item.query.get(item_id)
            enviar_notificacion_incidencia(current_app._get_current_object(), tecnico, incidencia, item)
            flash(f'✅ Incidencia registrada: {titulo}. Email enviado a {tecnico.persona.nombres} ({tecnico.persona.correo})', 'success')
        else:
            flash(f'✅ Incidencia registrada: {titulo}. ⚠️ No se pudo enviar email: técnico sin correo.', 'warning')
    else:
        mensaje = f'✅ Incidencia registrada: {titulo}. SLA recalculado automáticamente.'
        if alerta_generada:
            mensaje += f' 🚨 Se generó una alerta crítica y se notificó al equipo.'
        flash(mensaje, 'success')
    
    return redirect(url_for('main.incidencias_lista'))

def recalcular_sla_mes_actual(item_id):
    """Recalcula el SLA del mes actual después de registrar/resolver una incidencia"""
    try:
        # Obtener mes y año actual
        mes_actual = datetime.now().month
        anio_actual = datetime.now().year
        
        # Buscar métrica del mes actual
        metrica = Metrica.query.filter_by(
            item_id=item_id,
            mes=mes_actual,
            anio=anio_actual
        ).first()
        
        if not metrica:
            print(f"⚠️  No existe métrica del mes {mes_actual}/{anio_actual} para item {item_id}")
            return
        
        # Contar incidencias ACTIVAS del mes actual
        incidencias_activas = Incidencia.query.filter(
            Incidencia.item_id == item_id,
            Incidencia.estado != 'resuelta',
            db.func.extract('month', Incidencia.fecha_incidencia) == mes_actual,
            db.func.extract('year', Incidencia.fecha_incidencia) == anio_actual
        ).count()
        
        # Actualizar contador de incidencias
        metrica.incidencias = incidencias_activas
        
        # ✅ CÁLCULO CORRECTO DEL SEMÁFORO
        if incidencias_activas == 0:
            porcentaje = 100.0
            semaforo = 'verde'
        elif incidencias_activas <= 2:
            # Amarillo: 1-2 incidencias
            porcentaje = 100.0 - (incidencias_activas * 7.5)  # 92.5% con 1, 85% con 2
            semaforo = 'amarillo'
        else:
            # Rojo: 3+ incidencias
            porcentaje = max(0, 85.0 - ((incidencias_activas - 2) * 15))  # 70% con 3, 55% con 4...
            semaforo = 'rojo'
        
        # Actualizar métrica
        metrica.porcentaje_cumplimiento = round(porcentaje, 2)
        metrica.semaforo = semaforo
        
        db.session.commit()
        
        print(f"✅ SLA recalculado para item {item_id}: {incidencias_activas} inc → {porcentaje}% ({semaforo})")
        
    except Exception as e:
        print(f"❌ Error al recalcular SLA: {str(e)}")
        db.session.rollback()


@bp.route('/incidencias/<int:id>/resolver', methods=['POST'])
@login_required
def incidencia_resolver(id):
    """Resolver incidencia con imagen y comentario obligatorios"""
    try:
        incidencia = Incidencia.query.get_or_404(id)
        
        # Validar archivo
        if 'imagen_prueba' not in request.files:
            return jsonify({'success': False, 'error': 'Debe adjuntar una imagen como prueba de resolución'}), 400
        
        archivo = request.files['imagen_prueba']
        
        if archivo.filename == '':
            return jsonify({'success': False, 'error': 'Debe seleccionar una imagen'}), 400
        
        # Validar comentario
        comentario = request.form.get('comentario_resolucion', '').strip()
        if not comentario or len(comentario) < 10:
            return jsonify({'success': False, 'error': 'Debe ingresar un comentario de al menos 10 caracteres'}), 400
        
        # Validar extensión
        extensiones_permitidas = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        extension = archivo.filename.rsplit('.', 1)[1].lower() if '.' in archivo.filename else ''
        
        if extension not in extensiones_permitidas:
            return jsonify({'success': False, 'error': 'Formato no válido. Use: PNG, JPG, JPEG, GIF o WEBP'}), 400
        
        # ✅ CORREGIDO: Importar os al inicio para evitar conflicto
        import os as os_module
        
        # Validar tamaño (máx 5MB)
        archivo.seek(0, os_module.SEEK_END)  # ✅ Usar os_module en lugar de os
        tamaño = archivo.tell()
        archivo.seek(0)
        
        if tamaño > 5 * 1024 * 1024:
            return jsonify({'success': False, 'error': 'La imagen no debe superar los 5MB'}), 400
        
        # Generar nombre único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f"resolucion_{id}_{timestamp}.{extension}"
        
        # Guardar archivo
        from werkzeug.utils import secure_filename
        
        upload_folder = os_module.path.join(current_app.root_path, 'static', 'resoluciones')
        os_module.makedirs(upload_folder, exist_ok=True)
        
        ruta_completa = os_module.path.join(upload_folder, nombre_archivo)
        archivo.save(ruta_completa)
        
        print(f"✅ Imagen guardada en: {ruta_completa}")
        
        # ⚠️ CRÍTICO: Guardar SOLO la ruta relativa sin /static/
        ruta_relativa = f"resoluciones/{nombre_archivo}"
        
        # Obtener usuario actual
        usuario_actual = Usuario.query.get(session.get('user_id'))
        persona_actual = Persona.query.filter_by(usuario_id=usuario_actual.id).first()
        nombre_completo = f"{persona_actual.nombres} {persona_actual.apellidos}" if persona_actual else usuario_actual.username
        
        # Actualizar incidencia
        incidencia.estado = 'resuelta'
        incidencia.fecha_resolucion = datetime.utcnow()
        incidencia.resuelto_por = session.get('user_id')
        incidencia.imagen_resolucion = ruta_relativa  # ✅ SIN /static/
        incidencia.comentario_resolucion = comentario
        
        # Calcular tiempo de resolución
        if incidencia.fecha_incidencia:
            delta = incidencia.fecha_resolucion - incidencia.fecha_incidencia
            incidencia.tiempo_resolucion = int(delta.total_seconds() / 60)
        
        db.session.commit()
        
        print(f"✅ Ruta guardada en BD: {incidencia.imagen_resolucion}")
        
        # Recalcular SLA
        recalcular_sla_mes_actual(incidencia.item_id)
        resolver_alertas_si_vuelve_normal(incidencia.item_id)
        
        return jsonify({
            'success': True,
            'mensaje': 'Incidencia resuelta correctamente',
            'resuelto_por': nombre_completo
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al resolver incidencia: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/usuario-actual-info')
@login_required
def api_usuario_actual_info():
    """API: Obtener información completa del usuario actual"""
    try:
        usuario = Usuario.query.get(session.get('user_id'))
        persona = Persona.query.filter_by(usuario_id=usuario.id).first()
        
        nombre_completo = f"{persona.nombres} {persona.apellidos}" if persona else usuario.username
        
        return {
            'success': True,
            'username': usuario.username,
            'rol': usuario.rol,
            'nombre_completo': nombre_completo
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500
    
@bp.route('/api/incidencia/<int:id>/detalle-resolucion')
@login_required
def api_detalle_resolucion(id):
    """API: Obtener detalles completos de resolución de incidencia"""
    try:
        incidencia = Incidencia.query.get_or_404(id)
        
        if incidencia.estado != 'resuelta':
            return jsonify({
                'success': False,
                'error': 'Esta incidencia no está resuelta'
            }), 400
        
        # Obtener nombre del usuario que resolvió
        if incidencia.resuelto_por:
            usuario_resolvio = Usuario.query.get(incidencia.resuelto_por)
            persona_resolvio = Persona.query.filter_by(usuario_id=usuario_resolvio.id).first()
            nombre_resolvio = f"{persona_resolvio.nombres} {persona_resolvio.apellidos}" if persona_resolvio else usuario_resolvio.username
        else:
            nombre_resolvio = "No registrado"
        
        # ✅ LIMPIAR VALORES 'None' COMO STRING
        imagen_resolucion = incidencia.imagen_resolucion
        if imagen_resolucion in ['None', 'null', None, '']:
            imagen_resolucion = None
        
        comentario_resolucion = incidencia.comentario_resolucion
        if comentario_resolucion in ['None', 'null', None, '']:
            comentario_resolucion = 'Sin comentario'
        
        print(f"🔍 DEBUG API:")
        print(f"  - ID: {incidencia.id}")
        print(f"  - Imagen en BD: '{incidencia.imagen_resolucion}'")
        print(f"  - Imagen limpia: '{imagen_resolucion}'")
        print(f"  - Comentario: '{comentario_resolucion}'")
        
        return jsonify({
            'success': True,
            'incidencia': {
                'id': incidencia.id,
                'titulo': incidencia.titulo,
                'item_codigo': incidencia.item.codigo,
                'item_nombre': incidencia.item.nombre,
                'fecha_incidencia': incidencia.fecha_incidencia.strftime('%d/%m/%Y %H:%M') if incidencia.fecha_incidencia else '-',
                'fecha_resolucion': incidencia.fecha_resolucion.strftime('%d/%m/%Y %H:%M') if incidencia.fecha_resolucion else '-',
                'resuelto_por': nombre_resolvio,
                'comentario_resolucion': comentario_resolucion,
                'imagen_resolucion': imagen_resolucion  # ✅ None o ruta limpia
            }
        })
    except Exception as e:
        print(f"❌ Error API: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/incidencias/<int:id>/alerta-critica', methods=['POST'])
@login_required
def incidencia_alerta_critica(id):
    """Generar alerta crítica MANUAL (sin restricciones)"""
    if session.get('rol') not in ['jefe_ti', 'gerente']:
        return {'success': False, 'error': 'No autorizado'}, 403
    
    incidencia = Incidencia.query.get_or_404(id)
    item = incidencia.item
    
    # Verificar si ya existe
    alerta_existente = Alerta.query.filter_by(
        item_id=incidencia.item_id,
        tipo='alerta_manual_critica',
        estado='activa'
    ).first()
    
    if alerta_existente:
        return {'success': False, 'error': 'Ya existe alerta crítica activa'}, 400
    
    # Crear alerta
    alerta = Alerta(
        item_id=incidencia.item_id,
        tipo='alerta_manual_critica',
        nivel_urgencia='critica',
        mensaje=f'🔴 ALERTA CRÍTICA MANUAL: {item.codigo} - {item.nombre}. '
                f'Incidencia: "{incidencia.titulo}". '
                f'Generada por {session.get("username")}.',
        estado='activa'
    )
    
    db.session.add(alerta)
    db.session.commit()
    
    # ✅ CRÍTICO: ENVIAR NOTIFICACIONES POR EMAIL
    try:
        # Obtener técnicos y jefes TI con correo
        usuarios_notificar = Usuario.query.filter(
            Usuario.rol.in_(['tecnico', 'jefe_ti'])
        ).all()
        
        destinatarios = []
        for usuario in usuarios_notificar:
            if usuario.persona and usuario.persona.correo:
                destinatarios.append(usuario.persona.correo)
                print(f"📧 Destinatario: {usuario.persona.nombres} ({usuario.persona.correo})")
        
        if destinatarios:
            # ✅ LLAMAR A LA FUNCIÓN DE EMAIL_SERVICE
            resultado = enviar_notificacion_alerta_critica(
                app=current_app._get_current_object(),
                alerta=alerta,
                item=item,
                destinatarios=destinatarios
            )
            
            if resultado:
                print(f"✅ Emails enviados exitosamente a {len(destinatarios)} usuario(s)")
                return {
                    'success': True, 
                    'mensaje': f'✅ Alerta crítica generada y notificada a {len(destinatarios)} usuario(s)'
                }
            else:
                return {
                    'success': True, 
                    'mensaje': '⚠️ Alerta generada pero hubo error al enviar emails'
                }
        else:
            print("⚠️ No hay técnicos/jefes con correo registrado")
            return {
                'success': True, 
                'mensaje': '⚠️ Alerta generada pero no hay destinatarios con correo'
            }
    
    except Exception as e:
        print(f"❌ Error al enviar notificaciones: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': True, 
            'mensaje': '⚠️ Alerta generada pero falló el envío de emails'
        }

def generar_alerta_si_sobrepasa_sla(item_id):
    """
    Genera alerta si el item sobrepasa su límite de SLA
    ✅ MODIFICADO: Retorna la alerta generada para enviar notificaciones
    """
    try:
        item = Item.query.get(item_id)
        if not item:
            return None
        
        # Obtener SLA y calcular límite
        sla = SLA.query.filter_by(item_id=item_id).first()
        
        # Calcular límite según tipo
        if item.tipo == 'producto':
            if not sla:
                limite_sla = 2  # Default para productos sin SLA
            else:
                limite_sla = (sla.fallas_criticas_permitidas or 0) + (sla.fallas_menores_permitidas or 0)
        else:  # servicio
            limite_sla = 2  # Límite en 2 para servicios
        
        if limite_sla == 0:
            limite_sla = 2  # Mínimo por seguridad
        
        # Obtener incidencias del mes actual
        mes_actual = datetime.now().month
        anio_actual = datetime.now().year
        
        incidencias_activas = Incidencia.query.filter(
            Incidencia.item_id == item_id,
            Incidencia.estado != 'resuelta',
            db.func.extract('month', Incidencia.fecha_incidencia) == mes_actual,
            db.func.extract('year', Incidencia.fecha_incidencia) == anio_actual
        ).count()
        
        # Generar alerta si ALCANZA O SOBREPASA el límite
        if incidencias_activas > limite_sla:
            alerta_existente = Alerta.query.filter_by(
                item_id=item_id,
                tipo='sobrepaso_sla',
                estado='activa'
            ).first()
            
            if not alerta_existente:
                mensaje = f"⚠️ SOBREPASO DE SLA: {item.codigo} - {item.nombre} ha superado su límite de {limite_sla} incidencias mensuales. Actualmente tiene {incidencias_activas} incidencias activas."
                
                nueva_alerta = Alerta(
                    item_id=item_id,
                    tipo='sobrepaso_sla',
                    mensaje=mensaje,
                    nivel_urgencia='critica',
                    estado='activa',
                    incidencias_pendientes=incidencias_activas
                )
                
                db.session.add(nueva_alerta)
                db.session.commit()
                print(f"✅ Alerta de sobrepaso SLA generada para {item.codigo}")
                
                # ✅ RETORNAR LA ALERTA GENERADA
                return nueva_alerta
            else:
                # Actualizar contador en alerta existente
                alerta_existente.incidencias_pendientes = incidencias_activas
                db.session.commit()
                return None  # No enviar notificación si ya existe
        else:
            # Si ya no sobrepasa, resolver alertas activas
            alertas_activas = Alerta.query.filter_by(
                item_id=item_id,
                tipo='sobrepaso_sla',
                estado='activa'
            ).all()
            
            for alerta in alertas_activas:
                alerta.estado = 'resuelta'
                alerta.fecha_resolucion = datetime.utcnow()
            
            if alertas_activas:
                db.session.commit()
                print(f"✅ Alertas auto-resueltas para {item.codigo}")
        
        return None
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.session.rollback()
        return None
    

def enviar_notificaciones_alerta_critica(alerta):
    """
    Envía notificaciones por email a técnicos y jefes TI cuando se genera una alerta crítica
    
    Args:
        alerta: Objeto Alerta recién creado
    """
    try:
        # Obtener el item relacionado
        item = Item.query.get(alerta.item_id)
        if not item:
            print("⚠️ No se encontró el item para la alerta")
            return False
        
        # ✅ OBTENER CORREOS DE TÉCNICOS Y JEFES TI
        usuarios_notificar = Usuario.query.filter(
            Usuario.rol.in_(['tecnico', 'jefe_ti'])
        ).all()
        
        destinatarios = []
        for usuario in usuarios_notificar:
            if usuario.persona and usuario.persona.correo:
                destinatarios.append(usuario.persona.correo)
                print(f"📧 Agregando destinatario: {usuario.persona.nombres} ({usuario.persona.correo})")
        
        if not destinatarios:
            print("⚠️ No hay destinatarios con correo registrado")
            return False
        
        # ✅ ENVIAR NOTIFICACIÓN
        from app.email_service import enviar_notificacion_alerta_critica
        
        resultado = enviar_notificacion_alerta_critica(
            app=current_app._get_current_object(),
            alerta=alerta,
            item=item,
            destinatarios=destinatarios
        )
        
        if resultado:
            print(f"✅ Notificaciones de alerta enviadas a {len(destinatarios)} usuario(s)")
        else:
            print("❌ Error al enviar notificaciones de alerta")
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error al enviar notificaciones de alerta: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    

# ====================================
# API: NOTIFICACIONES DE ALERTAS
# ====================================

# ====================================
# API: NOTIFICACIONES DE ALERTAS
# ====================================

@bp.route('/api/alertas/nuevas')
@login_required
def api_alertas_nuevas():
    """
    API: Verificar si hay nuevas alertas críticas para el usuario actual
    Usado para notificaciones en tiempo real con sonido
    """
    try:
        # Obtener la última vez que el usuario verificó (desde session)
        ultima_verificacion = session.get('ultima_verificacion_alertas')
        
        # Si no hay registro, usar hace 5 minutos
        if not ultima_verificacion:
            from datetime import timedelta
            ultima_verificacion = datetime.utcnow() - timedelta(minutes=5)
        else:
            ultima_verificacion = datetime.fromisoformat(ultima_verificacion)
        
        # Buscar alertas nuevas desde la última verificación
        alertas_nuevas = Alerta.query.filter(
            Alerta.estado == 'activa',
            Alerta.fecha_creacion > ultima_verificacion
        ).order_by(Alerta.fecha_creacion.desc()).all()
        
        # Actualizar última verificación
        session['ultima_verificacion_alertas'] = datetime.utcnow().isoformat()
        
        alertas_json = []
        for alerta in alertas_nuevas:
            item = Item.query.get(alerta.item_id)
            if item:
                alertas_json.append({
                    'id': alerta.id,
                    'tipo': alerta.tipo,
                    'nivel_urgencia': alerta.nivel_urgencia,
                    'mensaje': alerta.mensaje,
                    'item_codigo': item.codigo,
                    'item_nombre': item.nombre,
                    'fecha_creacion': alerta.fecha_creacion.strftime('%d/%m/%Y %H:%M:%S')
                })
        
        return jsonify({
            'success': True,
            'hay_nuevas': len(alertas_json) > 0,
            'cantidad': len(alertas_json),
            'alertas': alertas_json
        })
    
    except Exception as e:
        print(f"❌ Error en api_alertas_nuevas: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ====================================
# ENVIAR NOTIFICACIONES DE ALERTA
# ====================================

# ====================================
# ENVIAR NOTIFICACIONES DE ALERTA
# ====================================

def enviar_notificaciones_alerta_critica(alerta):
    """
    Envía notificaciones por email a técnicos y jefes TI cuando se genera una alerta crítica
    
    Args:
        alerta: Objeto Alerta recién creado
    """
    try:
        # Obtener el item relacionado
        item = Item.query.get(alerta.item_id)
        if not item:
            print("⚠️ No se encontró el item para la alerta")
            return False
        
        # ✅ OBTENER CORREOS DE TÉCNICOS Y JEFES TI
        usuarios_notificar = Usuario.query.filter(
            Usuario.rol.in_(['tecnico', 'jefe_ti'])
        ).all()
        
        destinatarios = []
        for usuario in usuarios_notificar:
            if usuario.persona and usuario.persona.correo:
                destinatarios.append(usuario.persona.correo)
                print(f"📧 Agregando destinatario: {usuario.persona.nombres} ({usuario.persona.correo})")
        
        if not destinatarios:
            print("⚠️ No hay destinatarios con correo registrado")
            return False
        
        # ✅ ENVIAR NOTIFICACIÓN
        from app.email_service import enviar_notificacion_alerta_critica
        
        resultado = enviar_notificacion_alerta_critica(
            app=current_app._get_current_object(),
            alerta=alerta,
            item=item,
            destinatarios=destinatarios
        )
        
        if resultado:
            print(f"✅ Notificaciones de alerta enviadas a {len(destinatarios)} usuario(s)")
        else:
            print("❌ Error al enviar notificaciones de alerta")
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error al enviar notificaciones de alerta: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@bp.route('/admin/generar-metricas-ahora', methods=['POST'])
@login_required
def admin_generar_metricas_ahora():
    """Ejecutar generación de métricas MANUALMENTE (solo para testing)"""
    
    if session.get('rol') not in ['jefe_ti', 'gerente']:
        flash('No autorizado', 'danger')
        return redirect(url_for('main.dashboard'))
    
    from app.scheduler_service import generar_metricas_automaticas_mes_anterior
    
    resultado = generar_metricas_automaticas_mes_anterior()
    
    if resultado['success']:
        flash(f'✅ Métricas generadas: {resultado["generadas"]} items del mes {resultado["mes"]}/{resultado["anio"]}', 'success')
    else:
        flash(f'❌ Error: {resultado.get("error")}', 'danger')
    
    return redirect(url_for('main.metricas_lista'))

@bp.route('/api/servicios-afectados')
def api_servicios_afectados():
    """API para obtener catálogo de servicios afectados"""
    if 'user_id' not in session:
        return {'error': 'No autenticado'}, 401
    
    from app.models import ServicioAfectado
    
    servicios = ServicioAfectado.query.filter_by(activo=True).order_by(ServicioAfectado.nombre).all()
    
    servicios_json = []
    for servicio in servicios:
        servicios_json.append({
            'id': servicio.id,
            'nombre': servicio.nombre,
            'descripcion': servicio.descripcion,
            'icono': servicio.icono
        })
    
    return {
        'success': True,
        'servicios': servicios_json
    }

# ====================================
# GENERAR PDF DE PRODUCTOS
# ====================================

@bp.route('/productos/pdf')
@login_required
def productos_pdf():
    """Generar PDF de lista de productos"""
    from pdf_generator import generar_pdf_productos
    
    # Obtener filtros (igual que en la lista)
    buscar = request.args.get('buscar', '')
    estado = request.args.get('estado', '')
    
    # Query con filtros
    query = Item.query.filter_by(tipo='producto')
    
    if buscar:
        query = query.filter(
            (Item.nombre.contains(buscar)) | 
            (Item.codigo.contains(buscar)) |
            (Item.categoria.contains(buscar))
        )
    
    if estado:
        query = query.filter_by(estado=estado)
    
    productos = query.order_by(Item.codigo).all()
    
    # Generar PDF
    pdf_buffer = generar_pdf_productos(productos)
    
    # Nombre del archivo
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'productos_{timestamp}.pdf'
    
    # Enviar PDF
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=False,  # ✅ False = abrir en navegador
        download_name=filename
    )

@bp.route('/servicios/pdf')
@login_required
def servicios_pdf():
    """Generar PDF de lista de servicios"""
    from pdf_generator import generar_pdf_servicios
    
    # Obtener filtros (igual que en la lista)
    buscar = request.args.get('buscar', '')
    estado = request.args.get('estado', '')
    
    # Query con filtros
    query = Item.query.filter_by(tipo='servicio')
    
    if buscar:
        query = query.filter(
            (Item.nombre.contains(buscar)) | 
            (Item.codigo.contains(buscar)) |
            (Item.categoria.contains(buscar))
        )
    
    if estado:
        query = query.filter_by(estado=estado)
    
    servicios = query.order_by(Item.codigo).all()
    
    # Generar PDF
    pdf_buffer = generar_pdf_servicios(servicios)
    
    # Nombre del archivo
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'servicios_{timestamp}.pdf'
    
    # Enviar PDF
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=False,  # ✅ False = abrir en navegador
        download_name=filename
    )


# ====================================
# AGREGAR AL FINAL DE app/routes.py
# DESPUÉS DE LA RUTA servicios_pdf()
# ====================================

@bp.route('/api/historial/<int:item_id>/pdf')
@login_required
def historial_pdf(item_id):
    """Generar PDF del historial completo de reemplazos"""
    from pdf_generator import generar_pdf_historial_reemplazos
    
    try:
        # Obtener item actual
        item = Item.query.get_or_404(item_id)
        
        # Construir cadena anterior
        cadena_anterior = []
        item_temp = item
        contador = 0
        
        while item_temp.reemplaza_a_id and contador < 50:
            contador += 1
            item_ant = Item.query.get(item_temp.reemplaza_a_id)
            if not item_ant:
                break
            
            cadena_anterior.append({
                'id': item_ant.id,
                'codigo': item_ant.codigo,
                'nombre': item_ant.nombre,
                'tipo': item_ant.tipo,
                'categoria': item_ant.categoria,
                'estado': item_ant.estado,
                'responsable': item_ant.responsable,
                'fecha_creacion': item_ant.fecha_creacion.isoformat() if item_ant.fecha_creacion else None,
                'motivo_reemplazo': item_temp.motivo_reemplazo
            })
            
            item_temp = item_ant
        
        # Construir cadena posterior
        cadena_posterior = []
        item_temp = item
        contador = 0
        
        while contador < 50:
            contador += 1
            item_post = Item.query.filter_by(reemplaza_a_id=item_temp.id).first()
            if not item_post:
                break
            
            cadena_posterior.append({
                'id': item_post.id,
                'codigo': item_post.codigo,
                'nombre': item_post.nombre,
                'tipo': item_post.tipo,
                'categoria': item_post.categoria,
                'estado': item_post.estado,
                'responsable': item_post.responsable,
                'fecha_creacion': item_post.fecha_creacion.isoformat() if item_post.fecha_creacion else None,
                'motivo_reemplazo': item_post.motivo_reemplazo
            })
            
            item_temp = item_post
        
        # Item actual
        item_actual_dict = {
            'id': item.id,
            'codigo': item.codigo,
            'nombre': item.nombre,
            'tipo': item.tipo,
            'categoria': item.categoria,
            'estado': item.estado,
            'responsable': item.responsable,
            'fecha_creacion': item.fecha_creacion.isoformat() if item.fecha_creacion else None,
            'motivo_reemplazo': item.motivo_reemplazo
        }
        
        # Generar PDF
        pdf_buffer = generar_pdf_historial_reemplazos(item_actual_dict, cadena_anterior, cadena_posterior)
        
        # Nombre del archivo
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'historial_{item.codigo}_{timestamp}.pdf'
        
        # Enviar PDF
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,  # ✅ True = descargar automáticamente
            download_name=filename
        )
    
    except Exception as e:
        print(f"Error al generar PDF historial: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e)
        }, 500

    
# ✅ CORRECTO:
@bp.route('/alerta/<int:alerta_id>/incidencias', methods=['GET'])
@login_required
def alerta_incidencias(alerta_id):
    """Obtiene las incidencias asociadas a una alerta para resolverlas"""
    try:
        alerta = Alerta.query.get_or_404(alerta_id)
        item = Item.query.get_or_404(alerta.item_id)
        
        # ✅ OBTENER LÍMITE SLA DESDE LA TABLA SLA
        sla = SLA.query.filter_by(item_id=item.id).first()
        
        if item.tipo == 'producto':
            if not sla:
                limite_sla = 2  # Default para productos sin SLA
            else:
                limite_sla = (sla.fallas_criticas_permitidas or 0) + (sla.fallas_menores_permitidas or 0)
        else:  # servicio
            limite_sla = 2  # Límite estándar para servicios
        
        if limite_sla == 0:
            limite_sla = 2  # Mínimo por seguridad
        
        # Obtener incidencias del mes actual
        mes_actual = datetime.now().month
        anio_actual = datetime.now().year
        
        # Incidencias activas (no resueltas)
        incidencias_activas = Incidencia.query.filter(
            Incidencia.item_id == item.id,
            Incidencia.estado != 'resuelta',
            db.func.extract('month', Incidencia.fecha_incidencia) == mes_actual,
            db.func.extract('year', Incidencia.fecha_incidencia) == anio_actual
        ).order_by(Incidencia.fecha_incidencia.desc()).all()
        
        # Verificar cuáles ya están resueltas en esta alerta
        incidencias_resueltas_ids = db.session.query(AlertaIncidencia.incidencia_id).filter(
            AlertaIncidencia.alerta_id == alerta_id
        ).all()
        resueltas_ids = [r[0] for r in incidencias_resueltas_ids]
        
        # Preparar datos para el frontend
        incidencias_data = []
        for inc in incidencias_activas:
            incidencias_data.append({
                'id': inc.id,
                'titulo': inc.titulo,
                'descripcion': inc.descripcion or 'Sin descripción',
                'tipo': inc.tipo or 'No especificado',
                'severidad': inc.severidad or 'media',
                'fecha_incidencia': inc.fecha_incidencia.strftime('%d/%m/%Y %H:%M'),
                'usuarios_afectados': inc.usuarios_afectados or 0,
                'ya_resuelta': inc.id in resueltas_ids
            })
        
        # Contar total de incidencias resueltas en esta alerta
        total_resueltas = len(resueltas_ids)
        
        return jsonify({
            'success': True,
            'incidencias': incidencias_data,
            'item': {
                'codigo': item.codigo,
                'nombre': item.nombre,
                'limite_sla': limite_sla  # ✅ Ahora viene del SLA
            },
            'total_activas': len(incidencias_activas),
            'total_resueltas': total_resueltas
        })
        
    except Exception as e:
        print(f"❌ Error en alerta_incidencias: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@bp.route('/metricas/recalcular/<int:metrica_id>', methods=['POST'])
@login_required
def metrica_recalcular(metrica_id):
    """Recalcular una métrica existente basándose en incidencias actuales"""
    
    if session.get('rol') not in ['jefe_ti', 'gerente']:
        return {'success': False, 'error': 'No autorizado'}, 403
    
    try:
        metrica = Metrica.query.get_or_404(metrica_id)
        
        # Contar incidencias ACTIVAS del mes de esta métrica
        incidencias_activas = Incidencia.query.filter(
            Incidencia.item_id == metrica.item_id,
            Incidencia.estado != 'resuelta',
            db.func.extract('month', Incidencia.fecha_incidencia) == metrica.mes,
            db.func.extract('year', Incidencia.fecha_incidencia) == metrica.anio
        ).count()
        
        # Actualizar incidencias
        metrica.incidencias = incidencias_activas
        
        # ✅ CÁLCULO CORRECTO DEL SEMÁFORO
        if incidencias_activas == 0:
            porcentaje = 100.0
            semaforo = 'verde'
        elif incidencias_activas <= 2:
            # Amarillo: 1-2 incidencias
            porcentaje = 100.0 - (incidencias_activas * 7.5)  # 92.5% con 1, 85% con 2
            semaforo = 'amarillo'
        else:
            # Rojo: 3+ incidencias
            porcentaje = max(0, 85.0 - ((incidencias_activas - 2) * 15))  # 70% con 3, 55% con 4...
            semaforo = 'rojo'
        
        # Actualizar métrica
        metrica.porcentaje_cumplimiento = round(porcentaje, 2)
        metrica.semaforo = semaforo
        
        db.session.commit()
        
        # ✅ NUEVO: GENERAR ALERTAS SI CORRESPONDE
        # Solo generar alertas si es el mes actual
        from datetime import datetime
        mes_actual = datetime.now().month
        anio_actual = datetime.now().year
        
        if metrica.mes == mes_actual and metrica.anio == anio_actual:
            # Verificar si sobrepasa SLA
            generar_alerta_si_sobrepasa_sla(metrica.item_id)
            
            # Si ya no sobrepasa, resolver alertas
            if semaforo != 'rojo':
                resolver_alertas_si_vuelve_normal(metrica.item_id)
        
        return {
            'success': True,
            'incidencias': incidencias_activas,
            'semaforo': semaforo,
            'porcentaje_cumplimiento': metrica.porcentaje_cumplimiento
        }
    
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}, 500
    

def resolver_alertas_si_vuelve_normal(item_id):
    """
    Resuelve automáticamente alertas de sobrepaso SLA si el item vuelve a estado normal
    """
    try:
        # Obtener mes y año actual
        mes_actual = datetime.now().month
        anio_actual = datetime.now().year
        
        # Obtener item y SLA
        item = Item.query.get(item_id)
        if not item:
            return
        
        sla = SLA.query.filter_by(item_id=item_id).first()
        
        # Calcular límite según tipo
        if item.tipo == 'producto':
            if not sla:
                limite_sla = 2
            else:
                limite_sla = (sla.fallas_criticas_permitidas or 0) + (sla.fallas_menores_permitidas or 0)
        else:
            limite_sla = 2
        
        if limite_sla == 0:
            limite_sla = 2
        
        # Contar incidencias activas del mes
        incidencias_activas = Incidencia.query.filter(
            Incidencia.item_id == item_id,
            Incidencia.estado != 'resuelta',
            db.func.extract('month', Incidencia.fecha_incidencia) == mes_actual,
            db.func.extract('year', Incidencia.fecha_incidencia) == anio_actual
        ).count()
        
        # Si ya NO sobrepasa, resolver alertas activas de sobrepaso SLA
        if incidencias_activas <= limite_sla:
            alertas_activas = Alerta.query.filter_by(
                item_id=item_id,
                tipo='sobrepaso_sla',
                estado='activa'
            ).all()
            
            for alerta in alertas_activas:
                alerta.estado = 'resuelta'
                alerta.fecha_resolucion = datetime.utcnow()
                print(f"✅ Alerta #{alerta.id} resuelta automáticamente (volvió a límite normal)")
            
            if alertas_activas:
                db.session.commit()
    
    except Exception as e:
        print(f"❌ Error en resolver_alertas_si_vuelve_normal: {str(e)}")
        db.session.rollback()
    
@bp.route('/reportes')
@login_required
def reportes():
    """Vista principal de reportes"""
    return render_template('reportes.html')


@bp.route('/api/reportes/datos')
@login_required
def api_reportes_datos():
    """API: Obtener datos para reporte"""
    try:
        # Obtener mes y año actual
        mes_actual = datetime.now().month
        anio_actual = datetime.now().year
        
        # Items activos con sus métricas e incidencias
        items_reemplazados = db.session.query(Item.reemplaza_a_id).filter(
            Item.reemplaza_a_id.isnot(None)
        ).subquery()
        
        items = Item.query.filter(
            Item.estado == 'aprobado',
            Item.estado_operativo == 'activo',
            ~Item.id.in_(items_reemplazados)
        ).all()
        
        datos = []
        for item in items:
            # Métrica del mes actual
            metrica = Metrica.query.filter_by(
                item_id=item.id,
                mes=mes_actual,
                anio=anio_actual
            ).first()
            
            # Contar incidencias activas y resueltas
            incidencias_activas = Incidencia.query.filter_by(
                item_id=item.id,
                estado='abierta'
            ).count()
            
            incidencias_resueltas = Incidencia.query.filter_by(
                item_id=item.id,
                estado='resuelta'
            ).count()
            
            datos.append({
                'id': item.id,
                'codigo': item.codigo,
                'nombre': item.nombre,
                'tipo': item.tipo,
                'categoria': item.categoria or 'Sin categoría',
                'semaforo_sla': metrica.semaforo if metrica else 'verde',
                'cumplimiento_sla': metrica.porcentaje_cumplimiento if metrica else 100,
                'incidencias_activas': incidencias_activas,
                'incidencias_resueltas': incidencias_resueltas
            })
        
        return jsonify({'success': True, 'items': datos})
    
    except Exception as e:
        print(f"Error en api_reportes_datos: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/reportes/incidencias/<int:item_id>')
@login_required
def api_reportes_incidencias(item_id):
    """API: Obtener incidencias de un item"""
    try:
        # Incidencias activas
        activas = Incidencia.query.filter_by(
            item_id=item_id
        ).filter(
            Incidencia.estado != 'resuelta'
        ).order_by(Incidencia.fecha_incidencia.desc()).all()
        
        # Incidencias resueltas
        resueltas = Incidencia.query.filter_by(
            item_id=item_id,
            estado='resuelta'
        ).order_by(Incidencia.fecha_resolucion.desc()).all()
        
        def serializar_incidencia(inc):
            return {
                'id': inc.id,
                'titulo': inc.titulo,
                'descripcion': inc.descripcion,
                'tipo': inc.tipo or 'No especificado',
                'severidad': inc.severidad or 'media',
                'usuarios_afectados': inc.usuarios_afectados or 0,
                'fecha_incidencia': inc.fecha_incidencia.strftime('%d/%m/%Y %H:%M') if inc.fecha_incidencia else '-',
                'fecha_resolucion': inc.fecha_resolucion.strftime('%d/%m/%Y %H:%M') if inc.fecha_resolucion else None
            }
        
        return jsonify({
            'success': True,
            'activas': [serializar_incidencia(i) for i in activas],
            'resueltas': [serializar_incidencia(i) for i in resueltas]
        })
    
    except Exception as e:
        print(f"Error en api_reportes_incidencias: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# ====================================
# EDITAR USUARIO
# ====================================

@bp.route('/usuarios/<int:id>/editar', methods=['GET', 'POST'])
def usuario_editar(id):
    """Editar usuario existente con su información personal"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    # Solo Jefe TI y Gerente pueden editar usuarios
    if session.get('rol') not in ['jefe_ti', 'gerente']:
        flash('No tienes permisos para editar usuarios', 'danger')
        return redirect(url_for('main.dashboard'))
    
    usuario = Usuario.query.get_or_404(id)
    persona = Persona.query.filter_by(usuario_id=id).first()
    
    if request.method == 'POST':
        # Datos de usuario
        nuevo_username = request.form.get('username')
        nueva_password = request.form.get('password')
        nuevo_rol = request.form.get('rol')
        
        # Datos personales
        nuevos_nombres = request.form.get('nombres')
        nuevos_apellidos = request.form.get('apellidos')
        nuevo_telefono = request.form.get('telefono')
        nuevo_correo = request.form.get('correo')
        
        # Validaciones
        if not nuevo_username or not nuevo_rol or not nuevos_nombres or not nuevos_apellidos:
            flash('Todos los campos obligatorios deben ser completados', 'warning')
            return redirect(url_for('main.usuario_editar', id=id))
        
        # Verificar si el username ya existe (excepto el actual)
        existe_usuario = Usuario.query.filter(
            Usuario.username == nuevo_username,
            Usuario.id != id
        ).first()
        
        if existe_usuario:
            flash(f'El nombre de usuario "{nuevo_username}" ya está registrado', 'warning')
            return redirect(url_for('main.usuario_editar', id=id))
        
        # Verificar si el correo ya existe (excepto el actual)
        if nuevo_correo:
            existe_correo = Persona.query.filter(
                Persona.correo == nuevo_correo,
                Persona.usuario_id != id
            ).first()
            
            if existe_correo:
                flash(f'El correo "{nuevo_correo}" ya está registrado', 'warning')
                return redirect(url_for('main.usuario_editar', id=id))
        
        try:
            # Actualizar usuario
            cambios_usuario = []
            
            if usuario.username != nuevo_username:
                cambios_usuario.append(f'Username: {usuario.username} → {nuevo_username}')
                usuario.username = nuevo_username
            
            if usuario.rol != nuevo_rol:
                cambios_usuario.append(f'Rol: {usuario.rol} → {nuevo_rol}')
                usuario.rol = nuevo_rol
            
            # Actualizar contraseña solo si se proporcionó una nueva
            if nueva_password and nueva_password.strip():
                if len(nueva_password) < 6:
                    flash('La contraseña debe tener al menos 6 caracteres', 'warning')
                    return redirect(url_for('main.usuario_editar', id=id))
                
                usuario.set_password(nueva_password)
                cambios_usuario.append('Contraseña actualizada')
            
            # Actualizar o crear persona
            if persona:
                cambios_persona = []
                
                if persona.nombres != nuevos_nombres:
                    cambios_persona.append(f'Nombres: {persona.nombres} → {nuevos_nombres}')
                    persona.nombres = nuevos_nombres
                
                if persona.apellidos != nuevos_apellidos:
                    cambios_persona.append(f'Apellidos: {persona.apellidos} → {nuevos_apellidos}')
                    persona.apellidos = nuevos_apellidos
                
                if persona.telefono != nuevo_telefono:
                    cambios_persona.append(f'Teléfono: {persona.telefono or "Sin teléfono"} → {nuevo_telefono or "Sin teléfono"}')
                    persona.telefono = nuevo_telefono
                
                if persona.correo != nuevo_correo:
                    cambios_persona.append(f'Correo: {persona.correo or "Sin correo"} → {nuevo_correo or "Sin correo"}')
                    persona.correo = nuevo_correo
                
            else:
                # Crear persona si no existe
                persona = Persona(
                    usuario_id=id,
                    nombres=nuevos_nombres,
                    apellidos=nuevos_apellidos,
                    telefono=nuevo_telefono,
                    correo=nuevo_correo
                )
                db.session.add(persona)
                cambios_persona = ['Información personal creada']
            
            db.session.commit()
            
            # Mensaje de éxito detallado
            total_cambios = len(cambios_usuario) + len(cambios_persona)
            
            if total_cambios > 0:
                flash(f'✅ Usuario "{nuevo_username}" actualizado exitosamente. {total_cambios} campo(s) modificado(s).', 'success')
            else:
                flash('ℹ️ No se detectaron cambios en el usuario', 'info')
            
            return redirect(url_for('main.usuario_detalle', id=id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Error al actualizar usuario: {str(e)}', 'danger')
            return redirect(url_for('main.usuario_editar', id=id))
    
    # GET - Mostrar formulario con datos actuales
    return render_template('usuarios_editar.html', usuario=usuario, persona=persona)


# En routes.py

@bp.route('/api/tecnicos-activos')
def api_tecnicos_activos():
    """API: Obtener técnicos con correo registrado"""
    if 'user_id' not in session:
        return {'error': 'No autenticado'}, 401
    
    try:
        # Obtener todos los técnicos con datos personales y correo
        tecnicos = db.session.query(
            Usuario.id,
            Persona.nombres,
            Persona.apellidos,
            Persona.correo
        ).join(Persona, Usuario.id == Persona.usuario_id).filter(
            Usuario.rol == 'tecnico',
            Persona.correo.isnot(None),
            Persona.correo != ''
        ).all()
        
        tecnicos_json = []
        for tec in tecnicos:
            tecnicos_json.append({
                'id': tec.id,
                'nombres': tec.nombres,
                'apellidos': tec.apellidos,
                'correo': tec.correo
            })
        
        return {
            'success': True,
            'tecnicos': tecnicos_json
        }
    
    except Exception as e:
        print(f"Error en api_tecnicos_activos: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }, 500