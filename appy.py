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
        producto_nombre TEXT,
        precio_unitario TEXT,
        precio_total REAL DEFAULT 0.0,
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
            cursor.execute(
                'INSERT INTO centros_costos (nombre, departamento) VALUES (?, ?)',
                (nombre, departamento)
            )

    conn.commit()
    conn.close()


@app.route('/')
@app.route('/presupuestos', methods=['GET', 'POST'])
def presupuestos():
    conn = obtener_conexion()
    cursor = conn.cursor()

    if request.method == "POST":
        proveedor_id = request.form["proveedor_id"]
        centro_costo_id = request.form["centro_costo_id"]
        fecha = request.form["fecha"]
        productos = request.form.getlist("productos[]")
        precios_productos = request.form.getlist("precios_productos[]")
        precio_total = request.form["precio"]
        moneda = request.form["moneda"]
        cotizacion_dolar = request.form.get("cotizacion_dolar")

        # Guardar PDF
        pdf_filename = None
        if "archivo_pdf" in request.files:
            pdf_file = request.files["archivo_pdf"]
            if pdf_file and pdf_file.filename != "":
                pdf_filename = pdf_file.filename
                pdf_file.save(os.path.join(app.config["UPLOAD_FOLDER"], pdf_filename))

        # Convertir listas a strings
        productos_str = ",".join(productos)
        precios_str = ",".join(precios_productos)

        cursor.execute("""
            INSERT INTO presupuestos 
            (proveedor_id, centro_costo_id, fecha, producto_nombre, precio_unitario, precio_total, moneda, cotizacion_dolar, pdf_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (proveedor_id, centro_costo_id, fecha, productos_str, precios_str, precio_total, moneda, cotizacion_dolar, pdf_filename))
        conn.commit()

    # Mostrar presupuestos
    cursor.execute("""
        SELECT p.id, pr.razonsocial as proveedor, p.producto_nombre, p.precio_unitario,
               p.precio_total, p.moneda, p.cotizacion_dolar, cc.nombre as centro_costo, p.pdf_path
        FROM presupuestos p
        JOIN proveedores pr ON p.proveedor_id = pr.id
        JOIN centros_costos cc ON p.centro_costo_id = cc.id
    """)
    rows = cursor.fetchall()

    presupuestos = []
    for row in rows:
        presupuestos.append({
            "id": row["id"],
            "proveedor": row["proveedor"],
            "productos": row["producto_nombre"].split(",") if row["producto_nombre"] else [],
            "precios": row["precio_unitario"].split(",") if row["precio_unitario"] else [],
            "precio_total": row["precio_total"],
            "moneda": row["moneda"],
            "cotizacion_dolar": row["cotizacion_dolar"],
            "centro_costo": row["centro_costo"],
            "pdf_path": row["pdf_path"]
        })

    cursor.execute('SELECT id, razonsocial FROM proveedores ORDER BY razonsocial ASC')
    proveedores = cursor.fetchall()

    cursor.execute('SELECT id, nombre FROM centros_costos')
    centros_costos = cursor.fetchall()

    conn.close()
    return render_template("presupuestos.html", presupuestos=presupuestos, proveedores=proveedores, centros_costos=centros_costos)


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
    insertar_centros_costos()
    app.run(debug=True)
