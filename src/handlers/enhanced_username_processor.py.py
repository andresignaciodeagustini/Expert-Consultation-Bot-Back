from typing import Dict, List, Optional, Any
import logging
from .username_processor import UsernameProcessor
from .enhanced_language_configs import NEW_LANGUAGE_PATTERNS, NEW_LANGUAGE_SETTINGS
import re
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

    def _detect_language_enhanced(self, text: str) -> str:
        """
        Versión mejorada de detección de idioma que incluye los nuevos idiomas
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

        # Verificar palabras clave en todos los nuevos idiomas
        for lang, config in self.new_language_patterns.items():
            if any(keyword in text_lower for keyword in config['keywords']):
                return lang

        # Si no se encuentra ningún patrón nuevo, usar el detector original
        return super()._detect_language(text)
    def _process_rtl_text(self, text: str, lang: str) -> str:
        """
        Procesa texto para idiomas que se escriben de derecha a izquierda
        """
        try:
            # Normalizar el texto RTL
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

            return text
        except Exception as e:
            logger.error(f"Error processing European text: {str(e)}")
            return text

    def _normalize_arabic(self, text: str) -> str:
        """
        Normaliza texto árabe
        """
        # Normalizar alefs y hamzas
        normalization_map = {
            'أ': 'ا', 'إ': 'ا', 'آ': 'ا',
            'ة': 'ه',
            'ى': 'ي',
            'ؤ': 'و'
        }
        for original, normalized in normalization_map.items():
            text = text.replace(original, normalized)
        return text

    def _normalize_hebrew(self, text: str) -> str:
        """
        Normaliza texto hebreo
        """
        # Normalizar caracteres finales
        final_chars = {
            'ך': 'כ', 'ם': 'מ', 'ן': 'נ',
            'ף': 'פ', 'ץ': 'צ'
        }
        for final, regular in final_chars.items():
            text = text.replace(final, regular)
        return text

    def _normalize_persian(self, text: str) -> str:
        """
        Normaliza texto persa
        """
        # Normalizar caracteres persas específicos
        persian_map = {
            'ك': 'ک',
            'ي': 'ی',
            'أ': 'ا',
            'إ': 'ا',
            'ۀ': 'ه'
        }
        for original, normalized in persian_map.items():
            text = text.replace(original, normalized)
        return text
    def _normalize_devanagari(self, text: str) -> str:
        """
        Normaliza texto en hindi (devanagari)
        """
        # Mapa de normalización para hindi
        devanagari_map = {
            'ऩ': 'न', 'ऱ': 'र', 'ऴ': 'ळ',
            'क़': 'क', 'ख़': 'ख', 'ग़': 'ग',
            'ज़': 'ज', 'ड़': 'ड', 'ढ़': 'ढ',
            'फ़': 'फ', 'य़': 'य'
        }
        for original, normalized in devanagari_map.items():
            text = text.replace(original, normalized)
        return text

    def _normalize_thai(self, text: str) -> str:
        """
        Normaliza texto tailandés
        """
        # Normalizar tonos y diacríticos
        tone_marks = ['่', '้', '๊', '๋', '์']
        for mark in tone_marks:
            text = text.replace(mark, '')
        return text

    def _normalize_vietnamese(self, text: str) -> str:
        """
        Normaliza texto vietnamita
        """
        vietnamese_map = {
            'à': 'a', 'á': 'a', 'ạ': 'a', 'ả': 'a', 'ã': 'a',
            'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ậ': 'a', 'ẩ': 'a', 'ẫ': 'a',
            'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ặ': 'a', 'ẳ': 'a', 'ẵ': 'a',
            'è': 'e', 'é': 'e', 'ẹ': 'e', 'ẻ': 'e', 'ẽ': 'e',
            'ê': 'e', 'ề': 'e', 'ế': 'e', 'ệ': 'e', 'ể': 'e', 'ễ': 'e',
            'ì': 'i', 'í': 'i', 'ị': 'i', 'ỉ': 'i', 'ĩ': 'i',
            'ò': 'o', 'ó': 'o', 'ọ': 'o', 'ỏ': 'o', 'õ': 'o',
            'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ộ': 'o', 'ổ': 'o', 'ỗ': 'o',
            'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ợ': 'o', 'ở': 'o', 'ỡ': 'o',
            'ù': 'u', 'ú': 'u', 'ụ': 'u', 'ủ': 'u', 'ũ': 'u',
            'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ự': 'u', 'ử': 'u', 'ữ': 'u',
            'ỳ': 'y', 'ý': 'y', 'ỵ': 'y', 'ỷ': 'y', 'ỹ': 'y',
            'đ': 'd'
        }
        for original, normalized in vietnamese_map.items():
            text = text.replace(original, normalized)
        return text

    def _normalize_indonesian_malay(self, text: str) -> str:
        """
        Normaliza texto indonesio/malayo
        """
        # Mapa de normalización para indonesio/malayo
        indo_malay_map = {
            'ā': 'a', 'ī': 'i', 'ū': 'u', 'ē': 'e', 'ō': 'o',
            'Ā': 'A', 'Ī': 'I', 'Ū': 'U', 'Ē': 'E', 'Ō': 'O'
        }
        for original, normalized in indo_malay_map.items():
            text = text.replace(original, normalized)
        return text

    def _normalize_tagalog(self, text: str) -> str:
        """
        Normaliza texto tagalo
        """
        tagalog_map = {
            'ñ': 'n', 'Ñ': 'N',
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U'
        }
        for original, normalized in tagalog_map.items():
            text = text.replace(original, normalized)
        return text

    def _normalize_greek(self, text: str) -> str:
        """
        Normaliza texto griego
        """
        greek_map = {
            'ά': 'α', 'έ': 'ε', 'ή': 'η', 'ί': 'ι', 'ό': 'ο', 'ύ': 'υ', 'ώ': 'ω',
            'Ά': 'Α', 'Έ': 'Ε', 'Ή': 'Η', 'Ί': 'Ι', 'Ό': 'Ο', 'Ύ': 'Υ', 'Ώ': 'Ω',
            'ϊ': 'ι', 'ϋ': 'υ', 'ΐ': 'ι', 'ΰ': 'υ'
        }
        for original, normalized in greek_map.items():
            text = text.replace(original, normalized)
        return text

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
        return text

    def _normalize_slavic(self, text: str) -> str:
        """
        Normaliza texto para idiomas eslavos (checo, eslovaco, croata, esloveno)
        """
        slavic_map = {
            # Caracteres compartidos
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ý': 'y', 'č': 'c', 'ď': 'd', 'ě': 'e', 'ň': 'n',
            'ř': 'r', 'š': 's', 'ť': 't', 'ž': 'z',
            # Caracteres específicos
            'ĺ': 'l', 'ľ': 'l', 'ŕ': 'r', 'ů': 'u',
            'ä': 'a', 'ô': 'o',
            'ć': 'c', 'đ': 'd'
        }
        for original, normalized in slavic_map.items():
            text = text.replace(original, normalized)
        return text

    def _normalize_european(self, text: str, lang: str) -> str:
        """
        Normaliza texto para otros idiomas europeos
        """
        european_maps = {
            'nl': {  # Holandés
                'ä': 'a', 'ë': 'e', 'ï': 'i', 'ö': 'o', 'ü': 'u',
                'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u'
            },
            'pl': {  # Polaco
                'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
                'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'
            },
            'sv': {  # Sueco
                'å': 'a', 'ä': 'a', 'ö': 'o'
            },
            'no': {  # Noruego
                'æ': 'ae', 'ø': 'o', 'å': 'a'
            },
            'fi': {  # Finlandés
                'ä': 'a', 'ö': 'o', 'å': 'a'
            },
            'da': {  # Danés
                'æ': 'ae', 'ø': 'o', 'å': 'a'
            }
        }
        
        if lang in european_maps:
            for original, normalized in european_maps[lang].items():
                text = text.replace(original, normalized)
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

            # Aplicar procesamiento específico según el tipo de idioma
            if detected_lang in self.rtl_languages:
                processed_text = self._process_rtl_text(text, detected_lang)
            elif detected_lang in self.asian_languages:
                processed_text = self._process_asian_text(text, detected_lang)
            elif detected_lang in self.european_languages:
                processed_text = self._process_european_text(text, detected_lang)
            else:
                # Usar procesamiento original para otros idiomas
                return super().process_username(text, detected_lang)

            # Limpieza final y validación
            final_username = self._clean_username(processed_text)
            
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

        # Validaciones generales mejoradas
        if not self._validate_common_requirements(username):
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
            # Verificar si la mezcla es válida (por ejemplo, en nombres de usuario técnicos)
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

    def suggest_username_alternatives(self, text: str, lang: str) -> List[str]:
        """
        Sugiere alternativas para nombres de usuario basadas en el idioma
        """
        suggestions = []
        base_text = self._clean_text(text)

        # Variante transliterada
        if lang in self.rtl_languages or lang in self.asian_languages:
            transliterated = self._transliterate_text(base_text, lang)
            suggestions.append(transliterated)

        # Variante con números
        if len(base_text) > 3:
            suggestions.append(f"{base_text}123")
            suggestions.append(f"{base_text}01")

        # Variante con guiones bajos
        if ' ' in text:
            underscored = text.replace(' ', '_').lower()
            suggestions.append(underscored)

        # Variante con punto
        if len(base_text) > 3:
            parts = base_text.split()
            if len(parts) > 1:
                suggestions.append('.'.join(parts).lower())

        return list(set(suggestions))[:5]  # Eliminar duplicados y limitar a 5 sugerencias

    def validate_full_email_enhanced(self, email: str) -> Dict:
        """
        Validación mejorada de email completo con soporte multilingüe
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
            username_lang = self._detect_language_enhanced(username)
            domain_lang = self._detect_language_enhanced(domain)

            # Procesar username con el nuevo procesador
            username_result = self.process_username_enhanced(username, username_lang)
            if not username_result['success']:
                return username_result

            # Procesar domain
            domain_result = self.process_domain(domain, domain_lang)
            if not domain_result['success']:
                return {
                    'success': False,
                    'error': domain_result['error'],
                    'username': username_result['username'],
                    'domain': domain_result.get('processed_domain', ''),
                    'suggestions': domain_result.get('suggestions', [])
                }

            return {
                'success': True,
                'email': f"{username_result['username']}@{domain_result['domain']}",
                'username': username_result['username'],
                'domain': domain_result['domain'],
                'username_language': username_lang,
                'domain_language': domain_lang,
                'original': email
            }

        except Exception as e:
            logger.error(f"Error in enhanced email validation: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'original': email
            }
