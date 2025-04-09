import sqlite3

# Conexión a la base de datos
db_name = 'empresa.db'
conn = sqlite3.connect(db_name)
cursor = conn.cursor()

# Renombrar la tabla original
cursor.execute("ALTER TABLE proveedores RENAME TO proveedores_backup;")

# Crear la nueva tabla sin la columna 'nombre'
cursor.execute('''
CREATE TABLE proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    razonsocial TEXT,
    contacto TEXT,
    cuit TEXT,
    rubro TEXT,
    ubicacion TEXT,
    descripcion TEXT
);
''')

# Copiar los datos de la tabla antigua a la nueva
cursor.execute('''
INSERT INTO proveedores (id, razonsocial, contacto, cuit, rubro, ubicacion, descripcion)
SELECT id, razonsocial, contacto, cuit, rubro, ubicacion, descripcion
FROM proveedores_backup;
''')

# Eliminar la tabla antigua
cursor.execute("DROP TABLE proveedores_backup;")

print("La columna 'nombre' ha sido eliminada correctamente.")

conn.commit()
conn.close()