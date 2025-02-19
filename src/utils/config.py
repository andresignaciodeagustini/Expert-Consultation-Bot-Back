import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de Zoho
ZOHO_ACCESS_TOKEN = os.getenv('ZOHO_ACCESS_TOKEN')
ZOHO_CLIENT_ID = os.getenv('ZOHO_CLIENT_ID')
ZOHO_CLIENT_SECRET = os.getenv('ZOHO_CLIENT_SECRET')
ZOHO_REFRESH_TOKEN = os.getenv('ZOHO_REFRESH_TOKEN')
ZOHO_BASE_URL = os.getenv('ZOHO_BASE_URL')

# Configuración de OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Constantes de la aplicación
VALID_SECTORS = ["Technology", "Financial Services", "Manufacturing"]
VALID_REGIONS = ["North America", "Europe", "Asia"]

# Configuración de logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)