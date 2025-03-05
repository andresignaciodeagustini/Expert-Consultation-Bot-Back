import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import traceback

def get_env_path():
    return Path(__file__).parent.parent.parent.parent / '.env'

class TokenManager:
    def __init__(self):
        self.recruit_refresh_token = os.getenv('ZOHO_RECRUIT_REFRESH_TOKEN')
        self.client_id = os.getenv('ZOHO_CLIENT_ID')
        self.client_secret = os.getenv('ZOHO_CLIENT_SECRET')
        self.environment = os.getenv('ENVIRONMENT', 'development')

    def refresh_zoho_token(self):
        try:
            print("\n=== Refreshing Zoho Recruit Token ===")
            refresh_url = "https://accounts.zoho.com/oauth/v2/token"
            
            params = {
                'refresh_token': self.recruit_refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'refresh_token',
                'scope': 'ZohoRecruit.modules.ALL'
            }
            
            response = requests.post(refresh_url, params=params)
            print(f"Refresh Status: {response.status_code}")
            
            if response.status_code == 200:
                new_token = response.json().get('access_token')
                print(f"New token obtained: {new_token[:10]}...{new_token[-10:]}")
                
                # Actualizar el archivo .env si estamos en desarrollo
                if self.environment == 'development':
                    try:
                        env_path = get_env_path()
                        with open(env_path, 'r') as file:
                            lines = file.readlines()
                        
                        with open(env_path, 'w') as file:
                            token_env_key = 'ZOHO_RECRUIT_ACCESS_TOKEN'
                            for line in lines:
                                if line.startswith(f'{token_env_key}='):
                                    file.write(f'{token_env_key}={new_token}\n')
                                else:
                                    file.write(line)
                        print("\n=== Updated local .env file for Recruit ===")
                    except Exception as e:
                        print(f"Error updating .env file: {str(e)}")
                
                return new_token
            print(f"Error refreshing token: {response.text}")
            return None
        except Exception as e:
            print(f"Exception in refresh_zoho_token: {str(e)}")
            return None

