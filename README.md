# Gestión

Software de control de presupuestos y proveedores para la gestión administrativa de la empresa.

## Stack

- **Backend:** Python + Flask
- **Plantillas:** Jinja2
- **Base de datos:** SQLite
- **Reportes:** FPDF2
- **Servidor:** Gunicorn

## Estructura del proyecto

```
Gestion/
├── static/               # CSS, JavaScript y recursos estáticos
├── templates/            # Plantillas de la interfaz
├── appy.py               # Aplicación principal
├── fix_proveedores.py    # Utilidad de mantenimiento de proveedores
├── update_db.py          # Utilidad de actualización de la base de datos
├── start.sh              # Script de inicio
├── requirements.txt      # Dependencias de Python
└── empresa.db            # Base de datos local
```

## Módulos

- **Proveedores:** alta, consulta y administración de proveedores.
- **Presupuestos:** registro y control de presupuestos.
- **Archivos:** carga y gestión de documentación asociada.
- **Reportes:** generación de informes en PDF.
- **Base de datos:** persistencia de la información administrativa.
