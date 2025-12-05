"""
Script de migración: Agregar campos de resolución a tabla incidencia
Ejecutar desde la raíz del proyecto
"""

from app import create_app, db
from sqlalchemy import text

def migrate():
    app = create_app()
    
    with app.app_context():
        print("🔄 Iniciando migración de base de datos...")
        print("📋 Agregando campos: imagen_resolucion y comentario_resolucion")
        print("-" * 60)
        
        try:
            # Verificar si las columnas ya existen
            result = db.session.execute(text("PRAGMA table_info(incidencia)"))
            columnas_existentes = [row[1] for row in result]
            
            columnas_agregadas = []
            
            # Agregar imagen_resolucion si no existe
            if 'imagen_resolucion' not in columnas_existentes:
                db.session.execute(text('ALTER TABLE incidencia ADD COLUMN imagen_resolucion VARCHAR(500)'))
                columnas_agregadas.append('imagen_resolucion')
                print("✅ Columna 'imagen_resolucion' agregada correctamente")
            else:
                print("ℹ️  Columna 'imagen_resolucion' ya existe")
            
            # Agregar comentario_resolucion si no existe
            if 'comentario_resolucion' not in columnas_existentes:
                db.session.execute(text('ALTER TABLE incidencia ADD COLUMN comentario_resolucion TEXT'))
                columnas_agregadas.append('comentario_resolucion')
                print("✅ Columna 'comentario_resolucion' agregada correctamente")
            else:
                print("ℹ️  Columna 'comentario_resolucion' ya existe")
            
            # Commit solo si se agregó algo
            if columnas_agregadas:
                db.session.commit()
                print("-" * 60)
                print(f"✅ Migración completada: {len(columnas_agregadas)} columna(s) agregada(s)")
            else:
                print("-" * 60)
                print("ℹ️  No se requirieron cambios - Base de datos actualizada")
            
            # Verificar estructura final
            print("\n📊 Estructura actual de la tabla 'incidencia':")
            result = db.session.execute(text("PRAGMA table_info(incidencia)"))
            for row in result:
                col_id, nombre, tipo, notnull, default, pk = row
                print(f"   - {nombre:<30} {tipo:<15} {'PK' if pk else ''}")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR durante la migración:")
            print(f"   {str(e)}")
            print("\n💡 Solución:")
            print("   - Verifica que el archivo models.py esté actualizado")
            print("   - Asegúrate de que la base de datos no esté en uso")
            return False
        
        return True

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 MIGRACIÓN DE BASE DE DATOS - INVENTECH")
    print("=" * 60)
    print()
    
    success = migrate()
    
    print()
    print("=" * 60)
    if success:
        print("✅ MIGRACIÓN EXITOSA")
        print("\n📁 No olvides crear la carpeta:")
        print("   mkdir -p app/static/resoluciones")
    else:
        print("❌ MIGRACIÓN FALLIDA")
    print("=" * 60)