class ZohoService:
    def __init__(self):
        print("\n=== ZohoService Initialization ===")
        
        env_path = get_env_path()
        print(f"Looking for .env file at: {env_path}")
        print(f"File exists: {env_path.exists()}")
        
        load_dotenv(env_path)
        
        self.recruit_base_url = "https://recruit.zoho.com/recruit/v2"
        self.recruit_access_token = os.getenv('ZOHO_RECRUIT_ACCESS_TOKEN')
        self.token_manager = TokenManager()
        
        self._verify_token()

    def _verify_token(self):
        try:
            print("\n=== Recruit Token Verification ===")
            print(f"Current token: {self.recruit_access_token[:10]}... ")
            
            url = f"{self.recruit_base_url}/Candidates"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.recruit_access_token}'
            }
            
            response = requests.get(url, headers=headers)
            print(f"Verification Status: {response.status_code}")
            
            if response.status_code == 401:
                print("Token expired, attempting to refresh...")
                new_token = self.token_manager.refresh_zoho_token()
                if new_token:
                    self.recruit_access_token = new_token
                    print(f"Token refreshed successfully. New token: {new_token[:10]}...")
                    
                    # Verificar el nuevo token
                    headers['Authorization'] = f'Zoho-oauthtoken {new_token}'
                    verify_response = requests.get(url, headers=headers)
                    print(f"New token verification status: {verify_response.status_code}")
                    
                    if verify_response.status_code != 200:
                        print("Warning: New token verification failed")
                else:
                    print("Failed to refresh token")
            elif response.status_code != 200:
                print(f"Token verification failed: {response.text}")
            else:
                print("Token verification successful")
                
        except Exception as e:
            print(f"Error verifying token: {str(e)}")
            traceback.print_exc()

    def _handle_request(self, url, headers, params=None):
        try:
            # Primer intento
            response = requests.get(url, headers=headers, params=params)
            
            # Si el token expiró, intentar renovarlo y hacer un segundo intento
            if response.status_code == 401:
                print("Token expired, attempting to refresh...")
                new_token = self.token_manager.refresh_zoho_token()
                if new_token:
                    self.recruit_access_token = new_token
                    headers['Authorization'] = f'Zoho-oauthtoken {new_token}'
                    response = requests.get(url, headers=headers, params=params)
                    print(f"Second attempt status: {response.status_code}")
                else:
                    print("Failed to refresh token")
            
            return response
        except Exception as e:
            print(f"Error in _handle_request: {str(e)}")
            traceback.print_exc()
            return None

    def search_candidates(self, search_criteria):
        try:
            print(f"\n=== Searching Candidates with criteria: {search_criteria} ===")
            url = f"{self.recruit_base_url}/Candidates/search"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.recruit_access_token}'
            }
            params = {
                'criteria': search_criteria
            }
            
            # Verificar y actualizar token si es necesario
            self._verify_token()
            
            response = self._handle_request(url, headers, params)
            if not response:
                return {"error": "No response from server"}
                
            print(f"Search Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                candidates = data.get('data', [])
                print(f"Successfully found {len(candidates)} candidates")
                return candidates
            else:
                error_message = response.text if hasattr(response, 'text') else "Unknown error"
                print(f"Error Response: {error_message}")
                return {"error": error_message}
                
        except Exception as e:
            print(f"Exception in search_candidates: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}

    def get_candidates(self):
        try:
            print("\n=== Getting All Candidates ===")
            url = f"{self.recruit_base_url}/Candidates"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.recruit_access_token}'
            }
            
            response = self._handle_request(url, headers)
            if not response:
                return []
                
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                candidates = data.get('data', [])
                print(f"Successfully retrieved {len(candidates)} candidates")
                return candidates
            else:
                print(f"Error Response: {response.text}")
                return []
            
        except Exception as e:
            print(f"Exception in get_candidates: {str(e)}")
            return []

    def get_jobs(self):
        try:
            print("\n=== Getting All Jobs ===")
            url = f"{self.recruit_base_url}/JobOpenings"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.recruit_access_token}'
            }
            
            response = self._handle_request(url, headers)
            if not response:
                return []
                
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                jobs = data.get('data', [])
                print(f"Successfully retrieved {len(jobs)} jobs")
                return jobs
            else:
                print(f"Error Response: {response.text}")
                return []
            
        except Exception as e:
            print(f"Exception in get_jobs: {str(e)}")
            return []

    def create_candidate(self, candidate_data):
        try:
            print("\n=== Creating New Candidate ===")
            url = f"{self.recruit_base_url}/Candidates"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.recruit_access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, headers=headers, json={'data': [candidate_data]})
            print(f"Response Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"Error Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception in create_candidate: {str(e)}")
            return None

    def get_candidate_by_email(self, email):
        try:
            print(f"\n=== Getting Candidate by Email: {email} ===")
            url = f"{self.recruit_base_url}/Candidates/search"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.recruit_access_token}'
            }
            params = {
                'criteria': f"(Email:equals:{email})"
            }
            
            response = self._handle_request(url, headers, params)
            if not response:
                return None
                
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                candidates = data.get('data', [])
                if candidates:
                    print("Candidate found")
                    return candidates[0]
                print("No candidate found with this email")
                return None
            else:
                print(f"Error Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception in get_candidate_by_email: {str(e)}")
            return None

    def update_candidate(self, candidate_id, update_data):
        try:
            print(f"\n=== Updating Candidate {candidate_id} ===")
            url = f"{self.recruit_base_url}/Candidates/{candidate_id}"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.recruit_access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.put(url, headers=headers, json={'data': [update_data]})
            print(f"Response Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"Error Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception in update_candidate: {str(e)}")
            return None