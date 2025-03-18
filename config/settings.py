import os
from pathlib import Path

class Config:
    # Configuraciones generales
    PROJECT_ROOT = str(Path(__file__).parent.parent)
    
    # Lista de orígenes permitidos
    ALLOWED_ORIGINS = [
        "https://expert-consultation-bot-front.vercel.app",
        "https://expert-consultation-bot-front-i0r29638j.vercel.app",
        "https://expert-consultation-bot-front2.onrender.com",
        "https://expert-consultation-bot-front.onrender.com",
        "http://localhost:5173",
        "http://127.0.0.1:8080"
    ]

    # Configuraciones de Zoho
    ZOHO_RECRUIT_ACCESS_TOKEN = os.getenv('ZOHO_RECRUIT_ACCESS_TOKEN')
    ZOHO_RECRUIT_REFRESH_TOKEN = os.getenv('ZOHO_RECRUIT_REFRESH_TOKEN')
    ZOHO_CLIENT_ID = os.getenv('ZOHO_CLIENT_ID')
    ZOHO_CLIENT_SECRET = os.getenv('ZOHO_CLIENT_SECRET')
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False