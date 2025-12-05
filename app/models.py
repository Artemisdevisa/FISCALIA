from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(db.Model):
    __tablename__ = 'usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), nullable=False)  # 'tecnico', 'jefe_ti', 'gerente'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class Persona(db.Model):
    __tablename__ = 'persona'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), unique=True, nullable=False)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(15))
    correo = db.Column(db.String(100))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación con Usuario
    usuario = db.relationship('Usuario', backref=db.backref('persona', uselist=False))

# TABLA: Productos/Servicios
class Item(db.Model):
    __tablename__ = 'item'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'producto', 'servicio'
    categoria = db.Column(db.String(50))
    definicion = db.Column(db.Text)
    proposito = db.Column(db.Text)
    estado_actual = db.Column(db.Text)
    estado_objetivo = db.Column(db.Text)
    beneficio = db.Column(db.Text)
    caso_uso = db.Column(db.Text)
    responsable = db.Column(db.String(100))
    dependencias = db.Column(db.Text)
    
    estado = db.Column(db.String(20), default='propuesto')
    estado_operativo = db.Column(db.String(20), default='activo')
    
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    creado_por = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    
    reemplaza_a_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=True)
    motivo_reemplazo = db.Column(db.Text, nullable=True)
    fecha_reemplazo = db.Column(db.DateTime, nullable=True)
    
    # Item que este item reemplaza
    reemplaza_a = db.relationship(
        'Item',
        remote_side=[id],
        backref=db.backref('reemplazado_por', uselist=False),
        foreign_keys=[reemplaza_a_id]
    )
    
    # Relaciones existentes
    versiones = db.relationship('Version', backref='item', lazy=True)
    sla = db.relationship('SLA', backref='item', uselist=False)
    metricas = db.relationship('Metrica', backref='item', lazy=True)

    @property
    def limite_sla(self):
        """Calcula el límite SLA del item basado en su tipo y configuración SLA"""
        sla_obj = SLA.query.filter_by(item_id=self.id).first()
        
        if self.tipo == 'producto':
            if not sla_obj:
                return 2  # Default para productos sin SLA
            limite = (sla_obj.fallas_criticas_permitidas or 0) + (sla_obj.fallas_menores_permitidas or 0)
            return limite if limite > 0 else 2
        else:  # servicio
            return 2  # Límite estándar para servicios

# TABLA: SLA (Niveles de Servicio)
class SLA(db.Model):
    __tablename__ = 'sla'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    
    # Para servicios
    disponibilidad = db.Column(db.Float)
    velocidad_min = db.Column(db.Integer)
    latencia_max = db.Column(db.Integer)
    tiempo_respuesta = db.Column(db.Integer)
    tiempo_resolucion = db.Column(db.Integer)
    capacidad_usuarios = db.Column(db.Integer)
    horario = db.Column(db.String(50))
    
    # Para productos (especificaciones técnicas)
    fallas_criticas_permitidas = db.Column(db.Integer)
    fallas_menores_permitidas = db.Column(db.Integer)
    disponibilidad_esperada = db.Column(db.Float)
    tiempo_max_inactividad = db.Column(db.Float)
    vida_util = db.Column(db.Integer)
    mantenimiento_preventivo = db.Column(db.String(50))
    caracteristicas = db.Column(db.Text)
    
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

# TABLA: Versiones (Historial)
class Version(db.Model):
    __tablename__ = 'version'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    numero_version = db.Column(db.Integer, nullable=False)
    campo_modificado = db.Column(db.String(100))
    valor_anterior = db.Column(db.Text)
    valor_nuevo = db.Column(db.Text)
    razon_cambio = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))

class Aprobacion(db.Model):
    __tablename__ = 'aprobacion'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    aprobador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    estado = db.Column(db.String(20))
    comentarios = db.Column(db.Text)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_respuesta = db.Column(db.DateTime)

