import sys
from pathlib import Path
import os
from dotenv import load_dotenv
import requests

def setup_project_path():
    """Configura la ruta del proyecto en sys.path"""
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.append(project_root)

def get_env_path():
    """Obtiene la ruta del archivo .env"""
    return Path(__file__).parent.parent.parent / '.env'

def load_environment_variables():
    """Carga las variables de entorno"""
    env_path = get_env_path()
    print("\n=== Environment Setup ===")
    print(f"Project Root: {env_path.parent}")
    print(f"Env file path: {env_path}")
    print(f"Env file exists: {env_path.exists()}")
    
    load_dotenv(env_path)

def test_zoho_token():
    """Prueba el token de Zoho Recruit"""
    from src.services.external.zoho_services import ZohoService
    
    # Crear una única instancia de ZohoService con verificación de token
    zoho_service = ZohoService(verify_token=True)
    
    recruit_token = os.getenv('ZOHO_RECRUIT_ACCESS_TOKEN')
    
    print(f"\n=== Token Verification ===")
    print(f"Recruit Token loaded: {recruit_token[:10]}...{recruit_token[-10:] if recruit_token else 'None'}")
    
    try:
        # Intentar obtener candidatos para verificar el token
        candidates = zoho_service.get_candidates()
        
        print("\nTesting Recruit token with Zoho API...")
        print(f"Token verification successful")
        print(f"Retrieved {len(candidates)} candidates")
        
        return True
    
    except Exception as e:
        print(f"Recruit Token test failed: {str(e)}")
        print("WARNING: Recruit functionality may not work correctly")
        return False