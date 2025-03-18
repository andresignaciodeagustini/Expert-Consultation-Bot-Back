from src.utils.chatgpt_helper import ChatGPTHelper

class SectorDetectionService:
    def __init__(self, chatgpt=None):
        """
        Inicializar servicio de detección de sector
        
        :param chatgpt: Instancia de ChatGPTHelper
        """
        self.chatgpt = chatgpt or ChatGPTHelper()

    def detect_sector(self, text):
        """
        Detectar sector a partir de texto
        
        :param text: Texto para detección de sector
        :return: Resultado de detección de sector
        """
        try:
            # Validar entrada
            if not text:
                return {
                    'success': False,
                    'message': 'Text input is required'
                }

            # Realizar detección de sector
            sector_result = self.chatgpt.translate_sector(text)

            # Procesar resultado
            if sector_result['success']:
                if sector_result['is_valid']:
                    return {
                        'success': True,
                        'sector': sector_result['translated_sector'],
                        'displayed_sector': sector_result['displayed_sector']
                    }
                else:
                    return {
                        'success': False,
                        'message': f"Invalid sector. Available sectors: {sector_result.get('available_sectors')}",
                        'available_sectors': sector_result.get('available_sectors')
                    }
            
            return {
                'success': False,
                'message': 'Could not process sector'
            }

        except Exception as e:
            print(f"Error in sector detection: {str(e)}")
            return {
                'success': False,
                'message': f'Error processing sector: {str(e)}'
            }