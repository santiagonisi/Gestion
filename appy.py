import os
import sqlite3
from flask import Flask, render_template, request, redirect, send_from_directory, url_for

app = Flask(__name__)


UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


def obtener_conexion():
    conn = sqlite3.connect('empresa.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row  
    return conn


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
        precio_total REAL DEFAULT 0.0,
        FOREIGN KEY (proveedor_id) REFERENCES proveedores (id)
    )
    ''')

    conn.commit()
    conn.close()


def agregar_columnas():
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE presupuestos ADD COLUMN cotizacion_dolar REAL")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE presupuestos ADD COLUMN precio_total REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


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


@app.route('/')
@app.route('/presupuestos', methods=['GET', 'POST'])
def presupuestos():
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    search_query = request.args.get('search', '').strip()
    
    if request.method == 'POST':
        proveedor_id = request.form['proveedor_id']
        productos_texto = request.form.get('productos', '')
        precios_texto = request.form.get('precios_productos', '')
        productos = [producto.strip() for producto in productos_texto.split(',') if producto.strip()]
        precios = [float(precio.strip().replace(',', '.')) for precio in precios_texto.split(',') if precio.strip()]
        
        
        if len(productos) != len(precios):
            return "La cantidad de productos no coincide con la cantidad de precios", 400
        
        precio_total = float(request.form['precio'].replace(',', '.'))
        moneda = request.form['moneda']
        fecha = request.form['fecha']
        centro_costo_id = request.form['centro_costo_id']
        
        cotizacion_dolar = request.form.get('cotizacion_dolar', '').strip()
        if cotizacion_dolar:
            cotizacion_dolar = float(cotizacion_dolar.replace(',', '.'))
        else:
            cotizacion_dolar = None
        
        pdf_file = request.files['archivo_pdf']
        pdf_path = None
        if pdf_file:
            pdf_filename = pdf_file.filename
            pdf_path = pdf_filename 
            pdf_file.save(os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename))

        
        for producto, precio in zip(productos, precios):
            cursor.execute('''
                INSERT INTO presupuestos (proveedor_id, producto_nombre, precio, moneda, fecha, centro_costo_id, pdf_path, cotizacion_dolar, precio_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (proveedor_id, producto, precio, moneda, fecha, centro_costo_id, pdf_path, cotizacion_dolar, precio_total))
        
        conn.commit()
    
    
    if search_query:
        cursor.execute('''
            SELECT pr.id, p.razonsocial AS proveedor, GROUP_CONCAT(pr.producto_nombre) AS productos,
                   GROUP_CONCAT(pr.precio) AS precios, pr.moneda, pr.fecha, cc.nombre AS centro_costo, pr.pdf_path,
                   COALESCE(pr.cotizacion_dolar, 0.0) AS cotizacion_dolar, MAX(pr.precio_total) AS precio_total
            FROM presupuestos pr
            JOIN proveedores p ON pr.proveedor_id = p.id
            JOIN centros_costos cc ON pr.centro_costo_id = cc.id
            WHERE p.razonsocial LIKE ? OR pr.producto_nombre LIKE ?
            GROUP BY pr.id, p.razonsocial, pr.moneda, pr.fecha, cc.nombre, pr.pdf_path, pr.cotizacion_dolar
        ''', (f'%{search_query}%', f'%{search_query}%'))
    else: 
        cursor.execute('''
            SELECT pr.id, p.razonsocial AS proveedor, GROUP_CONCAT(pr.producto_nombre) AS productos,
                   GROUP_CONCAT(pr.precio) AS precios, pr.moneda, pr.fecha, cc.nombre AS centro_costo, pr.pdf_path,
                   COALESCE(pr.cotizacion_dolar, 0.0) AS cotizacion_dolar, MAX(pr.precio_total) AS precio_total
            FROM presupuestos pr
            JOIN proveedores p ON pr.proveedor_id = p.id
            JOIN centros_costos cc ON pr.centro_costo_id = cc.id
            GROUP BY pr.id, p.razonsocial, pr.moneda, pr.fecha, cc.nombre, pr.pdf_path, pr.cotizacion_dolar
        ''')
    
    presupuestos = cursor.fetchall()

    
    presupuestos_procesados = []
    for presupuesto in presupuestos:
        productos = presupuesto['productos'].split(',') if presupuesto['productos'] else []
        precios = [float(precio) for precio in presupuesto['precios'].split(',')] if presupuesto['precios'] else []
        presupuestos_procesados.append({
            'id': presupuesto['id'],
            'proveedor': presupuesto['proveedor'],
            'productos': productos,
            'precios': precios,
            'precio_total': presupuesto['precio_total'] if presupuesto['precio_total'] is not None else 0.0,
            'moneda': presupuesto['moneda'],
            'fecha': presupuesto['fecha'],
            'centro_costo': presupuesto['centro_costo'],
            'cotizacion_dolar': presupuesto['cotizacion_dolar'],
            'pdf_path': presupuesto['pdf_path']
        })

    
    cursor.execute('SELECT id, razonsocial FROM proveedores ORDER BY razonsocial ASC')
    proveedores = cursor.fetchall()

    
    cursor.execute('SELECT id, nombre FROM centros_costos')
    centros_costos = cursor.fetchall()

    conn.close()
    return render_template('presupuestos.html', presupuestos=presupuestos_procesados, proveedores=proveedores, centros_costos=centros_costos, search_query=search_query)


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
    agregar_columnas()
    insertar_centros_costos()
    app.run(debug=True)