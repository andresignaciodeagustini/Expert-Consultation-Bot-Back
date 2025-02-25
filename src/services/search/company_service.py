from openai import OpenAI
from typing import Dict
import uuid
from ..external.zoho_services import ZohoService

class CompanyService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.zoho_service = ZohoService()
        print("CompanyService initialized")

    def generate_companies(self, sector: str, geography: str, temperature: float = 0.7) -> Dict:
        try:
            print(f"\n=== Making API Request ===")
            print(f"Parameters: sector={sector}, geography={geography}")
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional business analyst that provides lists of companies based on sector and geography."
                    },
                    {
                        "role": "user",
                        "content": f"List 15 major companies in the {sector} sector that operate in {geography}. Only provide the company names separated by commas."
                    }
                ],
                temperature=temperature,
                max_tokens=150
            )
            
            if hasattr(response.choices[0].message, 'content'):
                companies = response.choices[0].message.content.split(',')
                companies = [company.strip() for company in companies]
                
                print(f"\n=== Success ===")
                print(f"Generated {len(companies)} companies")
                
                return {
                    "success": True,
                    "content": companies[:15],
                    "contentId": str(uuid.uuid4())
                }
            else:
                raise Exception("No content in response")
            
        except Exception as e:
            print(f"\n=== Error ===")
            print(f"Type: {type(e)}")
            print(f"Message: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "contentId": None
            }

    def get_combined_companies(self, sector: str, geography: str) -> Dict:
        """
        Obtiene empresas combinando Zoho CRM y ChatGPT
        """
        try:
            # 1. Buscar en Zoho CRM
            print(f"\nBuscando empresas en Zoho CRM...")
            print(f"Sector: {sector}")
            print(f"Region: {geography}")
            
            zoho_companies = self.zoho_service.get_accounts_by_industry_and_region(
                industry=sector,
                region=geography
            )
            
            zoho_company_names = [company['name'] for company in zoho_companies]
            print(f"\nEmpresas encontradas en Zoho: {len(zoho_company_names)}")
            
            # 2. Obtener sugerencias de ChatGPT
            print("\nObteniendo sugerencias de ChatGPT...")
            chatgpt_result = self.generate_companies(
                sector=sector,
                geography=geography
            )
            
            if not chatgpt_result['success']:
                print(f"Error obteniendo sugerencias de ChatGPT: {chatgpt_result.get('error')}")
                return {
                    'success': False,
                    'error': chatgpt_result.get('error')
                }
                
            chatgpt_companies = chatgpt_result['content']
            print(f"Sugerencias de ChatGPT: {len(chatgpt_companies)}")
            
            # 3. Filtrar empresas de ChatGPT
            filtered_chatgpt_companies = [
                company for company in chatgpt_companies 
                if company not in zoho_company_names
            ]
            
            # 4. Combinar resultados
            combined_companies = {
                'zoho_companies': [
                    {
                        'name': company['name'],
                        'source': 'Zoho CRM',
                        'industry': company['industry'],
                        'region_coverage': company['region_coverage'],
                        'details': {
                            'employees': company['employees'],
                            'annual_revenue': company['annual_revenue'],
                            'website': company['website'],
                            'description': company['description']
                        }
                    } for company in zoho_companies
                ],
                'suggested_companies': [
                    {
                        'name': company,
                        'source': 'ChatGPT',
                        'industry': sector,
                        'region': geography
                    } for company in filtered_chatgpt_companies
                ]
            }
            
            return {
                'success': True,
                'data': combined_companies,
                'total_companies': len(zoho_companies) + len(filtered_chatgpt_companies),
                'zoho_count': len(zoho_companies),
                'suggestions_count': len(filtered_chatgpt_companies)
            }
            
        except Exception as e:
            print(f"Error en get_combined_companies: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }