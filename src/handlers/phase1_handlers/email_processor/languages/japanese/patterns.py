from typing import Dict, TypedDict

class JapaneseEmailPattern(TypedDict):
    at_symbols: list[str]
    common_misspellings: list[str]
    dot_symbols: list[str]
    punctuation: str
    context_markers: Dict[str, list[str]]
    grammar_particles: Dict[str, list[str]]
    email_formats: Dict[str, list[str]]

JAPANESE_PATTERNS: JapaneseEmailPattern = {
    # Símbolos para @
    'at_symbols': [
        'アット',
        'アットマーク',
        '@',
        'あっと',
        'アト',
        'アド',
        r'\sat\s'
    ],

    # Errores comunes y variaciones
    'common_misspellings': [
        'あとまーく',
        'アトマーク',
        'アトmark',
        'アッto',
        'アドレス',
        'めーる',
        'メール'
    ],

    # Símbolos para punto
    'dot_symbols': [
        'ドット',
        'どっと',
        '。',
        'てん',
        'テン',
        'どつと',
        'ドツト'
    ],

    # Puntuación japonesa
    'punctuation': '。',

    # Marcadores de contexto
    'context_markers': {
        'start': [
            'は',
            'のメールアドレスは',
            'のアドレスは',
            'のメールは',
            'のメアドは',
            'のアドレス：',
            'のメール：'
        ],
        'end': [
            'です',
            'である',
            'だ',
            'です。',
            'である。',
            'だ。',
            'になります',
            'となります'
        ],
        'email_indicators': [
            'メール',
            'アドレス',
            'メールアドレス',
            'メアド',
            'アド',
            'イーメール',
            'E-メール'
        ]
    },

    # Partículas gramaticales japonesas
    'grammar_particles': {
        'topic_markers': ['は', 'が'],
        'possession_markers': ['の'],
        'connection_markers': ['に', 'へ', 'で', 'と'],
        'ending_particles': ['です', 'だ', 'である']
    },

    # Formatos comunes de email en japonés
    'email_formats': {
        'formal': [
            'メールアドレスは{email}です',
            'アドレスは{email}になります',
            '電子メールは{email}となります'
        ],
        'informal': [
            'メアドは{email}だ',
            'アドレスは{email}',
            'メールは{email}'
        ],
        'business': [
            'メールアドレスは{email}でございます',
            '電子メールアドレスは{email}となっております'
        ]
    },

    # Patrones de frase completa
    'full_patterns': {
        'standard': [
            r'(私|わたし|ぼく|僕)の(メール|メアド|アドレス)は\s*(.+?)\s*(です|だ|である)',
            r'(メール|メアド|アドレス)は\s*(.+?)\s*(です|だ|である)',
            r'(.+?)(のメール|のメアド|のアドレス)は\s*(.+?)\s*(です|だ|である)'
        ]
    },

    # Indicadores de error comunes
    'error_indicators': {
        'wrong_particles': ['を', 'も', 'や'],
        'wrong_endings': ['でした', 'だった', 'あります'],
        'wrong_formats': ['mail', 'address', 'アドドレス']
    },

    # Caracteres especiales japoneses
    'special_characters': {
        'brackets': ['「', '」', '『', '』'],
        'separators': ['・', '：', '／'],
        'punctuation_marks': ['。', '、', '！', '？']
    }
}

# Funciones auxiliares específicas para japonés
def is_japanese_character(char: str) -> bool:
    """
    Verifica si un carácter es japonés (hiragana, katakana, kanji)
    """
    return any([
        '\u3040' <= char <= '\u309F',  # Hiragana
        '\u30A0' <= char <= '\u30FF',  # Katakana
        '\u4E00' <= char <= '\u9FFF'   # Kanji
    ])

def contains_japanese(text: str) -> bool:
    """
    Verifica si un texto contiene caracteres japoneses
    """
    return any(is_japanese_character(char) for char in text)

def get_japanese_pattern(pattern_type: str) -> list:
    """
    Obtiene un patrón específico del diccionario de patrones japoneses
    """
    return JAPANESE_PATTERNS.get(pattern_type, [])