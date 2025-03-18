import sys
from pathlib import Path
import os

# Configuración de rutas del proyecto
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from app import create_app
from config.settings import ProductionConfig

# Crear la aplicación
app = create_app(ProductionConfig)

# Punto de entrada principal para Heroku
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    from waitress import serve
    serve(app, host='0.0.0.0', port=port)





































    



