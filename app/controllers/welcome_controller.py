import os
import re
import requests
from src.utils.chatgpt_helper import ChatGPTHelper

class WelcomeController:
    def __init__(self):
        self.last_detected_language = 'en'
        self.chatgpt = ChatGPTHelper()
        self.language_map = {
            # Español (es)
            'AR': 'es', 'BO': 'es', 'CL': 'es', 'CO': 'es', 'CR': 'es',
            'CU': 'es', 'DO': 'es', 'EC': 'es', 'SV': 'es', 'GQ': 'es',
            'GT': 'es', 'HN': 'es', 'MX': 'es', 'NI': 'es', 'PA': 'es',
            'PY': 'es', 'PE': 'es', 'PR': 'es', 'ES': 'es', 'UY': 'es',
            'VE': 'es',

            # Inglés (en)
            'US': 'en', 'GB': 'en', 'CA': 'en', 'AU': 'en', 'NZ': 'en',
            'IE': 'en', 'ZA': 'en', 'JM': 'en', 'BZ': 'en', 'TT': 'en',
            'GY': 'en', 'AG': 'en', 'BS': 'en', 'BB': 'en',
        }

    def validate_input(self, request):
        """
        Validar datos de entrada
        
        :param request: Solicitud Flask
        :return: Resultado de validación
        """
        if not request:
            return {
                'is_valid': False,
                'error': 'No request provided'
            }
        
        return {
            'is_valid': True,
            'request': request
        }

    def is_valid_ip(self, ip):
        """Validar formato de IP"""
        if not ip or ip == '127.0.0.1':
            return False
        ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
        return bool(ip_pattern.match(ip))

    def detect_client_ip(self, request):
        """Detectar IP del cliente"""
        ip_detection_methods = [
            ('X-Forwarded-For', request.headers.get('X-Forwarded-For')),
            ('X-Real-IP', request.headers.get('X-Real-IP')),
            ('Remote Address', request.remote_addr)
        ]

        client_ip = None
        for method, ip in ip_detection_methods:
            if isinstance(ip, str):
                if ',' in ip:
                    potential_ips = [i.strip() for i in ip.split(',')]
                    valid_ips = [i for i in potential_ips if self.is_valid_ip(i)]
                    if valid_ips:
                        client_ip = valid_ips[0]
                        break
                elif self.is_valid_ip(ip):
                    client_ip = ip
                    break

        return client_ip

    def geolocate_ip(self, client_ip):
        """Geolocalizar IP"""
        country_code = 'US'  # Valor por defecto
        detection_services = [
            ('ipapi.co', lambda ip: requests.get(f'https://ipapi.co/{ip}/json/', timeout=5)),
            ('ip-api.com', lambda ip: requests.get(f'http://ip-api.com/json/{ip}', timeout=5)),
            ('ipinfo.io', lambda ip: requests.get(f'https://ipinfo.io/{ip}/json?token={os.getenv("IPINFO_TOKEN", "")}', timeout=5))
        ]

        if client_ip:
            for service_name, service_func in detection_services:
                try:
                    response = service_func(client_ip)
                    data = response.json()

                    if service_name == 'ipapi.co':
                        country_code = data.get('country_code', 'US')
                    elif service_name == 'ip-api.com':
                        country_code = data.get('countryCode', 'US')
                    elif service_name == 'ipinfo.io':
                        country_code = data.get('country', 'US')

                    if country_code in self.language_map:
                        break

                except Exception:
                    continue

        return country_code

    def generate_welcome_message(self, request):
        """Generar mensaje de bienvenida"""
        try:
            # Validar entrada
            validation_result = self.validate_input(request)
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'status_code': 400
                }

            # Detectar IP y país
            client_ip = self.detect_client_ip(request)
            country_code = self.geolocate_ip(client_ip)

            # Determinar idioma
            target_language = self.language_map.get(country_code, 'en')

            # Actualizar idioma global
            self.last_detected_language = target_language

            # Mensajes de bienvenida base
            welcome_messages = {
                "greeting": {
                    "text": "Welcome to Silverlight Research Expert Network! I'm here to help you find the perfect expert for your needs.",
                    "protected_terms": ["Silverlight Research Expert Network"]
                },
                "instruction": "To get started, please provide your email address."
            }
            
            # Traducción condicional
            if target_language != 'en':
                translated_messages = {
                    "greeting": {
                        "english": welcome_messages["greeting"]["text"],
                        "translated": self.chatgpt.translate_message(
                            f"Translate the following keeping 'Silverlight Research Expert Network' unchanged: {welcome_messages['greeting']['text']}",
                            target_language
                        )
                    },
                    "instruction": {
                        "english": welcome_messages["instruction"],
                        "translated": self.chatgpt.translate_message(welcome_messages["instruction"], target_language)
                    }
                }
            else:
                translated_messages = {
                    "greeting": {
                        "english": welcome_messages["greeting"]["text"]
                    },
                    "instruction": {
                        "english": welcome_messages["instruction"]
                    }
                }
            
            # Preparar respuesta
            response_data = {
                'success': True,
                'detected_language': target_language,
                'messages': translated_messages,
                'country_code': country_code,
                'is_english_speaking': target_language == 'en',
                'status_code': 200
            }
            
            return response_data

        except Exception as e:
            error_message = "Error generating welcome message"
            try:
                error_message = self.chatgpt.translate_message(
                    error_message,
                    self.last_detected_language if self.last_detected_language else 'en'
                )
            except Exception:
                pass

            return {
                'success': False,
                'error': error_message,
                'details': str(e),
                'detected_language': 'en',
                'status_code': 500
            }

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        self.last_detected_language = language