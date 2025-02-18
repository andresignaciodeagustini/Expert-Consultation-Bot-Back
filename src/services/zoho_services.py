import os
import requests
from dotenv import load_dotenv

class ZohoService:
    def __init__(self):
        load_dotenv()
        self.base_url = "https://www.zohoapis.com/crm/v2"
        self.access_token = os.getenv('ZOHO_ACCESS_TOKEN')

    def get_accounts(self):
        try:
            url = f"{self.base_url}/Accounts"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.access_token}'
            }

            print(f"Requesting URL: {url}")
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return self._format_accounts(data.get('data', []))
            else:
                print(f"Error: {response.status_code}")
                print(f"Response: {response.text}")
                return []
        
        except Exception as e:
            print(f"Error getting accounts: {str(e)}")
            return []
        
    def get_accounts_by_industry(self, industry):
        try:
            url = f"{self.base_url}/Accounts/search"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.access_token}'
            }
            params = {
                'criteria': f"(Industry:equals:{industry})"
            }
            print(f"Requesting URL: {url}")
            print(f"Searching criteria: {params['criteria']}")
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                return self._format_accounts(data.get('data', []))
            else:
                print(f"Error: {response.status_code}")
                print(f"Response: {response.text}")
                return []
        except Exception as e:
            print(f"Error searching accounts: {str(e)}")
            return []

    def get_accounts_by_region(self, region):
        try:
            accounts = self.get_accounts()
            filtered_accounts = [
                account for account in accounts
                if region in account['region_coverage']
            ]
            return filtered_accounts
        
        except Exception as e:
            print(f"Error searching accounts by region: {str(e)}")
            return []
        
    def get_accounts_by_industry_and_region(self, industry, region):
        try:
            url = f"{self.base_url}/Accounts/search"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.access_token}'
            }
            params = {
                'criteria': f"(Industry:equals:{industry})"
            }

            print(f"\nSearching companies:")
            print(f"Industry: {industry}")
            print(f"Region: {region}")
            print(f"URL: {url}")
            print(f"Criteria: {params['criteria']}")

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                accounts = self._format_accounts(data.get('data', [])) 
            
                filtered_accounts = [
                    account for account in accounts
                    if region in account['region_coverage']
                ]
                return filtered_accounts
        
            else:
                print(f"Error: {response.status_code}")
                print(f"Response: {response.text}")
                return []
        except Exception as e:
            print(f"Error searching accounts: {str(e)}")
            return []

    def _format_accounts(self, accounts):  
        formatted_accounts = []
        for account in accounts:
            formatted_account = {
                'id': account.get('id'),
                'name': account.get('Account_Name'),  
                'industry': account.get('Industry'),  
                'website': account.get('Website'),  
                'employees': account.get('Employees'),
                'annual_revenue': account.get('Annual_Revenue'),
                'description': account.get('Description'),
                'region_coverage': account.get('Region_Coverage', [])  
            }
            formatted_accounts.append(formatted_account)
        return formatted_accounts

    def _format_account_display(self, account):
        return f"""
        Name: {account['name']}
        Industry: {account['industry']}
        Region: {', '.join(account['region_coverage'])}
        Employees: {account['employees'] or 'No mentions'}
        Annual revenue: {account['annual_revenue'] or 'No mentions'}
        Website: {account['website'] or 'No mentions'}
        Description: {account['description'] or 'No mentions'}
        """