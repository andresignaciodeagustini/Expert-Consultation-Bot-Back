from openai import OpenAI
import logging
import uuid
import re
from typing import Dict, List, Any, Set, Optional, Tuple
import os
from dotenv import load_dotenv
from typing import Dict, BinaryIO
import tempfile
from pathlib import Path
import tempfile
from unidecode import unidecode
import requests
import unicodedata 

logger = logging.getLogger(__name__)

# Configuraciones globales mejoradas
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
MAX_USERNAME_LENGTH = 64
MAX_DOMAIN_LENGTH = 253
# Mapeo mejorado de símbolos por idioma (COMPLETO)
SYMBOL_MAPPING = {
    '.': {
        'es': ['punto', 'puntos', 'dot'],
        'en': ['dot', 'point', 'period', 'full stop'],
        'fr': ['point', 'points'],
        'de': ['punkt'],
        'it': ['punto'],
        'pt': ['ponto'],
        'ru': ['точка', 'точки'],
        'ja': ['テン', 'ドット'],
        'zh': ['点', '點', 'dian'],
        'ko': ['점', '닷']
    },
    '_': {
        'es': ['guion bajo', 'subrayado', 'subraya'],
        'en': ['underscore', 'underline'],
        'fr': ['souligne', 'soulignement'],
        'de': ['unterstrich'],
        'it': ['sottolineato', 'sottolineatura'],
        'pt': ['sublinhado'],
        'ru': ['подчеркивание', 'нижнее подчеркивание'],
        'ja': ['アンダースコア', 'アンダーバー'],
        'zh': ['下划线', '底線'],
        'ko': ['밑줄']
    },
    '-': {
        'es': ['guion', 'raya', 'menos'],
        'en': ['hyphen', 'dash', 'minus'],
        'fr': ['tiret', 'trait'],
        'de': ['bindestrich', 'strich'],
        'it': ['trattino', 'tratto'],
        'pt': ['hífen', 'traço'],
        'ru': ['дефис', 'тире'],
        'ja': ['ハイフン'],
        'zh': ['连字符', '破折号'],
        'ko': ['하이픈', '대시']
    },
    '@': {
        'es': ['arroba', 'at'],
        'en': ['at', 'at sign'],
        'fr': ['arobase', 'at'],
        'de': ['at', 'klammeraffe'],
        'it': ['chiocciola'],
        'pt': ['arroba'],
        'ru': ['собака', 'собачка'],
        'ja': ['アット', 'アットマーク'],
        'zh': ['艾特', '@符号'],
        'ko': ['골뱅이']
    }
}

# Patrones de detección de idioma mejorados (COMPLETO)
LANGUAGE_PATTERNS = {
    'ru': {
        'pattern': r'[а-яА-Я]',
        'keywords': ['точка', 'собака', 'почта']
    },
    'ja': {
        'pattern': r'[\u3040-\u309F\u30A0-\u30FF]',
        'keywords': ['メール', 'ドット', 'アット']
    },
    'zh': {
        'pattern': r'[\u4E00-\u9FFF]',
        'keywords': ['点', '邮箱', '网址']
    },
    'ko': {
        'pattern': r'[\uAC00-\uD7AF\u1100-\u11FF]',
        'keywords': ['점', '메일', '주소']
    },
    'es': {
        'pattern': r'[áéíóúñ]',
        'keywords': ['punto', 'arroba', 'correo']
    },
    'fr': {
        'pattern': r'[éèêëàâçîïôûùü]',
        'keywords': ['point', 'arobase', 'courriel']
    },
    'de': {
        'pattern': r'[äöüß]',
        'keywords': ['punkt', 'at', 'mail']
    }
}
# Dominios comunes mejorados con variantes internacionales (COMPLETO)
COMMON_DOMAINS = {
    'global': {
        'gmail.com': ['gmail', 'googlemail'],
        'yahoo.com': ['yahoo', 'ymail'],
        'outlook.com': ['outlook', 'hotmail', 'live'],
        'icloud.com': ['icloud', 'me.com', 'mac.com']
    },
    'regional': {
        'ru': {
            'mail.ru': ['mail', 'мейл'],
            'yandex.ru': ['yandex', 'яндекс'],
            'rambler.ru': ['rambler', 'рамблер']
        },
        'cn': {
            'qq.com': ['qq', '腾讯'],
            '163.com': ['163', '网易'],
            'sina.com': ['sina', '新浪']
        },
        'jp': {
            'yahoo.co.jp': ['yahoo', 'ヤフー'],
            'docomo.ne.jp': ['docomo', 'ドコモ'],
            'softbank.ne.jp': ['softbank', 'ソフトバンク']
        },
        'kr': {
            'naver.com': ['naver', '네이버'],
            'daum.net': ['daum', '다음'],
            'hanmail.net': ['hanmail', '한메일']
        }
    }
}

