import os
import sqlite3
from flask import Flask, render_template, request, redirect, send_from_directory, url_for

app = Flask(__name__)

#configuracion carpeta uploads
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#carpeta uploads
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    print(f"Intentando servir el archivo: {filename}")
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

#base de datos
def obtener_conexion():
    conn = sqlite3.connect('empresa.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row  
    return conn

#tablas
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

#centro de costos
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

#presupuestos/paginaprincipal
@app.route('/')
@app.route('/presupuestos', methods=['GET', 'POST'])
def presupuestos():
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    
    search_query = request.args.get('search', '').strip()
    
    if request.method == 'POST':
        #datos del formulario
        proveedor_id = request.form['proveedor_id']
        producto_nombre = request.form['producto_nombre']
        precio = request.form['precio'].replace(',', '.')
        moneda = request.form['moneda']
        fecha = request.form['fecha']
        centro_costo_id = request.form['centro_costo_id']
        
        #PDF
        archivo_pdf = request.files.get('archivo_pdf')
        pdf_path = None
        if archivo_pdf:
            filename = f"{producto_nombre}_{archivo_pdf.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            archivo_pdf.save(filepath)
            pdf_path = filename 
            print(f"Archivo PDF guardado en: {filepath}")
        
        #insertar el presupuesto en la tabla presupuestos
        cursor.execute('''
            INSERT INTO presupuestos (proveedor_id, producto_nombre, precio, moneda, fecha, centro_costo_id, pdf_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (proveedor_id, producto_nombre, precio, moneda, fecha, centro_costo_id, pdf_path))
        conn.commit()
        print(f"Insertando en la base de datos: proveedor_id={proveedor_id}, producto_nombre={producto_nombre}, pdf_path={pdf_path}")
    
    #filtro de búsqueda presupuestos
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
    
    #mostrar en tabla los presupuestos
    presupuestos = cursor.fetchall()
    print(f"Presupuestos cargados: {presupuestos}")
    
    #menú desplegable de proveedores
    cursor.execute('SELECT id, nombre FROM proveedores')
    proveedores = cursor.fetchall()
    
    #menú desplegable de centros de costos
    cursor.execute('SELECT id, nombre FROM centros_costos')
    centros_costos = cursor.fetchall()
    
    conn.close()
    return render_template('presupuestos.html', presupuestos=presupuestos, proveedores=proveedores, centros_costos=centros_costos, search_query=search_query)

#proveedores
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
    
    cursor.execute('SELECT * FROM proveedores')
    proveedores = cursor.fetchall()
    
    #filtro de búsqueda proveedores
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