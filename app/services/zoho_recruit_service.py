from src.services.external.zoho_services import ZohoService
import requests

class ZohoRecruitService:
    def __init__(self, zoho_service=None):
        """
        Inicializar servicio de Zoho Recruit
        
        :param zoho_service: Servicio de Zoho
        """
        self.zoho_service = zoho_service or ZohoService()

    def get_all_candidates(self):
        """
        Obtener todos los candidatos de Zoho Recruit
        
        :return: Lista de candidatos o mensaje de error
        """
        try:
            print("\n=== Getting Candidates from Zoho Recruit ===")
            candidates = self.zoho_service.get_candidates()
            
            return {
                'success': True,
                'candidates': candidates
            }
        
        except Exception as e:
            print(f"Error getting candidates: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_all_jobs(self):
        """
        Obtener todos los trabajos de Zoho Recruit
        
        :return: Lista de trabajos o mensaje de error
        """
        try:
            print("\n=== Getting Jobs from Zoho Recruit ===")
            jobs = self.zoho_service.get_jobs()
            
            return {
                'success': True,
                'jobs': jobs
            }
        
        except Exception as e:
            print(f"Error getting jobs: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def search_candidates(self, criteria):
        """
        Buscar candidatos en Zoho Recruit
        
        :param criteria: Criterios de búsqueda
        :return: Resultado de la búsqueda
        """
        try:
            url = f"{self.zoho_service.recruit_base_url}/Candidates/search"
            headers = {
                'Authorization': f'Zoho-oauthtoken {self.zoho_service.recruit_access_token}'
            }
            params = {
                'criteria': criteria
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            return {
                'success': True,
                'data': response.json()
            }
        
        except Exception as e:
            print(f"Error searching candidates: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }