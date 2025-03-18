import os
import requests
from config.settings import Config

class TokenService:
    @staticmethod
    def refresh_zoho_token():
        """Refresca el token de Zoho Recruit"""
        try:
            refresh_url = "https://accounts.zoho.com/oauth/v2/token"
            params = {
                'refresh_token': Config.ZOHO_RECRUIT_REFRESH_TOKEN,
                'client_id': Config.ZOHO_CLIENT_ID,
                'client_secret': Config.ZOHO_CLIENT_SECRET,
                'grant_type': 'refresh_token',
                'scope': 'ZohoRecruit.modules.ALL'
            }
            
            print("\n=== Refreshing Recruit Token ===")
            print(f"Using refresh token: {params['refresh_token'][:10]}...")
            
            response = requests.post(refresh_url, params=params)
            print(f"Refresh response status: {response.status_code}")
            
            if response.status_code == 200:
                new_token = response.json().get('access_token')
                
                # Actualizar en Vercel si estamos en producción
                if Config.ENVIRONMENT == 'production':
                    TokenService._update_vercel_token(new_token)
                else:
                    TokenService._update_local_env(new_token)
                
                return new_token
            
            return None
        
        except Exception as e:
            print(f"Error refreshing token: {str(e)}")
            return None
    
    @staticmethod
    def _update_vercel_token(new_token):
        """Actualiza el token en Vercel"""
        vercel_api_url = f"https://api.vercel.com/v1/projects/{os.getenv('VERCEL_PROJECT_ID')}/env"
        headers = {
            'Authorization': f'Bearer {os.getenv("VERCEL_TOKEN")}'
        }
        data = {
            'key': 'ZOHO_RECRUIT_ACCESS_TOKEN',
            'value': new_token,
            'target': ['production']
        }
        
        print("\n=== Updating Vercel Environment ===")
        vercel_response = requests.post(vercel_api_url, headers=headers, json=data)
        print(f"Vercel update status: {vercel_response.status_code}")
    
    @staticmethod
    def _update_local_env(new_token):
        """Actualiza el token en el archivo .env local"""
        try:
            from app.utils.environment import get_env_path
            
            env_path = get_env_path()
            with open(env_path, 'r') as file:
                lines = file.readlines()
            
            with open(env_path, 'w') as file:
                for line in lines:
                    if line.startswith('ZOHO_RECRUIT_ACCESS_TOKEN='):
                        file.write(f'ZOHO_RECRUIT_ACCESS_TOKEN={new_token}\n')
                    else:
                        file.write(line)
            
            print("\n=== Updated local .env file for Recruit ===")
        except Exception as e:
            print(f"Error updating .env file: {str(e)}")