import os
import re
import requests
import logging
from src.utils.chatgpt_helper import ChatGPTHelper

class WelcomeController:
    def __init__(self):
        self.last_detected_language = 'en'
        self.chatgpt = ChatGPTHelper()
        # Mapa expandido para incluir más países
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
            
            # Puedes añadir más idiomas según sea necesario
        }
        # Configurar logging
        self.logger = logging.getLogger('WelcomeController')
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

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
        """
        Detectar IP del cliente con mejor manejo de casos especiales
        """
        # Lista ordenada de cabeceras para buscar la IP real
        ip_headers = [
            'X-Forwarded-For',
            'Cf-Connecting-Ip',  # CloudFlare
            'X-Real-IP',
            'X-Client-IP',
            'X-Forwarded',
            'Forwarded-For',
            'X-Cluster-Client-IP',
            'True-Client-IP'
        ]
        
        client_ip = None
        
        # Registramos todas las cabeceras para debug
        self.logger.debug("Headers recibidas:")
        for header_name, header_value in request.headers.items():
            self.logger.debug(f"{header_name}: {header_value}")
        
        # Intentamos las cabeceras conocidas
        for header in ip_headers:
            ip_value = request.headers.get(header)
            if ip_value:
                self.logger.debug(f"Encontrada cabecera {header}: {ip_value}")
                
                # Manejar múltiples IPs (primero es generalmente el cliente)
                if ',' in ip_value:
                    potential_ips = [i.strip() for i in ip_value.split(',')]
                    self.logger.debug(f"IPs múltiples encontradas: {potential_ips}")
                    valid_ips = [i for i in potential_ips if self.is_valid_ip(i)]
                    if valid_ips:
                        client_ip = valid_ips[0]
                        self.logger.debug(f"Seleccionada IP: {client_ip}")
                        break
                # IP única
                elif self.is_valid_ip(ip_value):
                    client_ip = ip_value
                    self.logger.debug(f"IP única: {client_ip}")
                    break
        
        # Último recurso: remote_addr
        if not client_ip and hasattr(request, 'remote_addr') and self.is_valid_ip(request.remote_addr):
            client_ip = request.remote_addr
            self.logger.debug(f"Usando remote_addr: {client_ip}")
        
        self.logger.info(f"IP de cliente detectada: {client_ip}")
        return client_ip

    def geolocate_ip(self, client_ip):
        """
        Geolocalizar IP con más servicios y mejor manejo de errores
        """
        country_code = 'US'  # Valor por defecto
        
        # Si no hay IP, devolver el valor por defecto
        if not client_ip:
            self.logger.warning("No se pudo determinar la IP del cliente, usando país por defecto")
            return country_code
        
        # Lista de servicios para geolocalización
        detection_services = [
            # Integramos ipapi.co (gratis, límite de 1000 consultas/día)
            ('ipapi.co', lambda ip: requests.get(f'https://ipapi.co/{ip}/json/', timeout=5)),
            
            # ip-api.com (gratis, límite de 45 consultas/minuto)
            ('ip-api.com', lambda ip: requests.get(f'http://ip-api.com/json/{ip}', timeout=5)),
            
            # ipinfo.io (requiere token gratuito, 50,000 consultas/mes)
            ('ipinfo.io', lambda ip: requests.get(
                f'https://ipinfo.io/{ip}/json?token={os.getenv("IPINFO_TOKEN", "")}', 
                timeout=5
            )),
            
            # ipdata.co (requiere token, 1,500 consultas/día con cuenta gratuita)
            ('ipdata.co', lambda ip: requests.get(
                f'https://api.ipdata.co/{ip}?api-key={os.getenv("IPDATA_TOKEN", "")}',
                timeout=5
            )),
            
            # ipgeolocation.io (requiere token, 1,000 consultas/día con cuenta gratuita)
            ('ipgeolocation.io', lambda ip: requests.get(
                f'https://api.ipgeolocation.io/ipgeo?apiKey={os.getenv("IPGEOLOCATION_TOKEN", "")}&ip={ip}',
                timeout=5
            ))
        ]

        for service_name, service_func in detection_services:
            try:
                self.logger.debug(f"Intentando geolocalizar con: {service_name}")
                response = service_func(client_ip)
                
                if response.status_code != 200:
                    self.logger.warning(f"{service_name} respondió con código: {response.status_code}")
                    continue
                    
                data = response.json()
                self.logger.debug(f"Respuesta de {service_name}: {data}")
                
                # Extraer el código de país según el servicio
                if service_name == 'ipapi.co':
                    country_code = data.get('country_code', country_code)
                elif service_name == 'ip-api.com':
                    country_code = data.get('countryCode', country_code)
                elif service_name == 'ipinfo.io':
                    country_code = data.get('country', country_code)
                elif service_name == 'ipdata.co':
                    country_code = data.get('country_code', country_code)
                elif service_name == 'ipgeolocation.io':
                    country_code = data.get('country_code2', country_code)
                
                self.logger.info(f"País detectado por {service_name}: {country_code}")
                
                # Si encontramos un código de país válido, terminamos
                if country_code and country_code != 'US':  # Solo aceptamos el default si realmente falla todo
                    break
                    
            except Exception as e:
                self.logger.warning(f"Error con {service_name}: {str(e)}")
                continue

        # Asegurarse que el código de país esté en mayúsculas
        country_code = country_code.upper() if isinstance(country_code, str) else 'US'
        self.logger.info(f"Código de país final: {country_code}")
        return country_code

    def generate_welcome_message(self, request):
        """Generar mensaje de bienvenida con mejor detección de ubicación"""
        try:
            # Validar entrada
            validation_result = self.validate_input(request)
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'status_code': 400
                }

            # Detectar IP y país con sistema mejorado
            self.logger.info("Iniciando detección de IP y país")
            client_ip = self.detect_client_ip(request)
            country_code = self.geolocate_ip(client_ip)

            # Determinación de idioma con fallback inteligente
            target_language = self.language_map.get(country_code, 'en')
            self.logger.info(f"Idioma seleccionado: {target_language} para país: {country_code}")

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
            
            # Traducción condicional con mejor manejo
            if target_language != 'en':
                self.logger.info(f"Traduciendo mensajes a {target_language}")
                try:
                    greeting_translated = self.chatgpt.translate_message(
                        f"Translate the following keeping 'Silverlight Research Expert Network' unchanged: {welcome_messages['greeting']['text']}",
                        target_language
                    )
                    instruction_translated = self.chatgpt.translate_message(
                        welcome_messages["instruction"], 
                        target_language
                    )
                    
                    translated_messages = {
                        "greeting": {
                            "english": welcome_messages["greeting"]["text"],
                            "translated": greeting_translated
                        },
                        "instruction": {
                            "english": welcome_messages["instruction"],
                            "translated": instruction_translated
                        }
                    }
                    
                    self.logger.debug(f"Mensajes traducidos: {translated_messages}")
                except Exception as translate_error:
                    self.logger.error(f"Error en traducción: {str(translate_error)}")
                    # Fallback a inglés si falla la traducción
                    translated_messages = {
                        "greeting": {
                            "english": welcome_messages["greeting"]["text"]
                        },
                        "instruction": {
                            "english": welcome_messages["instruction"]
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
            
            # Preparar respuesta detallada
            response_data = {
                'success': True,
                'detected_language': target_language,
                'messages': translated_messages,
                'country_code': country_code,
                'is_english_speaking': target_language == 'en',
                'client_ip': client_ip,  # Para debug
                'has_translations': target_language != 'en',
                'status_code': 200
            }
            
            self.logger.info(f"Respuesta generada exitosamente para {country_code}/{target_language}")
            return response_data

        except Exception as e:
            self.logger.error(f"Error general: {str(e)}", exc_info=True)
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