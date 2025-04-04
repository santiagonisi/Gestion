import os
import sqlite3
from flask import Flask, render_template, request, redirect, send_from_directory, url_for

app = Flask(__name__)

# Configuración de la carpeta de subida
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Asegura que la carpeta exista
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ruta para servir los archivos subidos
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    print(f"Intentando servir el archivo: {filename}")
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Conectar a la base de datos
def obtener_conexion():
    conn = sqlite3.connect('empresa.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row  
    return conn

# Crear las tablas si no existen
def crear_tablas():
    conn = obtener_conexion()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS centros_costos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        departamento TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        razonsocial TEXT,
        contacto TEXT,
        cuit TEXT,
        rubro TEXT,
        ubicacion TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        categoria TEXT,
        cantidad INTEGER DEFAULT 0
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS proveedores_productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proveedor_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        precio REAL NOT NULL,
        fecha TEXT NOT NULL,
        centro_costo_id INTEGER NOT NULL,
        pdf_path TEXT,
        FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),
        FOREIGN KEY (producto_id) REFERENCES productos(id),
        FOREIGN KEY (centro_costo_id) REFERENCES centros_costos(id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS presupuestos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proveedor_id INTEGER NOT NULL,
        producto_nombre TEXT NOT NULL,
        precio REAL NOT NULL,
        moneda TEXT,
        fecha DATE NOT NULL,
        centro_costo_id TEXT NOT NULL,
        pdf_path TEXT,
        FOREIGN KEY (proveedor_id) REFERENCES proveedores (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Insertar centros de costos si no existen
def insertar_centros_costos():
    conn = obtener_conexion()
    cursor = conn.cursor()

    centros_costos = [
        ('Sector Obra', 'Obra'),
        ('Sector Administración', 'Administración'),
        ('Sector Oficina Técnica', 'Oficina Técnica'),
        ('Sector Laboratorio', 'Laboratorio'),
        ('Sector Mantenimiento', 'Mantenimiento'),
        ('Sector Seguridad y Medio Ambiente', 'Seguridad y Medio Ambiente'),
        ('Planta Ramallo', 'Planta'),
        ('Planta Baradero', 'Planta'),
        ('Planta Hormigón', 'Planta')
    ]

    for nombre, departamento in centros_costos:
        cursor.execute('SELECT id FROM centros_costos WHERE nombre = ?', (nombre,))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO centros_costos (nombre, departamento) VALUES (?, ?)', (nombre, departamento))

    conn.commit()
    conn.close()

# Página principal (Presupuestos)
@app.route('/')
@app.route('/presupuestos', methods=['GET', 'POST'])
def presupuestos():
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    # Obtener el término de búsqueda si existe
    search_query = request.args.get('search', '').strip()
    
    if request.method == 'POST':
        # Obtener los datos del formulario
        proveedor_id = request.form['proveedor_id']
        producto_nombre = request.form['producto_nombre']
        precio = request.form['precio'].replace(',', '.')  # Reemplazar ',' por '.'
        moneda = request.form['moneda']  # Obtener la moneda seleccionada
        fecha = request.form['fecha']
        centro_costo_id = request.form['centro_costo_id']
        
        # Manejar el archivo PDF
        archivo_pdf = request.files.get('archivo_pdf')
        pdf_path = None
        if archivo_pdf:
            filename = f"{producto_nombre}_{archivo_pdf.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            archivo_pdf.save(filepath)
            pdf_path = filename  # Guardar solo el nombre del archivo en la base de datos
            print(f"Archivo PDF guardado en: {filepath}")
        
        # Insertar el presupuesto en la tabla presupuestos
        cursor.execute('''
            INSERT INTO presupuestos (proveedor_id, producto_nombre, precio, moneda, fecha, centro_costo_id, pdf_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (proveedor_id, producto_nombre, precio, moneda, fecha, centro_costo_id, pdf_path))
        conn.commit()
        print(f"Insertando en la base de datos: proveedor_id={proveedor_id}, producto_nombre={producto_nombre}, pdf_path={pdf_path}")
    
    # Filtrar presupuestos si hay un término de búsqueda
    if search_query:
        cursor.execute('''
            SELECT pr.id, p.nombre AS proveedor, pr.producto_nombre, pr.precio, pr.moneda, pr.fecha, cc.nombre AS centro_costo, pr.pdf_path
            FROM presupuestos pr
            JOIN proveedores p ON pr.proveedor_id = p.id
            JOIN centros_costos cc ON pr.centro_costo_id = cc.id
            WHERE p.nombre LIKE ? OR pr.producto_nombre LIKE ?
        ''', (f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute('''
            SELECT pr.id, p.nombre AS proveedor, pr.producto_nombre, pr.precio, pr.moneda, pr.fecha, cc.nombre AS centro_costo, pr.pdf_path
            FROM presupuestos pr
            JOIN proveedores p ON pr.proveedor_id = p.id
            JOIN centros_costos cc ON pr.centro_costo_id = cc.id
        ''')
    
    # Obtener los presupuestos para mostrar en la tabla
    presupuestos = cursor.fetchall()
    print(f"Presupuestos cargados: {presupuestos}")
    
    # Obtener los proveedores para el menú desplegable
    cursor.execute('SELECT id, nombre FROM proveedores')
    proveedores = cursor.fetchall()
    
    # Obtener los centros de costos para el menú desplegable
    cursor.execute('SELECT id, nombre FROM centros_costos')
    centros_costos = cursor.fetchall()
    
    conn.close()
    return render_template('presupuestos.html', presupuestos=presupuestos, proveedores=proveedores, centros_costos=centros_costos, search_query=search_query)

# Página de proveedores
@app.route('/proveedores', methods=['GET', 'POST'])
def proveedores():
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        razonsocial = request.form['razonsocial']
        contacto = request.form['contacto']
        cuit = request.form['cuit']
        rubro = request.form['rubro']
        ubicacion = request.form['ubicacion']
        
        cursor.execute('INSERT INTO proveedores (nombre, razonsocial, contacto, cuit, rubro, ubicacion) VALUES (?, ?, ?, ?, ?, ?)',
                       (nombre, razonsocial, contacto, cuit, rubro, ubicacion))
        conn.commit()
        return redirect(url_for('proveedores'))
    
    cursor.execute('SELECT * FROM proveedores')
    proveedores = cursor.fetchall()
    
    conn.close()
    return render_template('proveedores.html', proveedores=proveedores)

@app.route('/eliminar_proveedor/<int:proveedor_id>', methods=['POST'])
def eliminar_proveedor(proveedor_id):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM proveedores WHERE id = ?', (proveedor_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('proveedores'))

@app.route('/eliminar_presupuesto/<int:presupuesto_id>', methods=['POST'])
def eliminar_presupuesto(presupuesto_id):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM presupuestos WHERE id = ?', (presupuesto_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('presupuestos'))

if __name__ == '__main__':
    crear_tablas()
    insertar_centros_costos()
    app.run(debug=True)