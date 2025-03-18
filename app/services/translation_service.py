from src.utils.chatgpt_helper import ChatGPTHelper

class TranslationService:
    def __init__(self, chatgpt=None):
        """
        Inicializar servicio de traducción
        
        :param chatgpt: Instancia de ChatGPTHelper
        """
        self.chatgpt = chatgpt or ChatGPTHelper()

    def translate_text(self, text, target_language):
        """
        Traducir texto a un idioma objetivo
        
        :param text: Texto a traducir
        :param target_language: Idioma objetivo
        :return: Texto traducido
        """
        try:
            # Validar entrada
            if not text or not target_language:
                return {
                    'success': False,
                    'message': 'Both text and target_language are required'
                }

            # Realizar traducción
            translated_text = self.chatgpt.translate_message(text, target_language)

            # Registrar detalles de traducción
            print(f"\n=== Translation Result ===")
            print(f"Original text: {text}")
            print(f"Target language: {target_language}")
            print(f"Translated text: {translated_text}")

            return {
                'success': True,
                'translated_text': translated_text
            }

        except Exception as e:
            print(f"\n=== Error in translation ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            return {
                'success': False,
                'message': 'Error translating text',
                'error': str(e)
            }