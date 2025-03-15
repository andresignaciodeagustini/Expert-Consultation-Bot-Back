# src/handlers/company_handler.py
from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.external.zoho_services import ZohoService

class CompanyHandler:
    def __init__(self, zoho_service: ZohoService):
        self.zoho_service = zoho_service
        self.chatgpt = ChatGPTHelper()

    def handle_company_search(self, sector, region, limit=20):
        try:
            zoho_companies = self.zoho_service.get_accounts_by_industry_and_region(
                industry=sector,
                region=region
            )

            companies_needed = limit - len(zoho_companies)
            chatgpt_suggestions = []

            if companies_needed > 0:
                chatgpt_result = self.chatgpt.get_companies_suggestions(
                    sector=sector,
                    geography=region,
                    limit=companies_needed
                )
                if chatgpt_result['success']:
                    chatgpt_suggestions = chatgpt_result['content'][:companies_needed]

            return {
                'success': True,
                'companies': {
                    'zoho': zoho_companies,
                    'suggestions': chatgpt_suggestions,
                    'total': len(zoho_companies) + len(chatgpt_suggestions)
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# src/handlers/language_handler.py
from src.utils.chatgpt_helper import ChatGPTHelper

class LanguageHandler:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()

    def handle_language_detection(self, text):
        try:
            detected_language = self.chatgpt.detect_language(text)
            return {
                'success': True,
                'language': detected_language
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# src/handlers/validation_handler.py
from src.utils.config import VALID_SECTORS
from src.utils.chatgpt_helper import ChatGPTHelper

class ValidationHandler:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()
        self.VALID_REGIONS = ["North America", "Europe", "Asia"]

    def handle_input_validation(self, data):
        try:
            errors = []
            validated_data = {}

            # Validar sector
            if 'sector' in data:
                sector_result = self.chatgpt.translate_sector(data['sector'])
                if sector_result['success'] and sector_result['is_valid']:
                    validated_data['sector'] = sector_result['translated_sector']
                else:
                    errors.append(f"Invalid sector. Must be one of: {', '.join(VALID_SECTORS)}")

            # Validar región
            if 'region' in data:
                region_result = self.chatgpt.identify_region(data['region'])
                if region_result['success']:
                    validated_data['region'] = region_result['region']
                else:
                    errors.append(f"Invalid region. Must be one of: {', '.join(self.VALID_REGIONS)}")

            return {
                'success': len(errors) == 0,
                'validated_data': validated_data if len(errors) == 0 else None,
                'errors': errors
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }