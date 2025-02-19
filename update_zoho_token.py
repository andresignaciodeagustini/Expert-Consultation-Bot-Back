import os
from dotenv import load_dotenv
import requests
from pathlib import Path

def update_env_file(new_token):
    # Lee todo el contenido del archivo .env
    with open('.env', 'r') as file:
        lines = file.readlines()
    
    # Actualiza la línea del token
    with open('.env', 'w') as file:
        for line in lines:
            if line.startswith('ZOHO_ACCESS_TOKEN='):
                file.write(f'ZOHO_ACCESS_TOKEN={new_token}\n')
            else:
                file.write(line)

def refresh_token():
    print("\n=== Zoho Token Refresh Process ===")
    
    # Cargar variables actuales
    load_dotenv()
    client_id = os.getenv('ZOHO_CLIENT_ID')
    client_secret = os.getenv('ZOHO_CLIENT_SECRET')
    refresh_token = os.getenv('ZOHO_REFRESH_TOKEN')
    
    print("1. Verificando credenciales...")
    print(f"Client ID: {client_id[:10]}..." if client_id else "Client ID: Missing")
    print(f"Client Secret: {client_secret[:10]}..." if client_secret else "Client Secret: Missing")
    print(f"Refresh Token: {refresh_token[:10]}..." if refresh_token else "Refresh Token: Missing")
    
    # Obtener nuevo token
    print("\n2. Solicitando nuevo token...")
    refresh_url = "https://accounts.zoho.com/oauth/v2/token"
    params = {
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token'
    }
    
    response = requests.post(refresh_url, params=params)
    print(f"Response Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        new_token = response.json().get('access_token')
        print("\n3. Actualizando archivo .env...")
        update_env_file(new_token)
        
        # Verificar el nuevo token
        print("\n4. Verificando nuevo token...")
        test_url = "https://www.zohoapis.com/crm/v2/Accounts"
        headers = {
            'Authorization': f'Zoho-oauthtoken {new_token}'
        }
        test_response = requests.get(test_url, headers=headers)
        print(f"Test Status: {test_response.status_code}")
        
        if test_response.status_code == 200:
            print("\n✅ Token actualizado y verificado correctamente!")
            print(f"Nuevo token: {new_token[:10]}...{new_token[-10:]}")
            return True
        else:
            print("\n❌ El nuevo token no funciona correctamente")
            print(f"Error: {test_response.text}")
            return False
    else:
        print("\n❌ Error obteniendo nuevo token")
        return False

if __name__ == "__main__":
    print("=== Iniciando proceso de actualización de token ===")
    print(f"Directorio actual: {Path.cwd()}")
    print(f"Archivo .env existe: {Path('.env').exists()}")
    
    if refresh_token():
        print("\nProceso completado exitosamente!")
        print("Puedes reiniciar tu servidor Flask ahora.")
    else:
        print("\nError en el proceso de actualización.")
        print("Verifica tus credenciales en el archivo .env")