from flask import Flask, request
from flask_cors import CORS
from config.settings import DevelopmentConfig

# Importaciones de utilidades
from app.utils.environment import (
    setup_project_path, 
    load_environment_variables, 
    test_zoho_token
)

# Importaciones de rutas
from app.routes.token_routes import token_routes
from app.routes.ai.voiceRoutes import voice_routes
from app.routes.ai.translateRoutes import translate_routes
from app.routes.welcome_routes import welcome_routes
from app.routes.conversation_routes import conversation_routes
from app.routes.test_routes import test_routes
from app.routes.ai.sector_routes import sector_routes 
from app.routes.zoho_routes import zoho_routes
from app.routes.monitoring_routes import monitoring_routes

# Importaciones de servicios 
from src.services.external.zoho_services import ZohoService
from src.handlers.voice_handler import VoiceHandler
from src.utils.chatgpt_helper import ChatGPTHelper
from app.services.server_monitoring_service import ServerMonitoringService

def create_app(config_class=DevelopmentConfig):
    # Configurar rutas del proyecto
    setup_project_path()
    
    # Cargar variables de entorno
    load_environment_variables()
    
    # Probar tokens
    test_zoho_token()
    
    # Crear aplicación Flask
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configurar CORS
    CORS(app, resources={
        r"/*": {
            "origins": config_class.ALLOWED_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Content-Type", 
                "Authorization",
                "Accept",
                "Origin"
            ],
            "supports_credentials": True
        }
    })
    
    # Manejo de CORS para cada respuesta
    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        if origin in config_class.ALLOWED_ORIGINS:
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept,Origin')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    # Inicializar servicios globales (opcional)
    print("\n=== Initializing Global Services ===")
    global_services = {
        'zoho_service': ZohoService(verify_token=True),
        'voice_handler': VoiceHandler(),
        'chatgpt': ChatGPTHelper()
    }
    
    for service_name, service_instance in global_services.items():
        app.config[service_name] = service_instance
        print(f"Initialized {service_name}")
    
    # Inicializar servicio de monitoreo
    monitoring_service = ServerMonitoringService()
    monitoring_service.start_keep_alive()
    
    # Definir blueprints de forma más clara
    blueprints_config = [
        {
            'blueprint': token_routes, 
            'url_prefix': '/api'
        },
        {
            'blueprint': voice_routes, 
            'url_prefix': '/api/ai/voice'
        },
        {
            'blueprint': translate_routes,
            'url_prefix': '/api/ai'
        },
        {
            'blueprint': welcome_routes, 
            'url_prefix': '/api'
        },
        {
            'blueprint': conversation_routes, 
            'url_prefix': '/api'
        },
        {
            'blueprint': test_routes,
            'url_prefix': ''  # Sin prefijo para que sea accesible directamente
        },
        {
            'blueprint': sector_routes,
            'url_prefix': '/api/ai'
        },
        {
            'blueprint': zoho_routes,
            'url_prefix': '/api'
        },
        {
            'blueprint': monitoring_routes,
            'url_prefix': '/api'
        }
    ]
    
    # Registrar blueprints
    for bp_config in blueprints_config:
        app.register_blueprint(
            bp_config['blueprint'], 
            url_prefix=bp_config['url_prefix']
        )
    
    return app