# Nuevo mapa de transliteración completo
TRANSLITERATION_MAP = {
    'russian': {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'a', 'Б': 'b', 'В': 'v', 'Г': 'g', 'Д': 'd', 'Е': 'e', 'Ё': 'yo',
        'Ж': 'zh', 'З': 'z', 'И': 'i', 'Й': 'y', 'К': 'k', 'Л': 'l', 'М': 'm',
        'Н': 'n', 'О': 'o', 'П': 'p', 'Р': 'r', 'С': 's', 'Т': 't', 'У': 'u',
        'Ф': 'f', 'Х': 'h', 'Ц': 'ts', 'Ч': 'ch', 'Ш': 'sh', 'Щ': 'sch',
        'Ъ': '', 'Ы': 'y', 'Ь': '', 'Э': 'e', 'Ю': 'yu', 'Я': 'ya'
    },
    'japanese': {
        'あ': 'a', 'い': 'i', 'う': 'u', 'え': 'e', 'お': 'o',
        'か': 'ka', 'き': 'ki', 'く': 'ku', 'け': 'ke', 'こ': 'ko',
        'さ': 'sa', 'し': 'shi', 'す': 'su', 'せ': 'se', 'そ': 'so',
        'た': 'ta', 'ち': 'chi', 'つ': 'tsu', 'て': 'te', 'と': 'to',
        'な': 'na', 'に': 'ni', 'ぬ': 'nu', 'ね': 'ne', 'の': 'no',
        'は': 'ha', 'ひ': 'hi', 'ふ': 'fu', 'へ': 'he', 'ほ': 'ho',
        'ま': 'ma', 'み': 'mi', 'む': 'mu', 'め': 'me', 'も': 'mo',
        'や': 'ya', 'ゆ': 'yu', 'よ': 'yo',
        'ら': 'ra', 'り': 'ri', 'る': 'ru', 'れ': 're', 'ろ': 'ro',
        'わ': 'wa', 'を': 'wo', 'ん': 'n'
    },
    'chinese': {
        '阿': 'a', '伯': 'bo', '茨': 'ci', '德': 'de', '俄': 'e',
        '佛': 'fo', '哥': 'ge', '海': 'hai', '艾': 'ai', '杰': 'jie',
        '卡': 'ka', '拉': 'la', '马': 'ma', '娜': 'na', '欧': 'ou',
        '帕': 'pa', '奇': 'qi', '热': 're', '萨': 'sa', '特': 'te',
        '维': 'wei', '西': 'xi', '雅': 'ya', '扎': 'zha'
    },
    'korean': {
        '김': 'kim', '이': 'lee', '박': 'park', '정': 'jung', '최': 'choi',
        '강': 'kang', '조': 'cho', '윤': 'yoon', '장': 'jang', '임': 'lim',
        '한': 'han', '오': 'oh', '서': 'seo', '신': 'shin', '권': 'kwon',
        '황': 'hwang', '안': 'ahn', '송': 'song', '전': 'jeon', '홍': 'hong'
    }
}

# TLDs internacionales completos
INTERNATIONAL_TLDS = {
    'us': ['com', 'org', 'net', 'edu', 'gov', 'mil'],
    'uk': ['co.uk', 'org.uk', 'me.uk', 'ac.uk', 'gov.uk'],
    'eu': ['eu', 'de', 'fr', 'es', 'it', 'nl', 'be', 'at', 'dk', 'fi', 'gr', 'ie', 'pt', 'se'],
    'asia': ['jp', 'cn', 'kr', 'in', 'sg', 'hk', 'tw', 'my', 'th', 'vn'],
    'ru': ['ru', 'su', 'рф', 'moscow', 'спб'],
    'other': ['info', 'biz', 'name', 'mobi', 'asia', 'tel', 'pro']
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

        # Inicializar todas las configuraciones
        self.symbol_mapping = SYMBOL_MAPPING
        self.language_patterns = LANGUAGE_PATTERNS
        self.common_domains = COMMON_DOMAINS
        self.transliteration_map = TRANSLITERATION_MAP
        self.international_tlds = INTERNATIONAL_TLDS

    def _process_with_gpt4(self, text: str) -> str:
        """
        Procesa el texto usando GPT-4
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "Procesa el nombre de usuario manteniendo solo letras, números y los símbolos permitidos (punto, guion bajo). Elimina palabras que describan símbolos."
                    },
                    {
                        "role": "user",
                        "content": f"Procesa este nombre: {text}"
                    }
                ],
                temperature=0.1
            )
            
            processed_text = response.choices[0].message.content.strip()
            return self._clean_username(processed_text)
        except Exception as e:
            logger.error(f"Error in GPT-4 processing: {str(e)}")
            return text

    def _clean_username(self, username: str) -> str:
        """
        Limpia y formatea el nombre de usuario
        """
        # Convertir a minúsculas y eliminar espacios extras
        cleaned = username.lower().strip()
        # Reemplazar espacios con guiones bajos
        cleaned = "_".join(cleaned.split())
        # Eliminar caracteres no permitidos
        cleaned = ''.join(c for c in cleaned if c.isalnum() or c in '_.-')
        return cleaned

    def _clean_text(self, text: str) -> str:
        """
        Limpieza de texto mejorada
        """
        # Eliminar espacios extras
        text = ' '.join(text.split())
        # Convertir a minúsculas
        text = text.lower()
        # Normalizar caracteres Unicode
        text = unicodedata.normalize('NFKD', text)
        # Eliminar caracteres no deseados pero mantener símbolos importantes
        text = re.sub(r'[^\w\s\.\-_@]', '', text)
        return text
    def process_username(self, text: str, detected_lang: str = None) -> Dict:
        """
        Procesa el nombre de usuario con mejor manejo de símbolos y caracteres especiales
        """
        try:
            logger.debug(f"Processing username: {text}")
            
            # Detectar idioma si no se proporciona
            if not detected_lang:
                detected_lang = self._detect_language(text)
            logger.debug(f"Detected language: {detected_lang}")

            # Procesar con GPT-4
            processed_text = self._process_with_gpt4(text)
            
            # Transliterar si es necesario
            if detected_lang in ['ru', 'ja', 'zh', 'ko']:
                processed_text = self._transliterate_text(processed_text, detected_lang)
            
            # Limpiar y formatear
            final_username = self._clean_username(processed_text)
            
            # Validación final
            if not self._validate_username_format(final_username):
                return {
                    'success': False,
                    'error': 'Invalid username format',
                    'original': text
                }

            return {
                'success': True,
                'username': final_username,
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

    def process_email(self, username_part: str, domain_part: str) -> Dict:
        """
        Procesa un email completo con mejor manejo de idiomas y formatos
        """
        try:
            # Detectar idiomas
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

            # Construir y validar email completo
            email = f"{username_result['username']}@{domain_result['domain']}"
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
    def process_domain(self, text: str, detected_lang: str = None) -> Dict:
        """
        Procesa el dominio con mejor manejo de formatos internacionales
        """
        try:
            logger.debug(f"Processing domain: {text}")
            
            if not detected_lang:
                detected_lang = self._detect_language(text)
            logger.debug(f"Detected language: {detected_lang}")

            cleaned_text = self._clean_text(text)
            processed_text = self._process_domain_symbols(cleaned_text, detected_lang)
            
            # Verificar si es un dominio común
            common_domain = self._get_common_domain(processed_text, detected_lang)
            if common_domain:
                return {
                    'success': True,
                    'domain': common_domain,
                    'is_common': True,
                    'original': text,
                    'detected_language': detected_lang
                }

            # Validar formato y estructura
            if not self._validate_domain_structure(processed_text):
                suggestions = self._get_domain_suggestions(processed_text, detected_lang)
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
        Detección de idioma mejorada con patrones y palabras clave
        """
        text_lower = text.lower()

        # Verificar patrones de caracteres específicos
        for lang, info in self.language_patterns.items():
            if re.search(info['pattern'], text):
                return lang
            # Verificar palabras clave del idioma
            if any(keyword in text_lower for keyword in info['keywords']):
                return lang

        # Verificar palabras de símbolos
        for symbol_info in self.symbol_mapping.values():
            for lang, words in symbol_info.items():
                if any(word in text_lower for word in words):
                    return lang

        return 'en'  # Default a inglés

    def _process_domain_symbols(self, text: str, lang: str) -> str:
        """
        Procesamiento específico de símbolos para dominios
        """
        # Primero procesar símbolos normales
        processed = self._process_symbols(text, lang)
        
        # Limpiar formato de dominio
        parts = processed.split('.')
        clean_parts = []
        
        for part in parts:
            # Limpiar cada parte del dominio
            clean_part = re.sub(r'[^\w\-]', '', part)
            if clean_part:
                clean_parts.append(clean_part)
        
        return '.'.join(clean_parts)

    def _process_symbols(self, text: str, lang: str) -> str:
        """
        Procesamiento mejorado de símbolos según el idioma
        """
        words = text.split()
        result = []
        
        for word in words:
            word_lower = word.lower()
            symbol_found = False
            
            # Buscar en todos los símbolos
            for symbol, lang_mappings in self.symbol_mapping.items():
                # Verificar en el idioma específico
                if lang in lang_mappings and any(kw in word_lower for kw in lang_mappings[lang]):
                    result.append(symbol)
                    symbol_found = True
                    break
                
                # Verificar en inglés como respaldo
                if not symbol_found and 'en' in lang_mappings:
                    if any(kw in word_lower for kw in lang_mappings['en']):
                        result.append(symbol)
                        symbol_found = True
                        break
            
            if not symbol_found:
                result.append(word)
        
        return ''.join(result)

    def _transliterate_text(self, text: str, lang: str) -> str:
        """
        Transliteración mejorada según el idioma
        """
        if lang not in ['ru', 'ja', 'zh', 'ko']:
            return text

        result = text
        lang_map = {
            'ru': 'russian',
            'ja': 'japanese',
            'zh': 'chinese',
            'ko': 'korean'
        }

        if lang in lang_map and lang_map[lang] in self.transliteration_map:
            for original, transliterated in self.transliteration_map[lang_map[lang]].items():
                result = result.replace(original, transliterated)

        return unidecode(result.lower())

    def _validate_username_format(self, username: str) -> bool:
        """
        Validación mejorada de formato de username
        """
        if not username:
            return False

        if len(username) > MAX_USERNAME_LENGTH:
            return False

        # Permitir letras, números y símbolos específicos
        if not re.match(r'^[\w\.\-_@]+$', username):
            return False

        # No permitir símbolos al inicio o final
        if re.match(r'^[\.\-_@]|[\.\-_@]$', username):
            return False

        # No permitir símbolos consecutivos
        if re.search(r'[\.\-_@]{2,}', username):
            return False

        # Verificar estructura básica de email si contiene @
        if '@' in username:
            parts = username.split('@')
            if len(parts) != 2 or not all(parts):
                return False

        return True

    def _validate_domain_structure(self, domain: str) -> bool:
        """
        Validación mejorada de estructura de dominio
        """
        if not domain or len(domain) > MAX_DOMAIN_LENGTH:
            return False

        # Validar formato general
        if not re.match(r'^[a-z0-9][a-z0-9\-\.]+[a-z0-9]$', domain):
            return False

        # Validar partes del dominio
        parts = domain.split('.')
        if len(parts) < 2:
            return False

        # Validar cada parte
        for part in parts:
            if len(part) > 63:  # Límite DNS
                return False
            if part.startswith('-') or part.endswith('-'):
                return False
            if not re.match(r'^[a-z0-9\-]+$', part):
                return False

        # Validar TLD
        return self._validate_tld(parts[-1])

    def _validate_tld(self, tld: str) -> bool:
        """
        Valida el TLD (Top Level Domain)
        """
        all_tlds = set()
        for region_tlds in self.international_tlds.values():
            all_tlds.update(region_tlds)
        return tld.lower() in all_tlds

    def _validate_email_format(self, email: str) -> bool:
        """
        Validación mejorada de formato de email
        """
        if not email or '@' not in email:
            return False

        username, domain = email.split('@')

        # Validar longitudes
        if len(username) > MAX_USERNAME_LENGTH:
            return False
        if len(domain) > MAX_DOMAIN_LENGTH:
            return False

        # Validar username
        if not self._validate_username_format(username):
            return False

        # Validar dominio
        if not self._validate_domain_structure(domain):
            return False

        # Validar formato general
        return bool(re.match(EMAIL_REGEX, email))

    def _get_common_domain(self, domain: str, lang: str) -> Optional[str]:
        """
        Búsqueda mejorada de dominios comunes con soporte multilingüe
        """
        domain_lower = domain.lower()

        # Verificar en dominios globales
        for domain_name, variants in self.common_domains['global'].items():
            if any(variant in domain_lower for variant in variants):
                return domain_name

        # Verificar en dominios regionales según el idioma
        region_map = {
            'ru': 'ru',
            'zh': 'cn',
            'ja': 'jp',
            'ko': 'kr'
        }
        
        if lang in region_map:
            region = region_map[lang]
            if region in self.common_domains['regional']:
                for domain_name, variants in self.common_domains['regional'][region].items():
                    if any(variant in domain_lower for variant in variants):
                        return domain_name

        return None

    def _get_domain_suggestions(self, invalid_domain: str, lang: str) -> List[str]:
        """
        Generación mejorada de sugerencias de dominio
        """
        suggestions = set()
        base_name = invalid_domain.split('.')[0]

        # Sugerir dominios comunes globales
        for domain_name, variants in self.common_domains['global'].items():
            if len(base_name) >= 3 and (
                base_name in domain_name or
                domain_name.startswith(base_name)
            ):
                suggestions.add(domain_name)

        # Sugerir dominios regionales según el idioma
        region_map = {
            'ru': 'ru',
            'zh': 'cn',
            'ja': 'jp',
            'ko': 'kr'
        }
        
        if lang in region_map:
            region = region_map[lang]
            if region in self.common_domains['regional']:
                for domain_name, variants in self.common_domains['regional'][region].items():
                    main_domain = variants[0]
                    suggestions.add(domain_name)

        # Sugerir TLDs comunes
        common_tlds = ['com', 'org', 'net']
        for tld in common_tlds:
            suggestion = f"{base_name}.{tld}"
            if self._validate_domain_structure(suggestion):
                suggestions.add(suggestion)

        # Convertir set a lista y limitar cantidad
        return list(suggestions)[:5]

    def get_domain_info(self, domain: str) -> Dict:
        """
        Información detallada mejorada sobre dominios
        """
        try:
            # Detectar idioma
            detected_lang = self._detect_language(domain)
            
            # Procesar dominio
            result = self.process_domain(domain, detected_lang)
            if not result['success']:
                return result

            domain_parts = result['domain'].split('.')
            tld = domain_parts[-1]
            
            # Determinar tipo y región
            domain_type = 'generic'
            domain_region = 'global'
            
            # Verificar TLDs regionales
            for region, tlds in self.international_tlds.items():
                if any(domain.endswith(f".{t}") for t in tlds):
                    domain_type = 'country-specific'
                    domain_region = region
                    break

            # Verificar si es un dominio común
            is_common = bool(self._get_common_domain(domain, detected_lang))

            return {
                'success': True,
                'domain': result['domain'],
                'is_common': is_common,
                'original': domain,
                'detected_language': detected_lang,
                'domain_info': {
                    'type': domain_type,
                    'region': domain_region,
                    'is_common': is_common,
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

    def validate_full_email(self, email: str) -> Dict:
        """
        Validación completa mejorada de email
        """
        try:
            if '@' not in email:
                return {
                    'success': False,
                    'error': 'Email must contain @',
                    'original': email
                }

            username, domain = email.split('@')
            
            # Detectar idiomas
            username_lang = self._detect_language(username)
            domain_lang = self._detect_language(domain)

            return self.process_email(username, domain)

        except Exception as e:
            logger.error(f"Error validating email: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'original': email
            }

    def test_connection(self) -> bool:
        """
        Prueba mejorada de conexión
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