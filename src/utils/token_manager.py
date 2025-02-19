import os
import requests
from datetime import datetime
import json

class TokenManager:
    def __init__(self):
        self.refresh_token = os.getenv('ZOHO_REFRESH_TOKEN')
        self.client_id = os.getenv('ZOHO_CLIENT_ID')
        self.client_secret = os.getenv('ZOHO_CLIENT_SECRET')
        self.vercel_token = os.getenv('VERCEL_TOKEN')
        self.project_id = os.getenv('VERCEL_PROJECT_ID')
        self.environment = os.getenv('ENVIRONMENT', 'development')

    def refresh_zoho_token(self):
        try:
            refresh_url = "https://accounts.zoho.com/oauth/v2/token"
            params = {
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(refresh_url, params=params)
            if response.status_code == 200:
                new_token = response.json().get('access_token')
                if self.environment == 'production':
                    self.update_vercel_env(new_token)
                else:
                    self.update_local_env(new_token)
                return new_token
            return None
        except Exception as e:
            print(f"Error refreshing token: {str(e)}")
            return None

    def update_vercel_env(self, new_token):
        try:
            url = f"https://api.vercel.com/v1/projects/{self.project_id}/env"
            headers = {
                'Authorization': f'Bearer {self.vercel_token}',
                'Content-Type': 'application/json'
            }
            data = {
                'key': 'ZOHO_ACCESS_TOKEN',
                'value': new_token,
                'target': ['production']
            }
            response = requests.post(url, headers=headers, json=data)
            return response.status_code == 200
        except Exception as e:
            print(f"Error updating Vercel env: {str(e)}")
            return False

    def update_local_env(self, new_token):
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
            with open(env_path, 'r') as file:
                lines = file.readlines()
            
            with open(env_path, 'w') as file:
                for line in lines:
                    if line.startswith('ZOHO_ACCESS_TOKEN='):
                        file.write(f'ZOHO_ACCESS_TOKEN={new_token}\n')
                    else:
                        file.write(line)
            return True
        except Exception as e:
            print(f"Error updating local env: {str(e)}")
            return False