import os
from dotenv import load_dotenv
import requests
from pathlib import Path

# Configuración
current_dir = Path(__file__).parent.absolute()
env_path = current_dir / '.env'

print(f"\n=== Environment Setup ===")
print(f"Current directory: {current_dir}")
print(f"Env file path: {env_path}")
print(f"Env file exists: {env_path.exists()}")

# Cargar .env
load_dotenv(env_path)
token = os.getenv('ZOHO_ACCESS_TOKEN')

print(f"\n=== Token Info ===")
print(f"Token found: {'Yes' if token else 'No'}")
if token:
    print(f"Token value: {token}")
    print(f"Token length: {len(token)}")

# Probar el token
if token:
    try:
        url = "https://www.zohoapis.com/crm/v2/Accounts"
        headers = {
            'Authorization': f'Zoho-oauthtoken {token}'
        }
        
        print(f"\n=== Making Test Request ===")
        print(f"URL: {url}")
        print(f"Headers: {headers}")
        
        response = requests.get(url, headers=headers)
        
        print(f"\n=== Response ===")
        print(f"Status code: {response.status_code}")
        print(f"Response body: {response.text[:200]}...")  # Primeros 200 caracteres
        
    except Exception as e:
        print(f"Error: {str(e)}")
else:
    print("No token found in .env file")