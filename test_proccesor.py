from openai import OpenAI
import logging
import uuid
import re
from typing import Dict, List, Any, Set, Optional, Tuple
import os
from dotenv import load_dotenv
import tempfile
from pathlib import Path
from unidecode import unidecode
import requests
import unicodedata

logger = logging.getLogger(__name__)

# Configuraciones globales
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
MAX_USERNAME_LENGTH = 64
MAX_DOMAIN_LENGTH = 253

# Dominios comunes globales
COMMON_DOMAINS = {
    'email': [
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'icloud.com', 'aol.com', 'protonmail.com'
    ],
    'social': [
        'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com'
    ],
    'business': [
        'zoho.com', 'office.com', 'microsoft.com', 'apple.com'
    ]
}

# TLDs válidos
VALID_TLDS = {
    'generic': ['com', 'org', 'net', 'edu', 'gov', 'mil', 'int'],
    'country': {
        'us': ['us', 'com', 'org', 'net', 'edu', 'gov'],
        'uk': ['uk', 'co.uk', 'org.uk', 'edu.uk', 'gov.uk'],
        'es': ['es', 'com.es', 'org.es', 'gob.es', 'edu.es'],
        'fr': ['fr', 'com.fr', 'org.fr', 'gouv.fr'],
        'de': ['de', 'com.de', 'org.de', 'edu.de'],
        'it': ['it', 'com.it', 'org.it', 'edu.it'],
        'ru': ['ru', 'com.ru', 'org.ru', 'edu.ru'],
        'cn': ['cn', 'com.cn', 'org.cn', 'edu.cn'],
        'jp': ['jp', 'co.jp', 'or.jp', 'ac.jp'],
        'kr': ['kr', 'co.kr', 'or.kr', 'ac.kr']
    }
}


# Mapeo de palabras a símbolos por idioma
SYMBOL_WORDS = {
    'dot': {
        'es': ['punto', 'puntos'],
        'en': ['dot', 'point', 'period'],
        'fr': ['point', 'points'],
        'de': ['punkt'],
        'it': ['punto'],
        'pt': ['ponto'],
        'ru': ['точка'],
        'ja': ['テン', 'ドット'],
        'zh': ['点', '點'],
        'ko': ['점', '닷'],
        'symbol': '.'
    },
    'underscore': {
        'es': ['guion bajo', 'subrayado', 'subraya'],
        'en': ['underscore', 'underline'],
        'fr': ['souligne', 'soulignement'],
        'de': ['unterstrich'],
        'it': ['sottolineato', 'sottolineatura'],
        'pt': ['sublinhado'],
        'ru': ['подчеркивание', 'нижнее подчеркивание'],
        'ja': ['アンダースコア', 'アンダーバー'],
        'zh': ['下划线', '底線'],
        'ko': ['밑줄'],
        'symbol': '_'
    },
    'hyphen': {
        'es': ['guion', 'raya', 'menos'],
        'en': ['hyphen', 'dash', 'minus'],
        'fr': ['tiret', 'trait'],
        'de': ['bindestrich', 'strich'],
        'it': ['trattino', 'tratto'],
        'pt': ['hífen', 'traço'],
        'ru': ['дефис', 'тире'],
        'ja': ['ハイフン'],
        'zh': ['连字符', '破折号'],
        'ko': ['하이픈', '대시'],
        'symbol': '-'
    },
    'at': {
        'es': ['arroba', 'at'],
        'en': ['at', 'at sign'],
        'fr': ['arobase', 'at'],
        'de': ['at', 'klammeraffe'],
        'it': ['chiocciola'],
        'pt': ['arroba'],
        'ru': ['собака', 'собачка'],
        'ja': ['アット', 'アットマーク'],
        'zh': ['艾特', '@符号'],
        'ko': ['골뱅이'],
        'symbol': '@'
    }
}

# Mapeo de caracteres para transliteración
TRANSLITERATION_MAP = {
    # Cirílico a Latino
    'ru': {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
        'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    },
    # Japonés (Katakana) a Latino
    'ja': {
        'ア': 'a', 'イ': 'i', 'ウ': 'u', 'エ': 'e', 'オ': 'o',
        'カ': 'ka', 'キ': 'ki', 'ク': 'ku', 'ケ': 'ke', 'コ': 'ko',
        'サ': 'sa', 'シ': 'shi', 'ス': 'su', 'セ': 'se', 'ソ': 'so',
        'タ': 'ta', 'チ': 'chi', 'ツ': 'tsu', 'テ': 'te', 'ト': 'to',
        'ナ': 'na', 'ニ': 'ni', 'ヌ': 'nu', 'ネ': 'ne', 'ノ': 'no',
        'ハ': 'ha', 'ヒ': 'hi', 'フ': 'fu', 'ヘ': 'he', 'ホ': 'ho',
        'マ': 'ma', 'ミ': 'mi', 'ム': 'mu', 'メ': 'me', 'モ': 'mo',
        'ヤ': 'ya', 'ユ': 'yu', 'ヨ': 'yo',
        'ラ': 'ra', 'リ': 'ri', 'ル': 'ru', 'レ': 're', 'ロ': 'ro',
        'ワ': 'wa', 'ヲ': 'wo', 'ン': 'n'
    },
    # Chino (Pinyin simplificado)
    'zh': {
        '点': 'dian', '号': 'hao', '网': 'wang', '邮': 'you',
        '箱': 'xiang', '公': 'gong', '司': 'si', '政': 'zheng',
        '府': 'fu', '教': 'jiao', '育': 'yu'
    },
    # Coreano (Romanización revisada)
    'ko': {
        '점': 'jeom', '골': 'gol', '뱅': 'baeng', '이': 'i',
        '메': 'me', '일': 'il', '닷': 'dat', '컴': 'keom'
    }
}

# Patrones de caracteres por idioma
LANGUAGE_PATTERNS = {
    'ru': r'[а-яА-Я]',
    'ja': r'[\u3040-\u309F\u30A0-\u30FF]',
    'zh': r'[\u4E00-\u9FFF]',
    'ko': r'[\uAC00-\uD7AF\u1100-\u11FF]'
}

class UsernameProcessor:
    def __init__(self, client=None):
        # Inicializar OpenAI
        load_dotenv()
        try:
            if client:
                self.client = client
            else:
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not found in environment variables")
                self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise

        # Inicializar configuraciones
        self.symbol_words = SYMBOL_WORDS
        self.transliteration_map = TRANSLITERATION_MAP
        self.language_patterns = LANGUAGE_PATTERNS
        self.common_domains = COMMON_DOMAINS
        self.valid_tlds = VALID_TLDS

    def process_email(self, username_part: str, domain_part: str) -> Dict:
        """
        Procesa un email completo a partir de sus partes
        """
        try:
            # Detectar idioma
            username_lang = self._detect_language(username_part)
            domain_lang = self._detect_language(domain_part)
            
            logger.debug(f"Detected languages - Username: {username_lang}, Domain: {domain_lang}")

            # Procesar username
            username_result = self.process_username(username_part, username_lang)
            if not username_result['success']:
                return username_result

            # Procesar domain
            domain_result = self.process_domain(domain_part, domain_lang)
            if not domain_result['success']:
                return {
                    'success': False,
                    'error': domain_result['error'],
                    'username': username_result['username'],
                    'domain': domain_result.get('processed_domain', ''),
                    'suggestions': domain_result.get('suggestions', [])
                }

            # Construir email completo
            email = f"{username_result['username']}@{domain_result['domain']}"

            # Validar formato final
            if not self._validate_email_format(email):
                return {
                    'success': False,
                    'error': 'Invalid email format',
                    'username': username_result['username'],
                    'domain': domain_result['domain']
                }

            return {
                'success': True,
                'email': email,
                'username': username_result['username'],
                'domain': domain_result['domain'],
                'is_common_domain': domain_result.get('is_common', False),
                'original': {
                    'username': username_part,
                    'domain': domain_part
                }
            }

        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'username_part': username_part,
                'domain_part': domain_part
            }

    def process_username(self, text: str, detected_lang: str = None) -> Dict:
        """
        Procesa el nombre de usuario
        """
        try:
            logger.debug(f"Processing username: {text}")
            
            # Detectar idioma si no se proporciona
            if not detected_lang:
                detected_lang = self._detect_language(text)
            logger.debug(f"Detected language: {detected_lang}")

            # Limpiar y normalizar
            cleaned_text = self._clean_text(text)
            
            # Transliterar si es necesario
            if detected_lang in self.transliteration_map:
                cleaned_text = self._transliterate_text(cleaned_text, detected_lang)
            
            # Procesar símbolos
            processed_text = self._process_symbols(cleaned_text, detected_lang)
            
            # Validación final
            if not self._validate_username_format(processed_text):
                return {
                    'success': False,
                    'error': 'Invalid username format',
                    'original': text
                }

            return {
                'success': True,
                'username': processed_text,
                'original': text,
                'detected_language': detected_lang
            }

        except Exception as e:
            logger.error(f"Error processing username: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'original': text
            }

    def process_domain(self, text: str, detected_lang: str = None) -> Dict:
        """
        Procesa y valida el dominio
        """
        try:
            logger.debug(f"Processing domain: {text}")
            
            # Detectar idioma si no se proporciona
            if not detected_lang:
                detected_lang = self._detect_language(text)
            logger.debug(f"Detected language: {detected_lang}")

            # Limpiar y normalizar
            cleaned_text = self._clean_text(text)
            
            # Transliterar si es necesario
            if detected_lang in self.transliteration_map:
                cleaned_text = self._transliterate_text(cleaned_text, detected_lang)
            
            # Procesar símbolos
            processed_text = self._process_domain_symbols(cleaned_text, detected_lang)
            
            # Verificar si es un dominio común
            common_domain = self._get_common_domain(processed_text)
            if common_domain:
                return {
                    'success': True,
                    'domain': common_domain,
                    'is_common': True,
                    'original': text,
                    'detected_language': detected_lang
                }

            # Validar formato y TLD
            if not self._validate_domain_format(processed_text):
                suggestions = self._get_domain_suggestions(processed_text)
                return {
                    'success': False,
                    'error': 'Invalid domain format',
                    'processed_domain': processed_text,
                    'suggestions': suggestions,
                    'original': text
                }

            return {
                'success': True,
                'domain': processed_text,
                'is_common': False,
                'original': text,
                'detected_language': detected_lang
            }

        except Exception as e:
            logger.error(f"Error processing domain: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'original': text
            }

    def _detect_language(self, text: str) -> str:
        """
        Detecta el idioma del texto basado en caracteres y palabras clave
        """
        # Verificar patrones de caracteres específicos
        for lang, pattern in self.language_patterns.items():
            if re.search(pattern, text):
                return lang

        # Verificar palabras clave
        text_lower = text.lower()
        for symbol_type in self.symbol_words.values():
            for lang, words in symbol_type.items():
                if lang != 'symbol':  # Ignorar la clave 'symbol'
                    if any(word in text_lower for word in words):
                        return lang

        # Default a inglés si no se detecta otro idioma
        return 'en'

    def _clean_text(self, text: str) -> str:
        """
        Limpia y normaliza el texto
        """
        # Eliminar espacios extras
        text = ' '.join(text.split())
        
        # Convertir a minúsculas
        text = text.lower()
        
        # Normalizar caracteres Unicode
        text = unicodedata.normalize('NFKD', text)
        
        return text

    def _transliterate_text(self, text: str, lang: str) -> str:
        """
        Transliterar texto según el idioma detectado
        """
        result = text
        
        # Aplicar mapeo de transliteración específico del idioma
        if lang in self.transliteration_map:
            for original, latin in self.transliteration_map[lang].items():
                result = result.replace(original, latin)

        # Normalizar caracteres restantes
        result = unidecode(result)
        
        return result

    def _process_symbols(self, text: str, lang: str) -> str:
        """
        Procesa símbolos en el texto según el idioma
        """
        words = text.split()
        result = []
        
        i = 0
        while i < len(words):
            word = words[i]
            symbol_found = False
            
            # Buscar en todas las palabras de símbolos
            for symbol_type, symbol_info in self.symbol_words.items():
                if lang in symbol_info and word in symbol_info[lang]:
                    result.append(symbol_info['symbol'])
                    symbol_found = True
                    break
            
            if not symbol_found:
                result.append(word)
            i += 1
        
        return ''.join(result)

    def _process_domain_symbols(self, text: str, lang: str) -> str:
        """
        Procesa símbolos específicamente para dominios
        """
        words = text.split()
        result = []
        
        for word in words:
            # Verificar si es una palabra de símbolo
            for symbol_type, symbol_info in self.symbol_words.items():
                if lang in symbol_info and word in symbol_info[lang]:
                    result.append(symbol_info['symbol'])
                    break
            else:
                result.append(word)
        
        # Unir y limpiar
        domain = ''.join(result)
        
        # Asegurar formato correcto de dominio
        parts = domain.split('.')
        if len(parts) > 1:
            return '.'.join(parts)
        
        return domain

    def _validate_username_format(self, username: str) -> bool:
        """
        Valida el formato del nombre de usuario
        """
        if not username:
            return False

        if len(username) > MAX_USERNAME_LENGTH:
            return False

        # Verificar caracteres permitidos
        if not re.match(r'^[\w\.-_@]+$', username):
            return False

        # Verificar que no empiece ni termine con caracteres especiales
        if re.match(r'^[.-_@]|[.-_@]$', username):
            return False

        # Verificar que no haya símbolos consecutivos
        if re.search(r'[.-_@]{2,}', username):
            return False

        return True

    def _validate_domain_format(self, domain: str) -> bool:
        """
        Valida el formato del dominio
        """
        if not domain or len(domain) > MAX_DOMAIN_LENGTH:
            return False

        # Validar formato general
        if not re.match(r'^[a-z0-9][a-z0-9-\.]{1,251}[a-z0-9]$', domain):
            return False

        # Validar partes del dominio
        parts = domain.split('.')
        if len(parts) < 2:
            return False

        # Validar cada parte
        for part in parts[:-1]:  # Todas las partes excepto el TLD
            if not self._validate_domain_part(part):
                return False

        # Validar TLD
        return self._validate_tld(parts[-1])

    def _validate_domain_part(self, part: str) -> bool:
        """
        Valida una parte individual del dominio
        """
        if not part:
            return False
        
        if len(part) > 63:  # Límite DNS
            return False
        
        if part.startswith('-') or part.endswith('-'):
            return False
        
        if not re.match(r'^[a-z0-9-]+$', part):
            return False
        
        return True

    def _validate_tld(self, tld: str) -> bool:
        """
        Valida el Top Level Domain
        """
        # Verificar TLDs genéricos
        if tld in self.valid_tlds['generic']:
            return True

        # Verificar TLDs de países
        for country_tlds in self.valid_tlds['country'].values():
            if tld in country_tlds:
                return True

        return False

    def _validate_email_format(self, email: str) -> bool:
        """
        Valida el formato completo del email
        """
        if not email or '@' not in email:
            return False

        username, domain = email.split('@')

        # Validar longitudes
        if len(username) > MAX_USERNAME_LENGTH:
            return False
        if len(domain) > MAX_DOMAIN_LENGTH:
            return False

        # Validar formato general
        if not re.match(EMAIL_REGEX, email):
            return False

        return True

    def _get_common_domain(self, domain: str) -> Optional[str]:
        """
        Verifica si el dominio es uno común y retorna su forma correcta
        """
        # Verificar en dominios comunes
        for category in self.common_domains.values():
            for common_domain in category:
                if domain.lower() == common_domain.lower():
                    return common_domain

        return None

    def _get_domain_suggestions(self, invalid_domain: str) -> List[str]:
        """
        Genera sugerencias para dominios inválidos
        """
        suggestions = []
        
        # Obtener la parte base del dominio
        base_name = invalid_domain.split('.')[0]

        # Sugerir dominios comunes
        for category in self.common_domains.values():
            for domain in category:
                if base_name.lower() in domain.lower():
                    suggestions.append(domain)

        # Sugerir TLDs comunes
        common_tlds = ['com', 'org', 'net']
        for tld in common_tlds:
            suggestion = f"{base_name}.{tld}"
            if self._validate_domain_format(suggestion):
                suggestions.append(suggestion)

        # Eliminar duplicados y limitar cantidad
        return list(set(suggestions))[:5]

    def _format_email_parts(self, username: str, domain: str) -> Tuple[str, str]:
        """
        Formatea las partes del email antes del procesamiento
        """
        # Limpiar espacios extras
        username = username.strip()
        domain = domain.strip()
        
        # Remover @ si existe
        username = username.replace('@', '')
        domain = domain.replace('@', '')
        
        return username, domain

    def get_domain_info(self, domain: str) -> Dict:
        """
        Obtiene información detallada sobre un dominio
        """
        try:
            result = self.process_domain(domain)
            if not result['success']:
                return result

            # Añadir información adicional
            domain_parts = result['domain'].split('.')
            tld = domain_parts[-1]
            
            # Determinar tipo de dominio
            domain_type = 'generic'
            domain_region = 'global'
            
            for region, tlds in self.valid_tlds['country'].items():
                if tld in tlds:
                    domain_type = 'country-specific'
                    domain_region = region
                    break

            return {
                **result,
                'domain_info': {
                    'type': domain_type,
                    'region': domain_region,
                    'is_common': result['is_common'],
                    'parts': domain_parts,
                    'tld': tld
                }
            }

        except Exception as e:
            logger.error(f"Error getting domain info: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'domain': domain
            }

    def test_connection(self) -> bool:
        """
        Prueba la conexión con OpenAI
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "Test connection"}
                ]
            )
            logger.info("OpenAI connection test successful")
            return True
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {str(e)}")
            return False

def usage_examples():
    """
    Ejemplos de uso del UsernameProcessor
    """
    processor = UsernameProcessor()

    def print_result(title: str, result: Dict):
        print(f"\n=== {title} ===")
        print(f"Input: {result.get('original', 'N/A')}")
        print(f"Output: {result}")
        print("=" * 50)

    # Ejemplo 1: Procesamiento básico
    basic_tests = [
        # Español
        ("Juan punto Garcia guion bajo Lopez", "gmail punto com"),
        # Inglés
        ("John dot Smith underscore official", "gmail dot com"),
        # Francés
        ("Pierre souligne Dubois point fr", "gmail point fr"),
        # Ruso
        ("Дмитрий нижнее подчеркивание Иванов", "яндекс точка ру"),
        # Japonés
        ("田中 アンダースコア 太郎", "ジーメール テン コム"),
        # Chino
        ("李 下划线 明", "网易 点 康姆"),
        # Coreano
        ("김 밑줄 민수", "지메일 점 컴")
    ]

    print("\n=== PRUEBAS BÁSICAS ===")
    for username, domain in basic_tests:
        result = processor.process_email(username, domain)
        print_result(f"Email en {result.get('detected_language', 'unknown')}", result)

    # Ejemplo 2: Casos especiales
    special_tests = [
        # Mezcla de idiomas
        ("Pierre_Smith点华", "gmail.com"),
        # Caracteres especiales
        ("José.María-López", "empresa.com.es"),
        # Múltiples símbolos
        ("user.name_123-test", "domain-name.co.uk"),
        # Espacios extras
        ("  User  punto  Name  ", "  gmail  punto  com  "),
        # Casos mixtos
        ("JohnDOE.SMITH", "GMAIL.COM")
    ]

    print("\n=== PRUEBAS ESPECIALES ===")
    for username, domain in special_tests:
        result = processor.process_email(username, domain)
        print_result("Caso Especial", result)

    # Ejemplo 3: Validación de dominios
    domain_tests = [
        "gmail.com",
        "hotmail.com.ar",
        "invalid.domain",
        "empresa.com.es",
        "yandex.ru"
    ]

    print("\n=== PRUEBAS DE DOMINIOS ===")
    for domain in domain_tests:
        result = processor.get_domain_info(domain)
        print_result("Información de Dominio", result)

def main():
    """
    Función principal para ejecutar pruebas
    """
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        # Crear instancia del procesador
        processor = UsernameProcessor()

        # Probar conexión
        if not processor.test_connection():
            logger.error("Failed to connect to OpenAI")
            return

        # Ejecutar ejemplos
        usage_examples()

    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()