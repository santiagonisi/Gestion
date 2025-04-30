import os
import sqlite3
from flask import Flask, render_template, request, redirect, send_from_directory, url_for

app = Flask(__name__)

# Configuración carpeta uploads
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Carpeta uploads
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Base de datos
def obtener_conexion():
    conn = sqlite3.connect('empresa.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row  
    return conn

# Tablas
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
        razonsocial TEXT,
        contacto TEXT,
        cuit TEXT,
        rubro TEXT,
        ubicacion TEXT,
        descripcion TEXT
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
        cotizacion_dolar REAL,
        FOREIGN KEY (proveedor_id) REFERENCES proveedores (id)
    )
    ''')

    conn.commit()
    conn.close()

# Migración para agregar columna cotización del dólar
def agregar_columna_cotizacion_dolar():
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE presupuestos ADD COLUMN cotizacion_dolar REAL")
    except sqlite3.OperationalError:
        pass  # La columna ya existe
    conn.commit()
    conn.close()

# Centro de costos
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

# Presupuestos/página principal
@app.route('/')
@app.route('/presupuestos', methods=['GET', 'POST'])
def presupuestos():
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    search_query = request.args.get('search', '').strip()
    
    if request.method == 'POST':
        proveedor_id = request.form['proveedor_id']
        productos = request.form.getlist('productos[]')  # Lista de productos
        precio = float(request.form['precio'].replace(',', '.'))
        moneda = request.form['moneda']
        fecha = request.form['fecha']
        centro_costo_id = request.form['centro_costo_id']
        
        # Manejar el campo cotizacion_dolar
        cotizacion_dolar = request.form.get('cotizacion_dolar', '').strip()
        if cotizacion_dolar:  # Si el campo no está vacío
            cotizacion_dolar = float(cotizacion_dolar.replace(',', '.'))
        else:
            cotizacion_dolar = None  # O un valor predeterminado, como 0.0
        
        pdf_file = request.files['archivo_pdf']

        pdf_path = None
        if pdf_file:
            pdf_filename = pdf_file.filename
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
            pdf_file.save(pdf_path)

        # Guardar cada producto como un registro separado
        for producto in productos:
            cursor.execute('''
                INSERT INTO presupuestos (proveedor_id, producto_nombre, precio, moneda, fecha, centro_costo_id, pdf_path, cotizacion_dolar)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (proveedor_id, producto, precio, moneda, fecha, centro_costo_id, pdf_path, cotizacion_dolar))
        
        conn.commit()
    
    # Consulta para mostrar presupuestos
    cursor.execute('''
        SELECT pr.id, p.razonsocial AS proveedor, pr.producto_nombre, pr.precio, pr.moneda, pr.fecha, cc.nombre AS centro_costo, pr.pdf_path, pr.cotizacion_dolar
        FROM presupuestos pr
        JOIN proveedores p ON pr.proveedor_id = p.id
        JOIN centros_costos cc ON pr.centro_costo_id = cc.id
    ''')
    presupuestos = cursor.fetchall()
    
    # Menú desplegable de proveedores
    cursor.execute('SELECT id, razonsocial FROM proveedores ORDER BY razonsocial ASC')
    proveedores = cursor.fetchall()
    
    # Menú desplegable de centros de costos
    cursor.execute('SELECT id, nombre FROM centros_costos')
    centros_costos = cursor.fetchall()
    
    conn.close()
    return render_template('presupuestos.html', presupuestos=presupuestos, proveedores=proveedores, centros_costos=centros_costos, search_query=search_query)

# Proveedores
@app.route('/proveedores', methods=['GET', 'POST'])
def proveedores():
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    search_query = request.args.get('search', '').strip()
    
    if request.method == 'POST':
        razonsocial = request.form['razonsocial']
        contacto = request.form['contacto']
        cuit = request.form['cuit']
        rubro = request.form['rubro']
        ubicacion = request.form['ubicacion']
        descripcion = request.form['descripcion']
        
        cursor.execute('INSERT INTO proveedores (razonsocial, contacto, cuit, rubro, ubicacion, descripcion) VALUES (?, ?, ?, ?, ?, ?)',
                       (razonsocial, contacto, cuit, rubro, ubicacion, descripcion))
        conn.commit()
        return redirect(url_for('proveedores'))
    
    if search_query:
        cursor.execute('''
            SELECT * FROM proveedores
            WHERE razonsocial LIKE ? OR contacto LIKE ? OR cuit LIKE ? OR rubro LIKE ? OR ubicacion LIKE ? OR descripcion LIKE ?
        ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute('SELECT * FROM proveedores')
    
    proveedores = cursor.fetchall()
    conn.close()
    return render_template('proveedores.html', proveedores=proveedores, search_query=search_query)

@app.route('/editar_proveedor/<int:proveedor_id>', methods=['GET', 'POST'])
def editar_proveedor(proveedor_id):
    conn = obtener_conexion()
    cursor = conn.cursor()

    if request.method == 'POST':
        razonsocial = request.form['razonsocial']
        contacto = request.form['contacto']
        cuit = request.form['cuit']
        rubro = request.form['rubro']
        ubicacion = request.form['ubicacion']
        descripcion = request.form['descripcion']

        cursor.execute('''
            UPDATE proveedores
            SET razonsocial = ?, contacto = ?, cuit = ?, rubro = ?, ubicacion = ?, descripcion = ?
            WHERE id = ?
        ''', (razonsocial, contacto, cuit, rubro, ubicacion, descripcion, proveedor_id))
        conn.commit()
        conn.close()
        return redirect(url_for('proveedores'))

    cursor.execute('SELECT * FROM proveedores WHERE id = ?', (proveedor_id,))
    proveedor = cursor.fetchone()
    conn.close()

    return render_template('editar_proveedor.html', proveedor=proveedor)

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
    agregar_columna_cotizacion_dolar()
    insertar_centros_costos()
    app.run(debug=True)