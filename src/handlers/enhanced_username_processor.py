from typing import Dict, List, Optional, Any
import logging
import re
import unicodedata
from .username_processor import UsernameProcessor
from .enhanced_language_configs import NEW_LANGUAGE_PATTERNS, NEW_LANGUAGE_SETTINGS, INTERNATIONAL_TLDS
import idna
from unidecode import unidecode

logger = logging.getLogger(__name__)

class EnhancedUsernameProcessor(UsernameProcessor):
    """
    Versión mejorada del UsernameProcessor con soporte para idiomas adicionales
    """
    def __init__(self, client=None):
        # Inicializar la clase padre
        super().__init__(client)
        
        # Agregar las nuevas configuraciones
        self.new_language_patterns = NEW_LANGUAGE_PATTERNS
        self.new_language_settings = NEW_LANGUAGE_SETTINGS
        self.international_tlds = INTERNATIONAL_TLDS
        
        # Combinar patrones existentes con nuevos
        self.language_patterns.update(self.new_language_patterns)
        
        # Inicializar mapeos específicos para nuevos idiomas
        self._initialize_enhanced_mappings()

    def _initialize_enhanced_mappings(self):
        """
        Inicializa los mapeos adicionales para los nuevos idiomas
        """
        self.rtl_languages = set(['ar', 'he', 'fa'])
        self.asian_languages = set(['hi', 'th', 'vi', 'id', 'ms', 'tl'])
        self.european_languages = set([
            'nl', 'pl', 'sv', 'no', 'fi', 'da', 'el', 'cs', 
            'hu', 'tr', 'uk', 'ro', 'bg', 'hr', 'sk', 'sl'
        ])

    def process_username_enhanced(self, text: str, detected_lang: str = None) -> Dict:
        """
        Versión mejorada del procesamiento de nombres de usuario
        """
        try:
            logger.debug(f"Processing enhanced username: {text}")
            
            # Detectar idioma si no se proporciona
            if not detected_lang:
                detected_lang = self._detect_language_enhanced(text)
            logger.debug(f"Detected language (enhanced): {detected_lang}")

            # Procesar con GPT-4
            processed_text = self._process_with_gpt4(text)
            
            # Aplicar procesamiento específico según el tipo de idioma
            if detected_lang in self.rtl_languages:
                processed_text = self._process_rtl_text(processed_text, detected_lang)
            elif detected_lang in self.asian_languages:
                processed_text = self._process_asian_text(processed_text, detected_lang)
            elif detected_lang in self.european_languages:
                processed_text = self._process_european_text(processed_text, detected_lang)
            
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
            logger.error(f"Error in enhanced username processing: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'original': text
            }

    def _process_with_gpt4(self, text: str) -> str:
        """
        Procesa el texto usando GPT-4 con manejo mejorado de respuestas
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "Retorna SOLO el nombre de usuario procesado, sin texto adicional."
                    },
                    {
                        "role": "user",
                        "content": f"Procesa este nombre: {text}"
                    }
                ],
                temperature=0.1
            )
            
            processed_text = response.choices[0].message.content.strip()
            # Eliminar cualquier prefijo no deseado
            if processed_text.startswith("el_nombre_"):
                processed_text = processed_text.split("es_")[-1]
            return self._clean_username(processed_text)
        except Exception as e:
            logger.error(f"Error in GPT-4 processing: {str(e)}")
            return text
    def _process_rtl_text(self, text: str, lang: str) -> str:
        """
        Procesa texto para idiomas que se escriben de derecha a izquierda
        """
        try:
            # Normalizar el texto RTL según el idioma
            if lang == 'ar':  # Árabe
                text = self._normalize_arabic(text)
            elif lang == 'he':  # Hebreo
                text = self._normalize_hebrew(text)
            elif lang == 'fa':  # Persa
                text = self._normalize_persian(text)

            # Convertir números a formato occidental
            text = self._convert_rtl_numbers(text)
            
            # Manejar caracteres especiales
            text = self._handle_rtl_special_chars(text, lang)
            
            # Asegurar dirección correcta del texto
            text = self._ensure_rtl_direction(text)
            
            return text
        except Exception as e:
            logger.error(f"Error processing RTL text: {str(e)}")
            return text

    def _process_asian_text(self, text: str, lang: str) -> str:
        """
        Procesa texto para idiomas asiáticos
        """
        try:
            if lang == 'hi':  # Hindi
                text = self._normalize_devanagari(text)
            elif lang == 'th':  # Thai
                text = self._normalize_thai(text)
            elif lang == 'vi':  # Vietnamita
                text = self._normalize_vietnamese(text)
            elif lang in ['id', 'ms']:  # Indonesio/Malayo
                text = self._normalize_indonesian_malay(text)
            elif lang == 'tl':  # Tagalo
                text = self._normalize_tagalog(text)

            # Eliminar diacríticos y normalizar espacios
            text = unicodedata.normalize('NFKD', text)
            text = ''.join(c for c in text if not unicodedata.combining(c))
            text = ' '.join(text.split())

            return text
        except Exception as e:
            logger.error(f"Error processing Asian text: {str(e)}")
            return text

    def _process_european_text(self, text: str, lang: str) -> str:
        """
        Procesa texto para los nuevos idiomas europeos
        """
        try:
            # Normalización específica por idioma
            if lang in ['el']:  # Griego
                text = self._normalize_greek(text)
            elif lang in ['bg', 'uk']:  # Cirílico
                text = self._normalize_cyrillic(text)
            elif lang in ['cs', 'sk', 'hr', 'sl']:  # Idiomas eslavos
                text = self._normalize_slavic(text)
            else:  # Otros idiomas europeos
                text = self._normalize_european(text, lang)

            # Normalización común para todos los idiomas europeos
            text = text.lower()
            text = self._remove_diacritics(text)
            text = self._normalize_spaces(text)

            return text
        except Exception as e:
            logger.error(f"Error processing European text: {str(e)}")
            return text

    def _detect_language_enhanced(self, text: str) -> str:
        """
        Detección mejorada de idioma con soporte para nuevos idiomas
        """
        text_lower = text.lower()

        # Verificar idiomas RTL primero
        for lang in self.rtl_languages:
            pattern = self.new_language_patterns[lang]['pattern']
            if re.search(pattern, text):
                return lang

        # Verificar idiomas asiáticos
        for lang in self.asian_languages:
            pattern = self.new_language_patterns[lang]['pattern']
            if re.search(pattern, text):
                return lang

        # Verificar idiomas europeos
        for lang in self.european_languages:
            pattern = self.new_language_patterns[lang]['pattern']
            if re.search(pattern, text):
                return lang

        # Verificar palabras clave
        for lang, config in self.new_language_patterns.items():
            if any(keyword in text_lower for keyword in config['keywords']):
                return lang

        return 'en'  # Default a inglés si no se detecta ningún idioma específico
    def _normalize_arabic(self, text: str) -> str:
        """
        Normaliza texto árabe
        """
        normalization_map = {
            'أ': 'ا', 'إ': 'ا', 'آ': 'ا',  # Variantes de Alef
            'ة': 'ه',  # Taa Marbutah a Haa
            'ى': 'ي',  # Alef Maksura a Yaa
            'ؤ': 'و',  # Waw Hamza a Waw
            'ئ': 'ي',  # Yaa Hamza a Yaa
            'ء': '',   # Eliminar Hamza independiente
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }
        for original, normalized in normalization_map.items():
            text = text.replace(original, normalized)
        return text

    def _normalize_hebrew(self, text: str) -> str:
        """
        Normaliza texto hebreo
        """
        hebrew_map = {
            'ך': 'כ',  # Final Kaf a Kaf
            'ם': 'מ',  # Final Mem a Mem
            'ן': 'נ',  # Final Nun a Nun
            'ף': 'פ',  # Final Pe a Pe
            'ץ': 'צ',  # Final Tsadi a Tsadi
            'ײ': 'יי', # Double Yod
            'װ': 'וו', # Double Vav
            'ױ': 'וי'  # Vav Yod
        }
        for original, normalized in hebrew_map.items():
            text = text.replace(original, normalized)
        return text

    def _normalize_persian(self, text: str) -> str:
        """
        Normaliza texto persa
        """
        persian_map = {
            'ك': 'ک',  # Arabic Kaf a Persian Kaf
            'ي': 'ی',  # Arabic Yeh a Persian Yeh
            'أ': 'ا',  # Alef con Hamza arriba a Alef
            'إ': 'ا',  # Alef con Hamza abajo a Alef
            'ۀ': 'ه',  # Heh con Yeh arriba a Heh
            '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
            '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
        }
        for original, normalized in persian_map.items():
            text = text.replace(original, normalized)
        return text

    def _normalize_greek(self, text: str) -> str:
        """
        Normaliza texto griego
        """
        greek_map = {
            'ά': 'α', 'έ': 'ε', 'ή': 'η', 'ί': 'ι', 'ό': 'ο', 'ύ': 'υ', 'ώ': 'ω',
            'Ά': 'Α', 'Έ': 'Ε', 'Ή': 'Η', 'Ί': 'Ι', 'Ό': 'Ο', 'Ύ': 'Υ', 'Ώ': 'Ω',
            'ϊ': 'ι', 'ϋ': 'υ', 'ΐ': 'ι', 'ΰ': 'υ',
            'ς': 'σ'  # Final sigma a sigma regular
        }
        for original, normalized in greek_map.items():
            text = text.replace(original, normalized)
        return text.lower()

    def _normalize_cyrillic(self, text: str) -> str:
        """
        Normaliza texto cirílico (búlgaro y ucraniano)
        """
        cyrillic_map = {
            # Búlgaro
            'ѝ': 'и', 'ѣ': 'е', 'ѫ': 'ъ', 'ѭ': 'ю',
            # Ucraniano
            'ґ': 'г', 'є': 'е', 'і': 'и', 'ї': 'и',
            'Ґ': 'Г', 'Є': 'Е', 'І': 'И', 'Ї': 'И'
        }
        for original, normalized in cyrillic_map.items():
            text = text.replace(original, normalized)
        return text.lower()

    def _normalize_slavic(self, text: str) -> str:
        """
        Normaliza texto para idiomas eslavos
        """
        slavic_map = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ý': 'y', 'č': 'c', 'ď': 'd', 'ě': 'e', 'ň': 'n',
            'ř': 'r', 'š': 's', 'ť': 't', 'ž': 'z',
            'ĺ': 'l', 'ľ': 'l', 'ŕ': 'r', 'ů': 'u',
            'ä': 'a', 'ô': 'o', 'ć': 'c', 'đ': 'd'
        }
        for original, normalized in slavic_map.items():
            text = text.replace(original, normalized)
        return text.lower()

    def _remove_diacritics(self, text: str) -> str:
        """
        Elimina diacríticos manteniendo caracteres base
        """
        return ''.join(c for c in unicodedata.normalize('NFKD', text)
                      if not unicodedata.combining(c))

    def _normalize_spaces(self, text: str) -> str:
        """
        Normaliza espacios y caracteres de separación
        """
        # Reemplazar múltiples espacios con uno solo
        text = ' '.join(text.split())
        # Reemplazar espacios con guiones bajos
        text = text.replace(' ', '_')
        # Eliminar caracteres de control y espacios especiales
        text = ''.join(char for char in text if char.isprintable())
        return text

    def _convert_rtl_numbers(self, text: str) -> str:
        """
        Convierte números en idiomas RTL a números occidentales
        """
        number_map = {
            # Números árabes
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
            # Números persas
            '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
            '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
        }
        for original, western in number_map.items():
            text = text.replace(original, western)
        return text

    def _handle_rtl_special_chars(self, text: str, lang: str) -> str:
        """
        Maneja caracteres especiales en idiomas RTL
        """
        special_chars_map = {
            'ar': {
                '،': ',',  # Coma árabe
                '؛': ';',  # Punto y coma árabe
                '؟': '?',  # Signo de interrogación árabe
                '٪': '%',  # Símbolo de porcentaje árabe
                '٫': '.',  # Punto decimal árabe
                '٬': ',',  # Separador de miles árabe
                '﴾': '(',  # Paréntesis árabe
                '﴿': ')'   # Paréntesis árabe
            },
            'he': {
                '״': '"',  # Comillas hebreas
                '׳': "'",  # Apóstrofe hebreo
                '־': '-'   # Guión hebreo
            },
            'fa': {
                '،': ',',  # Coma persa
                '؛': ';',  # Punto y coma persa
                '؟': '?',  # Signo de interrogación persa
                '٫': '.',  # Punto decimal persa
                '٬': ','   # Separador de miles persa
            }
        }
        
        if lang in special_chars_map:
            for original, replacement in special_chars_map[lang].items():
                text = text.replace(original, replacement)
        return text

    def _ensure_rtl_direction(self, text: str) -> str:
        """
        Asegura la dirección correcta del texto RTL
        """
        # Agregar marcadores de dirección RTL si no están presentes
        if any(ord(c) >= 0x0591 and ord(c) <= 0x08FF for c in text):
            if not text.startswith('\u200F'):
                text = '\u200F' + text
            if not text.endswith('\u200F'):
                text = text + '\u200F'
        return text

    def _validate_enhanced_username_format(self, username: str, lang: str) -> bool:
        """
        Validación mejorada de formato de nombre de usuario con consideraciones específicas del idioma
        """
        if not username:
            return False

        # Verificar longitud
        if len(username) > self.MAX_USERNAME_LENGTH:
            return False

        # Validaciones específicas por tipo de idioma
        if lang in self.rtl_languages:
            # Verificar que no haya mezcla incorrecta de direcciones
            if self._has_mixed_rtl_ltr(username):
                return False
        
        elif lang in self.asian_languages:
            # Verificar caracteres asiáticos válidos
            if not self._validate_asian_chars(username, lang):
                return False

        # Validaciones generales
        return self._validate_common_requirements(username)
    def _validate_common_requirements(self, username: str) -> bool:
        """
        Valida requisitos comunes para todos los nombres de usuario
        """
        # No permitir caracteres especiales al inicio o final
        if re.match(r'^[._-]|[._-]$', username):
            return False

        # No permitir caracteres especiales consecutivos
        if re.search(r'[._-]{2,}', username):
            return False

        # Verificar caracteres permitidos
        allowed_pattern = r'^[\w._-]+$'
        if not re.match(allowed_pattern, username):
            return False

        return True

    def _has_mixed_rtl_ltr(self, text: str) -> bool:
        """
        Verifica si hay mezcla incorrecta de texto RTL y LTR
        """
        rtl_chars = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\u0590-\u05FF]')
        ltr_chars = re.compile(r'[a-zA-Z]')
        
        has_rtl = bool(rtl_chars.search(text))
        has_ltr = bool(ltr_chars.search(text))
        
        # Permitir números y símbolos especiales
        if has_rtl and has_ltr:
            # Verificar si la mezcla es válida
            valid_mixed_patterns = [
                r'^[a-zA-Z0-9_.-]+$',  # Patrón occidental estándar
                r'^[\u0600-\u06FF0-9_.-]+$'  # Patrón árabe/persa estándar
            ]
            return not any(re.match(pattern, text) for pattern in valid_mixed_patterns)
        
        return False

    def _validate_asian_chars(self, text: str, lang: str) -> bool:
        """
        Valida caracteres para idiomas asiáticos
        """
        valid_patterns = {
            'hi': r'[\u0900-\u097F\w.-]+$',  # Devanagari y caracteres latinos
            'th': r'[\u0E00-\u0E7F\w.-]+$',  # Thai y caracteres latinos
            'vi': r'[a-zA-Z0-9àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ._-]+$',
            'id': r'[\w.-]+$',  # Caracteres latinos básicos
            'ms': r'[\w.-]+$',  # Caracteres latinos básicos
            'tl': r'[\w.-]+$'   # Caracteres latinos básicos
        }
        
        if lang in valid_patterns:
            return bool(re.match(valid_patterns[lang], text))
        return True

    def get_language_info(self, text: str) -> Dict:
        """
        Obtiene información detallada sobre el idioma detectado
        """
        detected_lang = self._detect_language_enhanced(text)
        
        language_info = {
            'code': detected_lang,
            'script': 'latin',
            'direction': 'ltr',
            'supported_features': []
        }

        if detected_lang in self.rtl_languages:
            language_info['direction'] = 'rtl'
            language_info['script'] = 'arabic' if detected_lang == 'ar' else 'hebrew' if detected_lang == 'he' else 'persian'
        elif detected_lang in self.asian_languages:
            language_info['script'] = self._get_asian_script(detected_lang)
        
        language_info['supported_features'] = self._get_supported_features(detected_lang)
        
        return language_info

    def _get_asian_script(self, lang: str) -> str:
        """
        Determina el sistema de escritura para idiomas asiáticos
        """
        script_map = {
            'hi': 'devanagari',
            'th': 'thai',
            'vi': 'latin_extended',
            'id': 'latin',
            'ms': 'latin',
            'tl': 'latin'
        }
        return script_map.get(lang, 'unknown')

    def _get_supported_features(self, lang: str) -> List[str]:
        """
        Retorna las características soportadas para un idioma específico
        """
        features = ['basic_latin']
        
        if lang in self.rtl_languages:
            features.extend(['rtl_support', 'number_conversion', 'special_chars'])
        elif lang in self.asian_languages:
            features.extend(['transliteration', 'diacritic_handling'])
        elif lang in self.european_languages:
            features.extend(['diacritic_handling', 'extended_latin'])
            
        if lang in self.new_language_patterns:
            features.extend([
                'enhanced_validation',
                'script_detection',
                'local_domain_support'
            ])
            
        return features