import os
from dotenv import load_dotenv
import requests

# Cargar variables de entorno
load_dotenv()

# Obtener todas las variables relacionadas con Zoho
zoho_vars = {
    'ZOHO_ACCESS_TOKEN': os.getenv('ZOHO_ACCESS_TOKEN'),
    'ZOHO_CLIENT_ID': os.getenv('ZOHO_CLIENT_ID'),
    'ZOHO_CLIENT_SECRET': os.getenv('ZOHO_CLIENT_SECRET'),
    'ZOHO_REFRESH_TOKEN': os.getenv('ZOHO_REFRESH_TOKEN'),
    'ZOHO_BASE_URL': os.getenv('ZOHO_BASE_URL')
}

print("\n=== Zoho Environment Variables ===")
for key, value in zoho_vars.items():
    if value:
        print(f"{key}: {value[:10]}...{value[-10:]}")
    else:
        print(f"{key}: Not found")

# Probar el access token
print("\n=== Testing Access Token ===")
url = "https://www.zohoapis.com/crm/v2/Accounts"
headers = {
    'Authorization': f'Zoho-oauthtoken {zoho_vars["ZOHO_ACCESS_TOKEN"]}'
}

try:
    print(f"Making request to: {url}")
    print(f"Using token: {zoho_vars['ZOHO_ACCESS_TOKEN']}")
    response = requests.get(url, headers=headers)
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Found {len(data.get('data', []))} accounts")
    else:
        print(f"Error response: {response.text}")

        # Si el token expiró, intentar refrescarlo
        if response.status_code == 401:
            print("\n=== Attempting to refresh token ===")
            refresh_url = "https://accounts.zoho.com/oauth/v2/token"
            refresh_params = {
                'refresh_token': zoho_vars['ZOHO_REFRESH_TOKEN'],
                'client_id': zoho_vars['ZOHO_CLIENT_ID'],
                'client_secret': zoho_vars['ZOHO_CLIENT_SECRET'],
                'grant_type': 'refresh_token'
            }
            
            refresh_response = requests.post(refresh_url, params=refresh_params)
            print(f"Refresh status: {refresh_response.status_code}")
            print(f"Refresh response: {refresh_response.text}")
            
            if refresh_response.status_code == 200:
                new_token = refresh_response.json().get('access_token')
                print(f"\nNew access token: {new_token[:10]}...{new_token[-10:]}")
                print("\nUpdate your .env file with this new token")

except Exception as e:
    print(f"Error: {str(e)}")