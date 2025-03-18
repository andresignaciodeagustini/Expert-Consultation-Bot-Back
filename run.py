# run.py
from app import create_app
from config.settings import ProductionConfig
from waitress import serve
import os

app = create_app(ProductionConfig)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    serve(app, host='0.0.0.0', port=port)