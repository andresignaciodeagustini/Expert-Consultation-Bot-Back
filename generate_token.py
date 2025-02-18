# generate_token.py
import requests
import os
from dotenv import load_dotenv

def generate_refresh_token():
    load_dotenv()
    
    # Configuración
    client_id = os.getenv('ZOHO_CLIENT_ID')
    client_secret = os.getenv('ZOHO_CLIENT_SECRET')
    grant_token = "1000.cb8dcc06b1e3d7fddc5f702f6b95df3e.24fec2049d3efc06a47389d3f9ae71f5"
    
    # URL para obtener el refresh token
    url = "https://accounts.zoho.com/oauth/v2/token"
    
    # Datos para la solicitud
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": grant_token
    }
    
    print("=== Iniciando generación de Refresh Token ===")
    print(f"\nConfiguración:")
    print(f"URL: {url}")
    print(f"Client ID: {client_id}")
    print(f"Grant Token: {grant_token}")
    
    try:
        print("\nRealizando solicitud...")
        response = requests.post(url, data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            token_data = response.json()
            refresh_token = token_data.get('refresh_token')
            access_token = token_data.get('access_token')
            
            print("\n✅ Tokens generados exitosamente:")
            print(f"Refresh Token: {refresh_token}")
            print(f"Access Token: {access_token[:20]}...")
            
            # Actualizar el archivo .env
            env_path = '.env'
            with open(env_path, 'r') as file:
                lines = file.readlines()
            
            with open(env_path, 'w') as file:
                for line in lines:
                    if line.startswith('ZOHO_REFRESH_TOKEN='):
                        file.write(f'ZOHO_REFRESH_TOKEN={refresh_token}\n')
                    else:
                        file.write(line)
            
            print("\n✅ Archivo .env actualizado con el nuevo refresh token")
            return refresh_token
            
        else:
            print("\n❌ Error al obtener el refresh token")
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None
    finally:
        print("\n=== Fin del proceso ===")

if __name__ == "__main__":
    refresh_token = generate_refresh_token()