# TABLA: Métricas (Mediciones mensuales)
class Metrica(db.Model):
    __tablename__ = 'metrica'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    
    # Valores medidos
    disponibilidad_real = db.Column(db.Float)
    velocidad_real = db.Column(db.Integer)
    latencia_real = db.Column(db.Integer)
    tiempo_respuesta_real = db.Column(db.Integer)
    incidencias = db.Column(db.Integer)
    observaciones = db.Column(db.Text)
    
    # Estado
    semaforo = db.Column(db.String(10))
    porcentaje_cumplimiento = db.Column(db.Float)
    
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    registrado_por = db.Column(db.Integer, db.ForeignKey('usuario.id'))

class Alerta(db.Model):
    __tablename__ = 'alerta'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    nivel_urgencia = db.Column(db.String(20), default='media')
    mensaje = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(20), default='activa')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_resolucion = db.Column(db.DateTime)
    resuelto_por = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    incidencias_pendientes = db.Column(db.Integer, default=0)
    incidencias_resueltas_count = db.Column(db.Integer, default=0)
    
    # Relaciones
    item = db.relationship('Item', backref='alertas', foreign_keys=[item_id])
    usuario_resolucion = db.relationship('Usuario', foreign_keys=[resuelto_por])

    def actualizar_estado_incidencias(self):
        self.incidencias_resueltas_count = self.incidencias_resueltas.count()
        
        # Si todas las incidencias fueron resueltas, resolver la alerta automáticamente
        if self.incidencias_resueltas_count >= self.incidencias_pendientes and self.incidencias_pendientes > 0:
            if self.estado == 'activa':
                self.estado = 'resuelta'
                self.fecha_resolucion = datetime.utcnow()
                db.session.commit()

# ✅ NUEVA TABLA: Servicios Afectados (Catálogo)
class ServicioAfectado(db.Model):
    __tablename__ = 'servicio_afectado'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.String(200))
    icono = db.Column(db.String(50))  # Nombre del icono Font Awesome
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

class Incidencia(db.Model):
    __tablename__ = 'incidencia'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    
    # Información temporal
    fecha_incidencia = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_resolucion = db.Column(db.DateTime)
    tiempo_resolucion = db.Column(db.Integer)  # En minutos
    
    # Clasificación
    tipo = db.Column(db.String(50))  # 'critica', 'mayor', 'menor'
    severidad = db.Column(db.String(20))  # 'alta', 'media', 'baja'
    estado = db.Column(db.String(20), default='abierta')  # 'abierta', 'en_proceso', 'resuelta'
    
    # Descripción
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    causa_raiz = db.Column(db.Text)
    solucion_aplicada = db.Column(db.Text)
    
    # Impacto
    usuarios_afectados = db.Column(db.Integer)
    servicios_afectados = db.Column(db.String(500))
    
    # Seguimiento
    registrado_por = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    resuelto_por = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    
    # ✅ NUEVO: Campos de resolución
    imagen_resolucion = db.Column(db.String(500))  # Ruta del archivo
    comentario_resolucion = db.Column(db.Text)  # Comentario del técnico
    
    # Relaciones
    item = db.relationship('Item', backref='incidencias', foreign_keys=[item_id])
    registrador = db.relationship('Usuario', foreign_keys=[registrado_por], backref='incidencias_registradas')
    solucionador = db.relationship('Usuario', foreign_keys=[resuelto_por], backref='incidencias_resueltas')
    

class AlertaIncidencia(db.Model):
    """Tabla de relación entre alertas e incidencias resueltas"""
    __tablename__ = 'alerta_incidencia'
    
    id = db.Column(db.Integer, primary_key=True)
    alerta_id = db.Column(db.Integer, db.ForeignKey('alerta.id'), nullable=False)
    incidencia_id = db.Column(db.Integer, db.ForeignKey('incidencia.id'), nullable=False)
    fecha_resolucion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    alerta = db.relationship('Alerta', backref=db.backref('incidencias_resueltas', lazy='dynamic'))
    incidencia = db.relationship('Incidencia', backref=db.backref('alertas_relacionadas', lazy='dynamic'))