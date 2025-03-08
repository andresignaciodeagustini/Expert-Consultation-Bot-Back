# test_enhanced_languages.py

from src.handlers.enhanced_username_processor import EnhancedUsernameProcessor
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_new_languages():
    processor = EnhancedUsernameProcessor()

    # Diccionario de pruebas para cada idioma
    test_cases = {
        # Idiomas europeos occidentales
        'nl': {  # Holandés
            'username': "André van der Berg punt onderstrepingsteken",
            'email': "gebruiker@domein.nl"
        },
        'pl': {  # Polaco
            'username': "Łukasz kropka Kowalski",
            'email': "użytkownik@domena.pl"
        },
        'sv': {  # Sueco
            'username': "Björn punkt Andersson",
            'email': "användare@domän.se"
        },
        'no': {  # Noruego
            'username': "Øystein punktum Hansen",
            'email': "bruker@domene.no"
        },
        'fi': {  # Finlandés
            'username': "Päivi piste Virtanen",
            'email': "käyttäjä@verkkotunnus.fi"
        },
        'da': {  # Danés
            'username': "Søren punktum Jensen",
            'email': "bruger@domæne.dk"
        },

        # Idiomas europeos orientales
        'el': {  # Griego
            'username': "Νίκος τελεία Παπαδόπουλος",
            'email': "χρήστης@τομέας.gr"
        },
        'cs': {  # Checo
            'username': "Jiří tečka Novák",
            'email': "uživatel@doména.cz"
        },
        'hu': {  # Húngaro
            'username': "István pont Nagy",
            'email': "felhasználó@tartomány.hu"
        },
        'tr': {  # Turco
            'username': "Mehmet nokta Yılmaz",
            'email': "kullanıcı@alan.tr"
        },

        # Idiomas asiáticos
        'hi': {  # Hindi
            'username': "राजेश बिंदु कुमार",
            'email': "उपयोगकर्ता@डोमेन.in"
        },
        'th': {  # Tailandés
            'username': "สมชาย จุด ใจดี",
            'email': "ผู้ใช้@โดเมน.th"
        },
        'vi': {  # Vietnamita
            'username': "Nguyễn chấm Văn",
            'email': "người_dùng@tênmiền.vn"
        },
        'id': {  # Indonesio
            'username': "Budi titik Santoso",
            'email': "pengguna@domain.id"
        },
        'ms': {  # Malayo
            'username': "Ahmad titik Abdullah",
            'email': "pengguna@domain.my"
        },
        'tl': {  # Tagalo
            'username': "Juan tuldok Cruz",
            'email': "gumagamit@domain.ph"
        },

        # Idiomas RTL
        'ar': {  # Árabe
            'username': "محمد نقطة أحمد",
            'email': "مستخدم@نطاق.sa"
        },
        'he': {  # Hebreo
            'username': "דוד נקודה כהן",
            'email': "משתמש@תחום.il"
        },
        'fa': {  # Persa
            'username': "علی نقطه رضایی",
            'email': "کاربر@دامنه.ir"
        },

        # Idiomas europeos del este adicionales
        'uk': {  # Ucraniano
            'username': "Петро крапка Іваненко",
            'email': "користувач@домен.ua"
        },
        'ro': {  # Rumano
            'username': "Ioan punct Popescu",
            'email': "utilizator@domeniu.ro"
        },
        'bg': {  # Búlgaro
            'username': "Георги точка Димитров",
            'email': "потребител@домейн.bg"
        },
        'hr': {  # Croata
            'username': "Ivan točka Horvat",
            'email': "korisnik@domena.hr"
        },
        'sk': {  # Eslovaco
            'username': "Peter bodka Kováč",
            'email': "používateľ@doména.sk"
        },
        'sl': {  # Esloveno
            'username': "Janez pika Novak",
            'email': "uporabnik@domena.si"
        }
    }

    print("\n=== PRUEBAS DE NUEVOS IDIOMAS ===\n")

    for lang, tests in test_cases.items():
        print(f"\n=== Probando idioma: {lang} ===")
        
        # Probar procesamiento de username
        print(f"\nProcesando username en {lang}:")
        username_result = processor.process_username_enhanced(tests['username'], lang)
        print(f"Input: {tests['username']}")
        print(f"Output: {username_result}")

        # Probar procesamiento de email
        print(f"\nProcesando email en {lang}:")
        email_result = processor.validate_full_email_enhanced(tests['email'])
        print(f"Input: {tests['email']}")
        print(f"Output: {email_result}")

        # Obtener información del idioma
        lang_info = processor.get_language_info(tests['username'])
        print(f"\nInformación del idioma:")
        print(f"Script: {lang_info['script']}")
        print(f"Dirección: {lang_info['direction']}")
        print(f"Características soportadas: {lang_info['supported_features']}")
        
        print("=" * 50)

if __name__ == "__main__":
    test_new_languages()