import sqlite3

#base de datos
db_name = 'empresa.db' 
try:
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    print(f"Conectado a la base de datos: {db_name}")
except Exception as e:
    print(f"Error al conectar a la base de datos: {e}")
    exit()

#verifica si 'presupuestos' existe
try:
    cursor.execute("PRAGMA table_info(presupuestos);")
    columns = cursor.fetchall()
    if not columns:
        print("La tabla 'presupuestos' no existe en la base de datos.")
        exit()
    else:
        print("La tabla 'presupuestos' existe.")
except Exception as e:
    print(f"Error al verificar la tabla 'presupuestos': {e}")
    exit()

#verifica si 'pdf_path' existe
column_names = [column[1] for column in columns]
if 'pdf_path' not in column_names:
    #agrega tabla pdf_path
    try:
        cursor.execute('ALTER TABLE presupuestos ADD COLUMN pdf_path TEXT;')
        print("Columna 'pdf_path' agregada correctamente.")
    except Exception as e:
        print(f"Error al agregar la columna 'pdf_path': {e}")
else:
    print("La columna 'pdf_path' ya existe en la tabla 'presupuestos'.")

#confirmacion
conn.commit()
conn.close()