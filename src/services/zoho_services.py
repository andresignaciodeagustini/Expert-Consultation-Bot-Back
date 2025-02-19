import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import traceback

class TokenManager:
    def __init__(self):
        self.refresh_token = os.getenv('ZOHO_REFRESH_TOKEN')
        self.client_id = os.getenv('ZOHO_CLIENT_ID')
        self.client_secret = os.getenv('ZOHO_CLIENT_SECRET')
        self.environment = os.getenv('ENVIRONMENT', 'development')

    def refresh_zoho_token(self):
        try:
            print("\n=== Refreshing Zoho Token ===")
            refresh_url = "https://accounts.zoho.com/oauth/v2/token"
            params = {
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(refresh_url, params=params)
            print(f"Refresh Status: {response.status_code}")
            
            if response.status_code == 200:
                new_token = response.json().get('access_token')
                print(f"New token obtained: {new_token[:10]}...{new_token[-10:]}")
                return new_token
            print(f"Error refreshing token: {response.text}")
            return None
        except Exception as e:
            print(f"Exception in refresh_zoho_token: {str(e)}")
            return None

class ZohoService:
    def __init__(self):
        print("\n=== ZohoService Initialization ===")
        
        # Carga del archivo .env
        current_dir = Path(__file__).parent.parent.parent
        env_path = current_dir / '.env'
        print(f"Looking for .env file at: {env_path}")
        print(f"File exists: {env_path.exists()}")
        
        load_dotenv(env_path)
        self.base_url = "https://www.zohoapis.com/crm/v2"
        self.access_token = os.getenv('ZOHO_ACCESS_TOKEN')
        self.token_manager = TokenManager()
        
        if not self.access_token:
            print("WARNING: ZOHO_ACCESS_TOKEN not found in environment variables!")
        else:
            print(f"Base URL: {self.base_url}")
            print(f"Access Token: {self.access_token[:10]}...{self.access_token[-10:]}")
        
        # Verificación inicial del token
        self._verify_token()

    def _verify_token(self):
        try:
            print("\n=== Token Verification ===")
            url = f"{self.base_url}/Accounts"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.access_token}'
            }
            response = requests.get(url, headers=headers)
            print(f"Verification Status: {response.status_code}")
            
            if response.status_code == 401:  # Token expirado
                print("Token expired, attempting to refresh...")
                new_token = self.token_manager.refresh_zoho_token()
                if new_token:
                    self.access_token = new_token
                    print("Token refreshed successfully")
                else:
                    print("Failed to refresh token")
            elif response.status_code != 200:
                print(f"Token verification failed: {response.text}")
            else:
                print("Token verification successful")
        except Exception as e:
            print(f"Error verifying token: {str(e)}")

    def _handle_request(self, url, headers, params=None):
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 401:  # Token expirado
                print("Token expired, attempting to refresh...")
                new_token = self.token_manager.refresh_zoho_token()
                if new_token:
                    self.access_token = new_token
                    headers['Authorization'] = f'Zoho-oauthtoken {new_token}'
                    response = requests.get(url, headers=headers, params=params)
            
            return response
        except Exception as e:
            print(f"Error in _handle_request: {str(e)}")
            return None

    def get_accounts(self):
        try:
            print("\n=== Getting All Accounts ===")
            url = f"{self.base_url}/Accounts"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.access_token}'
            }

            print(f"Request Details:")
            print(f"URL: {url}")
            print(f"Headers: {headers}")
            
            response = self._handle_request(url, headers)
            if not response:
                return []
                
            print(f"Response Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                accounts = self._format_accounts(data.get('data', []))
                print(f"Successfully retrieved {len(accounts)} accounts")
                return accounts
            else:
                print(f"Error Response: {response.text}")
                return []
        
        except Exception as e:
            print(f"Exception in get_accounts: {str(e)}")
            print(traceback.format_exc())
            return []

    def get_accounts_by_industry(self, industry):
        try:
            print(f"\n=== Searching Accounts by Industry: {industry} ===")
            url = f"{self.base_url}/Accounts/search"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.access_token}'
            }
            params = {
                'criteria': f"(Industry:equals:{industry})"
            }

            print("Request Details:")
            print(f"URL: {url}")
            print(f"Headers: {headers}")
            print(f"Params: {params}")
            
            response = self._handle_request(url, headers, params)
            if not response:
                return []

            print(f"Response Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                accounts = self._format_accounts(data.get('data', []))
                print(f"Found {len(accounts)} accounts for industry: {industry}")
                return accounts
            else:
                print(f"Error Response: {response.text}")
                return []
        except Exception as e:
            print(f"Exception in get_accounts_by_industry: {str(e)}")
            print(traceback.format_exc())
            return []

    def get_accounts_by_region(self, region):
        try:
            print(f"\n=== Searching Accounts by Region: {region} ===")
            accounts = self.get_accounts()
            print(f"Total accounts before filtering: {len(accounts)}")
            
            filtered_accounts = []
            for account in accounts:
                region_coverage = account.get('region_coverage', [])
                if isinstance(region_coverage, str):
                    region_coverage = [region_coverage]
                if region in region_coverage:
                    filtered_accounts.append(account)
            
            print(f"Found {len(filtered_accounts)} accounts in region: {region}")
            return filtered_accounts
        
        except Exception as e:
            print(f"Exception in get_accounts_by_region: {str(e)}")
            print(traceback.format_exc())
            return []

    def get_accounts_by_industry_and_region(self, industry, region):
        try:
            print(f"\n=== Searching Companies by Industry and Region ===")
            print(f"Industry: {industry}")
            print(f"Region: {region}")
            
            url = f"{self.base_url}/Accounts/search"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.access_token}'
            }
            params = {
                'criteria': f"(Industry:equals:{industry})"
            }

            print("\nRequest Details:")
            print(f"URL: {url}")
            print(f"Headers: {headers}")
            print(f"Params: {params}")

            response = self._handle_request(url, headers, params)
            if not response:
                return []

            print(f"Response Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("Raw data received successfully")
                
                accounts = self._format_accounts(data.get('data', []))
                print(f"Total accounts found for industry {industry}: {len(accounts)}")
                
                filtered_accounts = []
                for account in accounts:
                    region_coverage = account.get('region_coverage', [])
                    if isinstance(region_coverage, str):
                        region_coverage = [region_coverage]
                    if region in region_coverage:
                        filtered_accounts.append(account)
                
                print(f"Accounts after filtering by region {region}: {len(filtered_accounts)}")
                
                print("\n=== Filtered Accounts Details ===")
                for account in filtered_accounts:
                    print(self._format_account_display(account))
                
                return filtered_accounts
            else:
                print(f"Error Response: {response.text}")
                return []
                
        except Exception as e:
            print(f"Exception in get_accounts_by_industry_and_region: {str(e)}")
            print(traceback.format_exc())
            return []

    def _format_accounts(self, accounts):
        try:
            print(f"\n=== Formatting {len(accounts)} Accounts ===")
            formatted_accounts = []
            for account in accounts:
                region_coverage = account.get('Region_Coverage', [])
                if isinstance(region_coverage, str):
                    region_coverage = [region_coverage]
                elif region_coverage is None:
                    region_coverage = []
                
                formatted_account = {
                    'id': account.get('id'),
                    'name': account.get('Account_Name'),
                    'industry': account.get('Industry'),
                    'website': account.get('Website'),
                    'employees': account.get('Employees'),
                    'annual_revenue': account.get('Annual_Revenue'),
                    'description': account.get('Description'),
                    'region_coverage': region_coverage
                }
                print(f"Formatted account: {formatted_account['name']}")
                formatted_accounts.append(formatted_account)
            return formatted_accounts
            
        except Exception as e:
            print(f"Exception in _format_accounts: {str(e)}")
            print(traceback.format_exc())
            return []

    def _format_account_display(self, account):
        try:
            region_coverage = account.get('region_coverage', [])
            if isinstance(region_coverage, str):
                region_coverage = [region_coverage]
            
            return f"""
            === Account Details ===
            Name: {account.get('name', 'N/A')}
            Industry: {account.get('industry', 'N/A')}
            Region: {', '.join(region_coverage)}
            Employees: {account.get('employees', 'No mentions')}
            Annual revenue: {account.get('annual_revenue', 'No mentions')}
            Website: {account.get('website', 'No mentions')}
            Description: {account.get('description', 'No mentions')}
            =====================
            """
        except Exception as e:
            print(f"Error formatting account display: {str(e)}")
            return "Error formatting account details"