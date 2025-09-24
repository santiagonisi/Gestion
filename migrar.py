import sqlite3

conn = sqlite3.connect('empresa.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE presupuestos ADD COLUMN precio_unitario TEXT;")
    print("Columna 'precio_unitario' agregada correctamente.")
except sqlite3.OperationalError as e:
    print("Error o la columna ya existe:", e)

conn.commit()
conn.close()