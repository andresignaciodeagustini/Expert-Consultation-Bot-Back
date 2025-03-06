import sys
from pathlib import Path
import os
import re
from dotenv import load_dotenv
from datetime import datetime 
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from waitress import serve
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage, MultiDict
import traceback  


# Configuración de rutas del proyecto
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Importaciones del proyecto después de configurar sys.path
from src.handlers.phase1_handlers.email_handler import handle_email_capture
from src.handlers.phase2_handlers.sector_handler import handle_sector_capture
from src.handlers.phase2_handlers.geography_handler import handle_geography_capture
from src.handlers.voice_handler import VoiceHandler
from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.external.zoho_services import ZohoService
from src.utils.config import VALID_SECTORS
from src.routes.ai.voiceRoutes import voice_routes

load_dotenv()
ZOHO_RECRUIT_ACCESS_TOKEN = os.getenv('ZOHO_RECRUIT_ACCESS_TOKEN')

LAST_DETECTED_LANGUAGE = None

def get_env_path():
    return Path(__file__).parent.parent / '.env'

# Configuración inicial
print("\n=== Environment Setup ===")
env_path = get_env_path()
print(f"Project Root: {project_root}")
print(f"Env file path: {env_path}")
print(f"Env file exists: {env_path.exists()}")

# Carga las variables de entorno
load_dotenv(env_path)

# Verifica el token de Recruit
recruit_token = os.getenv('ZOHO_RECRUIT_ACCESS_TOKEN')

print(f"\n=== Token Verification ===")
print(f"Recruit Token loaded: {recruit_token[:10]}...{recruit_token[-10:] if recruit_token else 'None'}")

# Prueba el token de Recruit
def test_tokens():
    try:
        if recruit_token:
            recruit_test_url = "https://recruit.zoho.com/recruit/v2/Candidates"
            recruit_headers = {
                'Authorization': f'Zoho-oauthtoken {recruit_token}'
            }
            print("\nTesting Recruit token with Zoho API...")
            recruit_response = requests.get(recruit_test_url, headers=recruit_headers)
            print(f"Recruit Test response status: {recruit_response.status_code}")
            if recruit_response.status_code != 200:
                print(f"Recruit Token test failed: {recruit_response.text}")
                print("WARNING: Recruit functionality may not work correctly")

    except Exception as e:
        print(f"Error testing tokens: {str(e)}")

# Ejecutar prueba de tokens
test_tokens()

# Inicialización de Flask
app = Flask(__name__)

# Configuración de CORS
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://expert-consultation-bot-front.vercel.app",
            "https://expert-consultation-bot-front-isej4yvne.vercel.app",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:3000"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Registro de blueprints
app.register_blueprint(voice_routes, url_prefix='/api/ai/voice')

print("\n=== Initializing Services ===")
zoho_service = ZohoService()
voice_handler = VoiceHandler()
chatgpt = ChatGPTHelper()

@app.route('/refresh-token', methods=['POST'])
def refresh_token():
    try:
        refresh_url = "https://accounts.zoho.com/oauth/v2/token"
        refresh_token = os.getenv('ZOHO_RECRUIT_REFRESH_TOKEN')
        token_env_key = 'ZOHO_RECRUIT_ACCESS_TOKEN'
        scope = 'ZohoRecruit.modules.ALL'

        params = {
            'refresh_token': refresh_token,
            'client_id': os.getenv('ZOHO_CLIENT_ID'),
            'client_secret': os.getenv('ZOHO_CLIENT_SECRET'),
            'grant_type': 'refresh_token',
            'scope': scope
        }
        
        print("\n=== Refreshing Recruit Token ===")
        print(f"Using refresh token: {refresh_token[:10]}...")
        
        response = requests.post(refresh_url, params=params)
        print(f"Refresh response status: {response.status_code}")
        
        if response.status_code == 200:
            new_token = response.json().get('access_token')
            
            global recruit_token
            recruit_token = new_token
            zoho_service.recruit_access_token = new_token
            
            # Actualizar en Vercel si estamos en producción
            if os.getenv('ENVIRONMENT') == 'production':
                vercel_api_url = f"https://api.vercel.com/v1/projects/{os.getenv('VERCEL_PROJECT_ID')}/env"
                headers = {
                    'Authorization': f'Bearer {os.getenv("VERCEL_TOKEN")}'
                }
                data = {
                    'key': token_env_key,
                    'value': new_token,
                    'target': ['production']
                }
                
                print("\n=== Updating Vercel Environment ===")
                vercel_response = requests.post(vercel_api_url, headers=headers, json=data)
                print(f"Vercel update status: {vercel_response.status_code}")
            
            # Actualizar archivo .env local si estamos en desarrollo
            else:
                try:
                    env_path = get_env_path()
                    with open(env_path, 'r') as file:
                        lines = file.readlines()
                    
                    with open(env_path, 'w') as file:
                        for line in lines:
                            if line.startswith(f'{token_env_key}='):
                                file.write(f'{token_env_key}={new_token}\n')
                            else:
                                file.write(line)
                    print("\n=== Updated local .env file for Recruit ===")
                except Exception as e:
                    print(f"Error updating .env file: {str(e)}")
            
            return jsonify({
                'success': True,
                'message': 'Recruit Token updated successfully',
                'new_token': new_token[:10] + '...'
            })
            
        return jsonify({
            'success': False,
            'message': f'Failed to refresh Recruit token: {response.text}'
        })
        
    except Exception as e:
        print(f"Error in refresh_token: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


###################################################################################################
######################################FASE 1 !!!!!!!!!!



@app.route('/api/welcome-message', methods=['GET'])
def get_welcome_message():
    try:
        global LAST_DETECTED_LANGUAGE
        print("\n=== Welcome Message Endpoint Started ===")
        print(f"Previous detected language: {LAST_DETECTED_LANGUAGE}")
        
        # Primera opción: ipapi.co
        try:
            print("Attempting primary IP detection (ipapi.co)...")
            response = requests.get('https://ipapi.co/json/', timeout=5)
            data = response.json()
            
            if 'error' in data:
                raise Exception(f"ipapi.co error: {data.get('reason', 'Unknown error')}")
                
            country_code = data.get('country_code', 'US')
            print(f"Successfully detected country from ipapi.co: {country_code}")
            
        except Exception as primary_error:
            print(f"Primary IP detection failed: {str(primary_error)}")
            
            # Segunda opción: ip-api.com
            try:
                print("Attempting secondary IP detection (ip-api.com)...")
                response = requests.get('http://ip-api.com/json/', timeout=5)
                data = response.json()
                
                if data.get('status') == 'success':
                    country_code = data.get('countryCode', 'US')
                    print(f"Successfully detected country from ip-api.com: {country_code}")
                else:
                    raise Exception("ip-api.com detection failed")
                    
            except Exception as secondary_error:
                print(f"Secondary IP detection failed: {str(secondary_error)}")
                
                # Tercera opción: ipinfo.io
                try:
                    print("Attempting tertiary IP detection (ipinfo.io)...")
                    token = os.getenv('IPINFO_TOKEN', 'fallback_token')
                    response = requests.get(f'https://ipinfo.io/json?token={token}', timeout=5)
                    data = response.json()
                    country_code = data.get('country', 'US')
                    print(f"Successfully detected country from ipinfo.io: {country_code}")
                    
                except Exception as tertiary_error:
                    print(f"All IP detection methods failed. Using default US")
                    country_code = 'US'

        print(f"Final detected Country Code: {country_code}")

        # Mapeo extensivo de países a códigos de idioma
        language_map = {
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

            # Francés (fr)
            'FR': 'fr', 'CA-FR': 'fr', 'BE': 'fr', 'CH': 'fr', 'MC': 'fr',
            'LU': 'fr', 'SN': 'fr', 'CI': 'fr', 'ML': 'fr', 'BF': 'fr',
            'NE': 'fr', 'TG': 'fr', 'BJ': 'fr', 'GA': 'fr', 'CG': 'fr',
            'MG': 'fr', 'CM': 'fr', 'DZ': 'fr', 'TN': 'fr', 'MA': 'fr',

            # [Resto del mapeo de idiomas igual...]
        }

        # Obtener el código de idioma correcto
        target_language = language_map.get(country_code, 'en')
        print(f"Mapped language code: {target_language}")

        # Actualizar el idioma global
        LAST_DETECTED_LANGUAGE = target_language
        print(f"Updated LAST_DETECTED_LANGUAGE to: {LAST_DETECTED_LANGUAGE}")

        # Mensajes de bienvenida base en inglés con el nombre de la compañía protegido
        welcome_messages = {
            "greeting": {
                "text": "Welcome to Silverlight Research Expert Network! I'm here to help you find the perfect expert for your needs.",
                "protected_terms": ["Silverlight Research Expert Network"]
            },
            "instruction": "To get started, please provide your email address."
        }

        chatgpt = ChatGPTHelper()
        
        # Si no es inglés, incluir ambas versiones
        if target_language != 'en':
            print(f"Translating messages to language: {target_language}")
            translated_messages = {
                "greeting": {
                    "english": welcome_messages["greeting"]["text"],
                    "translated": chatgpt.translate_message(
                        f"Translate the following keeping 'Silverlight Research Expert Network' unchanged: {welcome_messages['greeting']['text']}",
                        target_language
                    )
                },
                "instruction": {
                    "english": welcome_messages["instruction"],
                    "translated": chatgpt.translate_message(welcome_messages["instruction"], target_language)
                }
            }
        else:
            print("English language detected, using English only")
            translated_messages = {
                "greeting": {
                    "english": welcome_messages["greeting"]["text"]
                },
                "instruction": {
                    "english": welcome_messages["instruction"]
                }
            }
        
        response_data = {
            'success': True,
            'detected_language': target_language,
            'messages': translated_messages,
            'country_code': country_code,
            'is_english_speaking': target_language == 'en',
            'detection_method': 'primary' if 'primary_error' not in locals() else 
                              'secondary' if 'secondary_error' not in locals() else 
                              'tertiary' if 'tertiary_error' not in locals() else 'default'
        }
        
        print("\n=== Welcome Message Response ===")
        print(f"Sending response: {response_data}")
        
        return jsonify(response_data)

    except Exception as e:
        print("\n=== Welcome Message Error ===")
        print(f"Error type: {type(e)}")
        print(f"Error details: {str(e)}")
        print(f"Error location: {e.__traceback__.tb_lineno}")
        
        error_message = "Error generating welcome message"
        if 'chatgpt' in locals():
            error_message = chatgpt.translate_message(
                error_message,
                LAST_DETECTED_LANGUAGE if LAST_DETECTED_LANGUAGE else 'en'
            )
        
        return jsonify({
            'success': False,
            'error': error_message,
            'detected_language': 'en'
        }), 500
   





REGISTERED_TEST_EMAILS = [
    "test@test.com",        # Inglés
    "prueba@prueba.com",      # Español
    "essai@essai.com",       # Francés
    "prova@essai.com",       # Italiano
    "versuch@essai.com",
    "测试@测试.com"      # Alemán
]
def is_email_registered(email: str) -> bool:
    
    return email.lower() in [e.lower() for e in REGISTERED_TEST_EMAILS]





@app.route('/api/ai/email/capture', methods=['POST'])
def capture_email():
    try:
        global LAST_DETECTED_LANGUAGE
        print("\n=== Language Detection Debug ===")
        print(f"Previous detected language: {LAST_DETECTED_LANGUAGE}")
        
        data = request.json
        if 'text' not in data:
            print("Error: Missing 'text' in request")
            return jsonify({
                'success': False,
                'message': 'Text is required'
            }), 400
        
        print(f"Received text: {data['text']}")
        
        chatgpt = ChatGPTHelper()
        print("\n=== Email Extraction ===")
        email_extraction_result = chatgpt.extract_email(data['text'])
        print(f"Email extraction result: {email_extraction_result}")
        
        if not email_extraction_result['success']:
            print("Error: No valid email found")
            return jsonify({
                'success': False,
                'message': 'No valid email found in text'
            }), 400

        email = email_extraction_result['email']
        input_text = data['text']
        print(f"Extracted email: {email}")
        
        # Inicializar ChatGPTHelper
        print("\n=== Language Processing ===")
        chatgpt = ChatGPTHelper()
        text_processing_result = chatgpt.process_text_input(input_text, LAST_DETECTED_LANGUAGE)
        detected_language = text_processing_result.get('detected_language', 'en')
        print(f"Text processing result: {text_processing_result}")
        print(f"Detected language: {detected_language}")
        
        # Actualizar idioma global
        LAST_DETECTED_LANGUAGE = detected_language
        print(f"Updated LAST_DETECTED_LANGUAGE to: {LAST_DETECTED_LANGUAGE}")

        # Verificar si el email está registrado
        print("\n=== Registration Check ===")
        is_registered = is_email_registered(email)
        print(f"Is email registered? {is_registered}")

        # Traducción de mensajes
        print("\n=== Message Translation ===")
        base_message = "Thank you for your email. What is your name?"
        translated_message = chatgpt.translate_message(base_message, detected_language)
        print(f"Translated main message: {translated_message}")

        response = {
            'success': True,
            'email': email,
            'is_registered': is_registered,
            'detected_language': detected_language,
            'step': 'request_name',
            'message': translated_message,
            'next_action': 'provide_name'
        }

        # Solo agregar información de booking si no está registrado
        if not is_registered:
            print("\n=== Booking Information ===")
            booking_base_message = "Please book a call to complete your registration"
            booking_message = chatgpt.translate_message(booking_base_message, detected_language)
            print(f"Translated booking message: {booking_message}")
            
            response.update({
                'action_required': "book_call",
                'booking_link': "https://calendly.com/your-booking-link",
                'booking_message': booking_message
            })

        print("\n=== Final Response ===")
        print(f"Sending response: {response}")
        return jsonify(response)

    except Exception as e:
        print(f"\n=== Error Handling ===")
        print(f"Error in email capture: {str(e)}")
        error_message = "An error occurred while processing your request."
        if 'chatgpt' in locals():
            error_message = chatgpt.translate_message(
                error_message, 
                detected_language if 'detected_language' in locals() else 'en'
            )
        print(f"Translated error message: {error_message}")
        return jsonify({
            'success': False,
            'error': error_message
        }), 500





@app.route('/api/ai/name/capture', methods=['POST'])
def capture_name():
    try:
        global LAST_DETECTED_LANGUAGE
        print("\n=== Language Detection Debug ===")
        print(f"Previous detected language (global): {LAST_DETECTED_LANGUAGE}")
        
        data = request.json
        print(f"Received data: {data}")
        
        if 'text' not in data or 'is_registered' not in data:
            print("Error: Missing required fields")
            return jsonify({
                'success': False,
                'message': 'Text and registration status are required'
            }), 400

        chatgpt = ChatGPTHelper()
        
        # Obtener el idioma anterior del request
        previous_language = LAST_DETECTED_LANGUAGE
        print(f"Language from request: {previous_language}")
        
        print("\n=== Language Processing ===")
        # Procesar el texto con el idioma anterior como referencia
        text_processing_result = chatgpt.process_text_input(data['text'], previous_language)
        detected_language = text_processing_result.get('detected_language', 'en')
        print(f"Text processing result: {text_processing_result}")
        print(f"Detected language: {detected_language}")
        
        # Actualizar idioma global
        LAST_DETECTED_LANGUAGE = detected_language
        print(f"Updated LAST_DETECTED_LANGUAGE to: {LAST_DETECTED_LANGUAGE}")

        print("\n=== Name Extraction ===")
        name_extraction_result = chatgpt.extract_name(data['text'])
        print(f"Name extraction result: {name_extraction_result}")

        if not name_extraction_result['success']:
            print("Error: No valid name found")
            return jsonify({
                'success': False, 
                'message': 'No valid name found in text'
            }), 400

        name = name_extraction_result['name']
        is_registered = data['is_registered']
        print(f"Extracted name: {name}")
        print(f"Is registered: {is_registered}")

        print("\n=== Message Translation ===")
        if is_registered:
            base_message = f"Welcome back {name}! Would you like to connect with our experts?"
            translated_message = chatgpt.translate_message(base_message, detected_language)
            print(f"Translated welcome message: {translated_message}")
            
            yes_option = chatgpt.translate_message("yes", detected_language)
            no_option = chatgpt.translate_message("no", detected_language)
            print(f"Translated options: yes={yes_option}, no={no_option}")

            response = {
                'success': True,
                'name': name,
                'detected_language': detected_language,
                'step': 'ask_expert_connection',
                'message': translated_message,
                'next_action': 'provide_expert_answer',
                'options': [yes_option, no_option]
            }
        else:
            base_message = f"Thank you {name}! To better assist you, we recommend speaking with one of our agents."
            translated_message = chatgpt.translate_message(base_message, detected_language)
            print(f"Translated thank you message: {translated_message}")
            
            booking_message = chatgpt.translate_message(
                "Would you like to schedule a call?",
                detected_language
            )
            print(f"Translated booking message: {booking_message}")

            response = {
                'success': True,
                'name': name,
                'detected_language': detected_language,
                'step': 'propose_agent_contact',
                'message': translated_message,
                'booking_message': booking_message,
                'next_action': 'schedule_call',
                'action_required': 'book_call',
                'booking_link': "https://calendly.com/your-booking-link"
            }

        print("\n=== Final Response ===")
        print(f"Sending response: {response}")
        return jsonify(response)

    except Exception as e:
        print(f"\n=== Error Handling ===")
        print(f"Error in name capture: {str(e)}")
        error_message = "An error occurred while processing your request."
        if 'chatgpt' in locals():
            error_message = chatgpt.translate_message(
                error_message, 
                detected_language if 'detected_language' in locals() else 'en'
            )
        print(f"Translated error message: {error_message}")
        return jsonify({
            'success': False,
            'error': error_message
        }), 500







@app.route('/api/ai/expert-connection/ask', methods=['POST'])
def ask_expert_connection():
    try:
        global LAST_DETECTED_LANGUAGE
        print("\n=== Language Detection Debug ===")
        print(f"Previous detected language (global): {LAST_DETECTED_LANGUAGE}")
        
        data = request.json
        print(f"Received data: {data}")
        
        required_fields = ['text', 'name']
        if not all(field in data for field in required_fields):
            print("Error: Missing required fields")
            return jsonify({
                'success': False,
                'message': 'Required fields missing: text, name'
            }), 400

        text = data['text']
        name = data['name']
        print(f"Processing text: {text}")
        print(f"User name: {name}")

        chatgpt = ChatGPTHelper()
        
        print("\n=== Language Processing ===")
        # Usar el idioma global como referencia
        text_processing_result = chatgpt.process_text_input(text, LAST_DETECTED_LANGUAGE)
        detected_language = text_processing_result.get('detected_language', 'en')
        print(f"Text processing result: {text_processing_result}")
        print(f"Detected language: {detected_language}")
        
        # Actualizar idioma global
        LAST_DETECTED_LANGUAGE = detected_language
        print(f"Updated LAST_DETECTED_LANGUAGE to: {LAST_DETECTED_LANGUAGE}")

        print("\n=== Intention Extraction ===")
        intention_result = chatgpt.extract_intention(text)
        print(f"Intention result: {intention_result}")

        if not intention_result['success']:
            print("Error: Invalid intention")
            translated_error = chatgpt.translate_message(intention_result['error'], detected_language)
            print(f"Translated error: {translated_error}")
            return jsonify({
                'success': False,
                'error': translated_error,
                'step': 'clarify'
            }), 400

        intention = intention_result['intention']
        print(f"Extracted intention: {intention}")

        print("\n=== Response Generation ===")
        if intention == 'yes':
            base_message = f"Excellent! What sector interests you the most? Choose from:\n\n1. Technology\n2. Healthcare\n3. Finance\n4. Education\n5. Other"
            translated_message = chatgpt.translate_message(base_message, detected_language)
            print(f"Translated positive response: {translated_message}")
            
            response = {
                'success': True,
                'name': name,
                'detected_language': detected_language,
                'step': 'select_sector',
                'message': translated_message,
                'next_action': 'process_sector_selection'
            }

        elif intention == 'no':
            base_message = f"I understand, {name}. Feel free to come back when you'd like to connect with our experts. Have a great day!"
            translated_message = chatgpt.translate_message(base_message, detected_language)
            print(f"Translated negative response: {translated_message}")
            
            response = {
                'success': True,
                'name': name,
                'detected_language': detected_language,
                'step': 'farewell',
                'message': translated_message,
                'next_action': 'end_conversation'
            }

        else:  # intention is 'unclear'
            base_message = "I'm not sure if that's a yes or no. Could you please clarify?"
            translated_message = chatgpt.translate_message(base_message, detected_language)
            print(f"Translated unclear response: {translated_message}")
            
            response = {
                'success': True,
                'message': translated_message,
                'detected_language': detected_language,
                'step': 'clarify'
            }

        print("\n=== Final Response ===")
        print(f"Sending response: {response}")
        return jsonify(response)

    except Exception as e:
        print(f"\n=== Error Handling ===")
        print(f"Error in expert connection answer: {str(e)}")
        error_message = "An error occurred while processing your request."
        translated_error = chatgpt.translate_message(
            error_message, 
            detected_language if 'detected_language' in locals() else 'en'
        )
        print(f"Translated error message: {translated_error}")
        return jsonify({
            'success': False,
            'error': translated_error
        }), 500


@app.route('/api/sector-experience', methods=['POST'])
def sector_experience():
    try:
        global LAST_DETECTED_LANGUAGE
        print("\n=== Language Detection Debug ===")
        print(f"Previous detected language (global): {LAST_DETECTED_LANGUAGE}")
        
        data = request.json
        print(f"Received data: {data}")
        
        if 'sector' not in data:
            print("Error: Missing sector specification")
            base_error = 'A sector specification is required'
            return jsonify({
                'success': False,
                'message': base_error
            }), 400

        chatgpt = ChatGPTHelper()
        
        print("\n=== Language Processing ===")
        # Usar el idioma global como referencia
        text_processing_result = chatgpt.process_text_input(data['sector'], LAST_DETECTED_LANGUAGE)
        detected_language = text_processing_result.get('detected_language', 'en')
        print(f"Text processing result: {text_processing_result}")
        print(f"Detected language: {detected_language}")
        
        # Actualizar idioma global
        LAST_DETECTED_LANGUAGE = detected_language
        print(f"Updated LAST_DETECTED_LANGUAGE to: {LAST_DETECTED_LANGUAGE}")
        
        print("\n=== Sector Extraction ===")
        raw_sector_text = data['sector']
        sector = chatgpt.extract_sector(raw_sector_text)
        print(f"Raw sector text: {raw_sector_text}")
        print(f"Extracted sector: {sector}")
        
        if not sector:
            print("Error: Invalid sector")
            error_message = 'Could not identify a valid sector from the provided text'
            translated_error = chatgpt.translate_message(error_message, detected_language)
            print(f"Translated error: {translated_error}")
            return jsonify({
                'success': False,
                'message': translated_error
            }), 400

        print("\n=== Message Translation ===")
        BASE_MESSAGES = {
            'sector_received': "Thank you for specifying the {sector} sector.",
            'ask_region': "Which region are you interested in? (e.g., North America, Europe, Asia, etc.)",
            'processing_error': "Error processing your request"
        }

        base_message = (
            f"{BASE_MESSAGES['sector_received'].format(sector=sector)} "
            f"{BASE_MESSAGES['ask_region']}"
        )
        response_message = chatgpt.translate_message(base_message, detected_language)
        print(f"Base message: {base_message}")
        print(f"Translated message: {response_message}")

        additional_messages = {}
        if 'additional_info' in data:
            print("\n=== Additional Info Processing ===")
            confirmation_message = "Additional information has been registered successfully"
            additional_messages['confirmation'] = chatgpt.translate_message(
                confirmation_message,
                detected_language
            )
            print(f"Additional info present: {data['additional_info']}")
            print(f"Translated confirmation: {additional_messages['confirmation']}")

        response = {
            'success': True,
            'message': response_message,
            'has_additional_info': 'additional_info' in data and bool(data['additional_info']),
            'sector': sector,
            'detected_language': detected_language
        }

        if additional_messages:
            response['additional_messages'] = additional_messages

        print("\n=== Final Response ===")
        print(f"Sending response: {response}")
        return jsonify(response)

    except Exception as e:
        print(f"\n=== Error Handling ===")
        print(f"Error in sector experience: {str(e)}")
        error_message = BASE_MESSAGES['processing_error']
        translated_error = chatgpt.translate_message(error_message, detected_language)
        print(f"Translated error message: {translated_error}")
        return jsonify({
            'success': False,
            'message': translated_error,
            'error': str(e),
            'detected_language': detected_language
        }), 500
    

    
@app.route('/api/ai/test/process-text', methods=['POST'])
def test_process_text():
    try:
        global LAST_DETECTED_LANGUAGE
        
        data = request.json
        if 'text' not in data:
            base_error = 'Text is required'
            return jsonify({
                'success': False,
                'message': base_error
            }), 400

        chatgpt = ChatGPTHelper()
        
        print("\n=== Language Processing ===")
        text_processing_result = chatgpt.process_text_input(data['text'], LAST_DETECTED_LANGUAGE)
        detected_language = text_processing_result.get('detected_language', 'en')
        print(f"Text processing result: {text_processing_result}")
        print(f"Detected language: {detected_language}")
        
        LAST_DETECTED_LANGUAGE = detected_language
        print(f"Updated LAST_DETECTED_LANGUAGE to: {LAST_DETECTED_LANGUAGE}")
        
        print("\n=== Region Extraction ===")
        raw_region_text = data['text']
        region = chatgpt.extract_region(raw_region_text)
        print(f"Raw region text: {raw_region_text}")
        print(f"Extracted region: {region}")
        
        if not region:
            return jsonify({
                'success': False,
                'message': 'Could not identify a valid region from the provided text'
            }), 400

        BASE_MESSAGES = {
            'region_received': "Thank you for specifying the region.",
            'ask_companies': "Are there specific companies where you would like experts to have experience? Please enter the names separated by commas or answer 'no'.",
            'processing_error': "Error processing your request"
        }

        print("\n=== Message Translation ===")
        base_message = (
            f"{BASE_MESSAGES['region_received'].format(region=region)} "
            f"{BASE_MESSAGES['ask_companies']}"
        )
        print(f"Base message: {base_message}")
        next_question = chatgpt.translate_message(base_message, detected_language)
        print(f"Translated next question: {next_question}")

        result = {
            'success': True,
            'processed_region': region,
            'next_question': next_question,
            'detected_language': detected_language
        }

        print("\n=== Final Response ===")
        print(f"Sending response: {result}")
        return jsonify(result)

    except Exception as e:
        print(f"Error in test_process_text: {str(e)}")
        error_message = BASE_MESSAGES['processing_error']
        translated_error = chatgpt.translate_message(error_message, detected_language)
        return jsonify({
            'success': False,
            'message': translated_error,
            'error': str(e),
            'detected_language': detected_language
        }), 500


@app.route('/api/simple-expert-connection', methods=['POST'])
def simple_expert_connection():
    try:
        global LAST_DETECTED_LANGUAGE
        print("\n=== Simple Expert Connection ===")
        
        data = request.json
        print(f"Received data: {data}")
        
        if 'text' not in data:
            return jsonify({
                'success': False,
                'message': 'Text is required'
            }), 400

        chatgpt = ChatGPTHelper()
        
        # Procesar idioma
        text_processing_result = chatgpt.process_text_input(data['text'], LAST_DETECTED_LANGUAGE)
        detected_language = text_processing_result.get('detected_language', 'en')
        LAST_DETECTED_LANGUAGE = detected_language

        # Extraer empresas del texto
        companies_response = chatgpt.process_company_response(data['text'])
        
        if companies_response == "no" or not isinstance(companies_response, dict):
            return jsonify({
                'success': True,
                'message': chatgpt.translate_message(
                    "No specific companies mentioned. We will provide suggestions based on sector and region.",
                    detected_language
                ),
                'preselected_companies': []
            })

        # Obtener las empresas mencionadas
        preselected_companies = companies_response.get('companies', [])
        
        if preselected_companies:
            message = chatgpt.translate_message(
                f"We will include these companies in the main suggestions: {', '.join(preselected_companies)}",
                detected_language
            )
        else:
            message = chatgpt.translate_message(
                "No specific companies identified. We will provide suggestions based on sector and region.",
                detected_language
            )

        result = {
            'success': True,
            'message': message,
            'preselected_companies': preselected_companies,
            'detected_language': detected_language
        }

        print("\n=== Final Response ===")
        print(f"Preselected companies: {preselected_companies}")
        
        return jsonify(result)

    except Exception as e:
        print(f"\n=== Error Handling ===")
        print(f"Error: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/company-suggestions-test', methods=['POST'])
def company_suggestions_test():
    try:
        global LAST_DETECTED_LANGUAGE
        global EXCLUDED_COMPANIES  # Agregar referencia global
        
        data = request.json
        print("\n=== Company Suggestions Request ===")
        print(f"Received data: {data}")
        
        chatgpt = ChatGPTHelper()
        zoho_service = ZohoService()
        
        # Validar datos requeridos
        sector = data.get('sector')
        region = data.get('processed_region') or data.get('region')
        preselected_companies = data.get('preselected_companies', [])

        if not sector or not region:
            return jsonify({
                'success': False,
                'message': 'Sector and region are required',
                'language': LAST_DETECTED_LANGUAGE or 'en-US'
            }), 400

        print(f"\n=== Processing Request ===")
        print(f"Sector: {sector}")
        print(f"Region: {region}")
        print(f"Preselected companies: {preselected_companies}")
        print(f"Excluded companies: {list(EXCLUDED_COMPANIES)}")

        # Obtener sugerencias de ChatGPT incluyendo preseleccionadas y excluidas
        companies_result = chatgpt.get_companies_suggestions(
            sector=sector,
            geography=region,
            preselected_companies=preselected_companies,
            excluded_companies=EXCLUDED_COMPANIES
        )

        if not companies_result['success']:
            return jsonify({
                'success': False,
                'message': companies_result.get('error', 'Error getting company suggestions'),
                'language': LAST_DETECTED_LANGUAGE or 'en-US'
            }), 400

        suggested_companies = companies_result['content']
        print(f"\n=== Companies Generated ===")
        print(f"Suggested companies: {suggested_companies}")

        # Obtener candidatos para verificar empresas en DB
        all_candidates = zoho_service.get_candidates()
        db_companies = set()

        if isinstance(all_candidates, list):
            for candidate in all_candidates:
                current_employer = candidate.get('Current_Employer')
                if current_employer:
                    for company in suggested_companies:
                        if company.lower() in current_employer.lower():
                            db_companies.add(current_employer)
                            break

        # Organizar empresas con el orden de prioridad correcto
        final_companies = []
        
        # 1. Primero las empresas preseleccionadas
        for company in preselected_companies:
            if company not in final_companies and company not in EXCLUDED_COMPANIES:
                final_companies.append(company)

        # 2. Luego las empresas que están en DB (que no fueron preseleccionadas ni excluidas)
        for company in db_companies:
            clean_company = company.strip()
            if not any(preselected.lower() in clean_company.lower() for preselected in preselected_companies):
                if not any(excluded.lower() in clean_company.lower() for excluded in EXCLUDED_COMPANIES):
                    if not any(existing.lower() == clean_company.lower() for existing in final_companies):
                        final_companies.append(clean_company)

        # 3. Finalmente el resto de sugerencias hasta completar 20
        for company in suggested_companies:
            clean_company = company.strip()
            if not any(existing.lower() == clean_company.lower() for existing in final_companies):
                if not any(excluded.lower() in clean_company.lower() for excluded in EXCLUDED_COMPANIES):
                    final_companies.append(clean_company)
                    if len(final_companies) >= 20:
                        break

        # Limitar a 20 empresas
        final_companies = final_companies[:20]

        result = {
            'success': True,
            'message': chatgpt.translate_message(
                "Here are the recommended companies, with verified companies listed first. Do you agree with this list?",
                LAST_DETECTED_LANGUAGE or 'en-US'
            ),
            'companies': final_companies,
            'db_companies_count': len(db_companies),
            'total_companies': len(final_companies),
            'language': LAST_DETECTED_LANGUAGE or 'en-US'
        }

        print("\n=== Final Response ===")
        print(f"Total companies: {len(final_companies)}")
        print(f"DB companies: {len(db_companies)}")
        print(f"Preselected companies: {preselected_companies}")
        print(f"Excluded companies: {list(EXCLUDED_COMPANIES)}")
        
        return jsonify(result)

    except Exception as e:
        print(f"\n=== Error Handling ===")
        print(f"Error: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e),
            'language': LAST_DETECTED_LANGUAGE or 'en-US'
        }), 500

@app.route('/api/process-companies-agreement', methods=['POST'])
def process_companies_agreement():
    try:
        global LAST_DETECTED_LANGUAGE
        print("\n=== Previous Language State ===")
        print(f"Last detected language was: {LAST_DETECTED_LANGUAGE}")
        
        data = request.json
        print(f"Received data: {data}")
        
        if 'text' not in data:
            print("Error: Missing text field")
            return jsonify({
                'success': False,
                'message': 'Text is required'
            }), 400

        chatgpt = ChatGPTHelper()
        
        print("\n=== Language Processing ===")
        # Usar el idioma global como referencia
        text_processing_result = chatgpt.process_text_input(data['text'], LAST_DETECTED_LANGUAGE)
        detected_language = text_processing_result.get('detected_language', 'en')
        print(f"Text processing result: {text_processing_result}")
        print(f"Detected language: {detected_language}")
        
        # Actualizar idioma global
        LAST_DETECTED_LANGUAGE = detected_language
        print(f"Updated LAST_DETECTED_LANGUAGE to: {LAST_DETECTED_LANGUAGE}")
        
        print("\n=== Intention Extraction ===")
        text = data['text']
        intention = chatgpt.extract_intention(text)
        print(f"Extracted intention: {intention}")
        
        if intention is None:
            print("Error: Could not determine intention")
            error_message = 'Could not determine if you agree with the list. Please answer yes or no.'
            translated_error = chatgpt.translate_message(error_message, detected_language)
            print(f"Translated error: {translated_error}")
            return jsonify({
                'success': False,
                'message': translated_error
            }), 400

        BASE_MESSAGES = {
            'positive_response': "Great! Let's proceed with these companies.",
            'negative_response': "I'll help you find different company suggestions.",
            'processing_error': "Error processing your request"
        }

        print("\n=== Response Generation ===")
        is_positive = intention.get('intention', '').lower() == 'yes'
        print(f"Is positive response: {is_positive}")
        
        response_message = BASE_MESSAGES['positive_response'] if is_positive else BASE_MESSAGES['negative_response']
        translated_message = chatgpt.translate_message(response_message, detected_language)
        print(f"Base message: {response_message}")
        print(f"Translated message: {translated_message}")

        result = {
            'success': True,
            'message': translated_message,
            'agreed': intention,
            'detected_language': detected_language
        }

        print("\n=== Final Response ===")
        print(f"Sending response: {result}")
        return jsonify(result)

    except Exception as e:
        print(f"\n=== Error Handling ===")
        print(f"Error in process companies agreement: {str(e)}")
        error_message = BASE_MESSAGES['processing_error']
        translated_error = chatgpt.translate_message(error_message, detected_language)
        print(f"Translated error message: {translated_error}")
        return jsonify({
            'success': False,
            'message': translated_error,
            'error': str(e),
            'detected_language': detected_language
        }), 500
   
   
   
    """"""""""""""""""""""""""""""""""""""""2"""
######################################################################################################
####################################### FASE3##########################################################

@app.route('/api/specify-employment-status', methods=['POST'])
def specify_employment_status():
    try:
        global LAST_DETECTED_LANGUAGE
        print("\n=== Previous Language State ===")
        print(f"Last detected language was: {LAST_DETECTED_LANGUAGE}")
        
        data = request.json
        print(f"Received data: {data}")
        
        chatgpt = ChatGPTHelper()
        zoho_service = ZohoService()  # Inicializar ZohoService

        print("\n=== Language Processing ===")
        if 'status' in data:
            text_processing_result = chatgpt.process_text_input(data['status'], LAST_DETECTED_LANGUAGE)
            detected_language = text_processing_result.get('detected_language', 'en')
            print(f"Text processing result: {text_processing_result}")
            print(f"Detected language: {detected_language}")
            
            LAST_DETECTED_LANGUAGE = detected_language
            print(f"Updated LAST_DETECTED_LANGUAGE to: {LAST_DETECTED_LANGUAGE}")
        else:
            detected_language = LAST_DETECTED_LANGUAGE
            print(f"Using inherited language: {detected_language}")

        BASE_MESSAGES = {
            'ask_preference': "Would you prefer experts who currently work at these companies, who worked there previously, or both options?",
            'status_options': {
                'current': "Thank you, I will search for experts who currently work at these companies",
                'previous': "Thank you, I will search for experts who previously worked at these companies",
                'both': "Thank you, I will search for both current employees and former employees of these companies"
            },
            'normalize_prompt': "Translate this employment preference to one of these options: 'current', 'previous', or 'both': ",
            'invalid_option': "Please select one of the available options: current, previous, or both.",
            'processing_error': "Error processing your response"
        }

        def get_message(message):
            return chatgpt.translate_message(message, detected_language)

        def normalize_status(status_text):
            print(f"\nNormalizing status: {status_text}")
            status_text = status_text.strip().lower()
            
            status_mapping = {
                'current': ['current', 'currently', 'presente', 'actual', 'now', 'present'],
                'previous': ['previous', 'previously', 'former', 'past', 'anterior', 'antes'],
                'both': ['both', 'all', 'todos', 'ambos', 'both options', 'all options']
            }
            
            for status, variants in status_mapping.items():
                if any(variant in status_text for variant in variants):
                    print(f"Matched status: {status}")
                    return status
            
            print("No status match found")
            return None

        if 'status' not in data:
            print("\n=== Initial Question ===")
            translated_question = get_message(BASE_MESSAGES['ask_preference'])
            print(f"Translated initial question: {translated_question}")
            return jsonify({
                'success': True,
                'message': translated_question,
                'has_status': False,
                'detected_language': detected_language
            })

        print("\n=== Status Processing ===")
        status = chatgpt.extract_work_timing(data['status'])
        print(f"Work timing extraction result: {status}")
        
        if not status:
            print("Trying normal normalization")
            user_status = data['status'].strip().lower()
            status = normalize_status(user_status)

            if status is None:
                print("Trying ChatGPT normalization")
                normalize_prompt = BASE_MESSAGES['normalize_prompt'] + data['status']
                normalized_status = chatgpt.translate_message(normalize_prompt, 'en').strip().lower()
                status = normalize_status(normalized_status)
                print(f"ChatGPT normalized status: {status}")

        print("\n=== Response Generation ===")
        if status:
            print(f"Valid status found: {status}")
            
            # Convertir el status a criterios de búsqueda
            if status == 'current':
                search_criteria = "(Candidate_Status:equals:Active)"
            elif status == 'previous':
                search_criteria = "(Candidate_Status:equals:Inactive)"
            else:  # both
                search_criteria = "(Candidate_Status:equals:Active)OR(Candidate_Status:equals:Inactive)"
            
            try:
                print("\n=== Searching Candidates ===")
                print(f"Search Criteria: {search_criteria}")
                
                candidates = zoho_service.search_candidates(search_criteria)
                print(f"Search results: {candidates}")
                
                status_message = BASE_MESSAGES['status_options'][status]
                response_message = get_message(status_message)
                
                result = {
                    'success': True,
                    'message': response_message,
                    'has_status': True,
                    'employment_status': status,
                    'detected_language': detected_language,
                    'candidates': candidates,
                    'search_criteria': search_criteria
                }
            except Exception as zoho_error:
                print(f"Error searching candidates: {str(zoho_error)}")
                status_message = BASE_MESSAGES['status_options'][status]
                response_message = get_message(status_message)
                result = {
                    'success': True,
                    'message': response_message,
                    'has_status': True,
                    'employment_status': status,
                    'detected_language': detected_language,
                    'zoho_error': str(zoho_error)
                }
        else:
            print("Invalid status")
            error_message = get_message(BASE_MESSAGES['invalid_option'])
            print(f"Translated error: {error_message}")
            result = {
                'success': False,
                'message': error_message,
                'has_status': False,
                'detected_language': detected_language
            }
            return jsonify(result), 400

        print("\n=== Final Response ===")
        print(f"Sending response: {result}")
        return jsonify(result)

    except Exception as e:
        print(f"\n=== Error Handling ===")
        print(f"Error in specify employment status: {str(e)}")
        error_message = get_message(BASE_MESSAGES['processing_error'])
        print(f"Translated error message: {error_message}")
        return jsonify({
            'success': False,
            'message': error_message,
            'error': str(e),
            'detected_language': detected_language
        }), 500
    




# Variable global para mantener las empresas excluidas
EXCLUDED_COMPANIES = set()

@app.route('/api/exclude-companies', methods=['POST'])
def exclude_companies():
    try:
        global LAST_DETECTED_LANGUAGE
        global EXCLUDED_COMPANIES
        
        print("\n=== Previous Language State ===")
        print(f"Last detected language was: {LAST_DETECTED_LANGUAGE}")
        
        data = request.json
        print(f"Received data: {data}")
        
        chatgpt = ChatGPTHelper()
        zoho_service = ZohoService()

        print("\n=== Language Processing ===")
        if 'answer' in data:
            text_processing_result = chatgpt.process_text_input(data['answer'], LAST_DETECTED_LANGUAGE)
            detected_language = text_processing_result.get('detected_language', 'en')
            print(f"Text processing result: {text_processing_result}")
            print(f"Detected language: {detected_language}")
            
            LAST_DETECTED_LANGUAGE = detected_language
            print(f"Updated LAST_DETECTED_LANGUAGE to: {detected_language}")
        else:
            detected_language = LAST_DETECTED_LANGUAGE
            print(f"Using inherited language: {detected_language}")

        BASE_MESSAGES = {
            'ask_exclusions': "Are there any companies that should be excluded from the search? Please enter the names separated by commas or answer 'no'.",
            'no_exclusions': "Understood, there are no companies to exclude.",
            'exclusions_confirmed': "Understood, we will exclude the following companies from the search: {companies}",
            'processing_error': "An error occurred while processing your request."
        }

        def get_message(message):
            return chatgpt.translate_message(message, detected_language)

        if 'answer' not in data:
            print("\n=== Initial Question ===")
            initial_message = get_message(BASE_MESSAGES['ask_exclusions'])
            print(f"Translated initial question: {initial_message}")
            return jsonify({
                'success': True,
                'message': initial_message,
                'detected_language': detected_language,
                'has_excluded_companies': False,
                'excluded_companies': None
            })

        print("\n=== Company Response Processing ===")
        processed_response = chatgpt.process_company_response(data['answer'])
        print(f"Processed response: {processed_response}")

        print("\n=== Response Generation ===")
        if processed_response == "no" or data['answer'].lower() in ['no', 'n']:
            print("No companies to exclude")
            base_message = BASE_MESSAGES['no_exclusions']
            excluded_companies = None
            has_excluded_companies = False
            search_criteria = None
            candidates = None
            EXCLUDED_COMPANIES.clear()  # Limpiar exclusiones globales
            
        elif isinstance(processed_response, dict):
            print(f"Companies to exclude: {processed_response['companies']}")
            excluded_companies = processed_response['companies']
            EXCLUDED_COMPANIES.update(excluded_companies)  # Actualizar set global
            
            companies_list = ", ".join(excluded_companies)
            base_message = BASE_MESSAGES['exclusions_confirmed'].format(
                companies=companies_list
            )
            has_excluded_companies = True
            
            # Obtener todas las empresas disponibles de la base de datos
            print("\n=== Getting Available Companies ===")
            all_candidates = zoho_service.get_candidates()
            available_companies = set()
            
            if isinstance(all_candidates, list):
                for candidate in all_candidates:
                    if candidate.get('Current_Employer'):
                        available_companies.add(candidate['Current_Employer'])
                print(f"Found {len(available_companies)} unique companies in database")
            
            # Filtrar excluyendo las empresas especificadas
            included_companies = [
                company for company in available_companies 
                if not any(excluded.lower() in company.lower() for excluded in excluded_companies)
            ]
            
            print(f"\nCompanies after exclusion: {len(included_companies)}")
            
            # Crear criterio de búsqueda
            if included_companies:
                inclusion_criteria = [
                    f"(Current_Employer:contains:{company})" 
                    for company in included_companies
                ]
                search_criteria = "OR".join(inclusion_criteria)
                print(f"\nSearch criteria: {search_criteria}")
                
                try:
                    print("\n=== Searching Candidates ===")
                    candidates = zoho_service.search_candidates(search_criteria)
                    print(f"Found candidates: {len(candidates) if isinstance(candidates, list) else 'Error'}")
                except Exception as zoho_error:
                    print(f"Error searching candidates: {str(zoho_error)}")
                    candidates = {"error": str(zoho_error)}
            else:
                print("No companies available after exclusion")
                candidates = []
                search_criteria = None
        else:
            print("Invalid response format")
            base_message = BASE_MESSAGES['ask_exclusions']
            excluded_companies = None
            has_excluded_companies = False
            search_criteria = None
            candidates = None

        print("\n=== Message Translation ===")
        response_message = get_message(base_message)
        print(f"Base message: {base_message}")
        print(f"Translated message: {response_message}")

        result = {
            'success': True,
            'message': response_message,
            'detected_language': detected_language,
            'has_excluded_companies': has_excluded_companies,
            'excluded_companies': list(EXCLUDED_COMPANIES),  # Convertir set a lista
            'search_criteria': search_criteria,
            'candidates': candidates,
            'included_companies': included_companies if 'included_companies' in locals() else None
        }

        print("\n=== Final Response ===")
        print(f"Sending response: {result}")
        return jsonify(result)

    except Exception as e:
        print(f"\n=== Error Handling ===")
        print(f"Error in exclude companies: {str(e)}")
        error_message = get_message(BASE_MESSAGES['processing_error'])
        print(f"Translated error message: {error_message}")
        return jsonify({
            'success': False,
            'message': error_message,
            'error': str(e),
            'detected_language': detected_language
        }), 500


@app.route('/api/client-perspective', methods=['POST'])
def client_perspective():
    try:
        global LAST_DETECTED_LANGUAGE
        data = request.json
        
        if LAST_DETECTED_LANGUAGE is None:
            LAST_DETECTED_LANGUAGE = 'en-US'
        
        chatgpt = ChatGPTHelper()
        zoho_service = ZohoService()

        if 'answer' in data:
            text_processing_result = chatgpt.process_text_input(data['answer'], LAST_DETECTED_LANGUAGE)
            detected_language = text_processing_result.get('detected_language', 'en-US')
            LAST_DETECTED_LANGUAGE = detected_language
        else:
            detected_language = LAST_DETECTED_LANGUAGE

        if not data.get('answer'):
            return jsonify({
                'success': True,
                'message': chatgpt.translate_message(
                    "Would you like to include client-side companies?",
                    detected_language
                ),
                'detected_language': detected_language,
                'sector': data.get('sector'),
                'region': data.get('region'),
                'stage': 'question'
            })

        intention_result = chatgpt.extract_intention(data['answer'])
        intention = intention_result.get('intention') if intention_result.get('success') else None

        if intention == 'yes':
            client_companies_result = chatgpt.get_client_side_companies(
                sector=data.get('sector', 'Financial Services'),
                geography=data.get('region', 'Europe'),
                excluded_companies=EXCLUDED_COMPANIES
            )
            
            if not client_companies_result['success']:
                return jsonify({
                    'success': False,
                    'message': chatgpt.translate_message(
                        "Error generating client-side companies",
                        detected_language
                    ),
                    'detected_language': detected_language
                }), 400

            return jsonify({
                'success': True,
                'message': chatgpt.translate_message(
                    "Perfect! I will include client-side companies in the search.",
                    detected_language
                ),
                'message_prefix': chatgpt.translate_message(
                    "Here are the recommended companies, with verified companies listed first. Do you agree with this list?",
                    detected_language
                ),
                'detected_language': detected_language,
                'sector': data.get('sector'),
                'region': data.get('region'),
                'suggested_companies': client_companies_result.get('content', []),
                'stage': 'response'
            })
            
        elif intention == 'no':
            return jsonify({
                'success': True,
                'message': chatgpt.translate_message(
                    "Understood. I will not include client-side companies.",
                    detected_language
                ),
                'detected_language': detected_language,
                'sector': data.get('sector'),
                'region': data.get('region'),
                'suggested_companies': [],
                'stage': 'response'
            })
        else:
            return jsonify({
                'success': False,
                'message': chatgpt.translate_message(
                    "Please answer yes or no.",
                    detected_language
                ),
                'detected_language': detected_language
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': chatgpt.translate_message(
                "An error occurred while processing your request.",
                detected_language if 'detected_language' in locals() else 'en-US'
            ),
            'error': str(e),
            'detected_language': detected_language if 'detected_language' in locals() else 'en-US'
        }), 500
    ############################################







@app.route('/api/supply-chain-experience', methods=['POST'])
def supply_chain_experience():
    try:
        global LAST_DETECTED_LANGUAGE
        data = request.json
        
        if LAST_DETECTED_LANGUAGE is None:
            LAST_DETECTED_LANGUAGE = 'en-US'
        
        chatgpt = ChatGPTHelper()
        zoho_service = ZohoService()

        if 'answer' in data:
            text_processing_result = chatgpt.process_text_input(data['answer'], LAST_DETECTED_LANGUAGE)
            detected_language = text_processing_result.get('detected_language', 'en-US')
            LAST_DETECTED_LANGUAGE = detected_language
        else:
            detected_language = LAST_DETECTED_LANGUAGE

        if not data.get('answer'):
            return jsonify({
                'success': True,
                'message': chatgpt.translate_message(
                    "Would you like to include supply chain companies?",
                    detected_language
                ),
                'detected_language': detected_language,
                'sector': data.get('sector'),
                'region': data.get('region'),
                'stage': 'question'
            })

        intention_result = chatgpt.extract_intention(data['answer'])
        intention = intention_result.get('intention') if intention_result.get('success') else None

        if intention == 'yes':
            supply_companies_result = chatgpt.get_supply_chain_companies(
                sector=data.get('sector', 'Financial Services'),
                geography=data.get('region', 'Europe'),
                excluded_companies=EXCLUDED_COMPANIES
            )
            
            if not supply_companies_result['success']:
                return jsonify({
                    'success': False,
                    'message': chatgpt.translate_message(
                        "Error generating supply chain companies",
                        detected_language
                    ),
                    'detected_language': detected_language
                }), 400

            return jsonify({
                'success': True,
                'message': chatgpt.translate_message(
                    "Perfect! I will include supply chain companies in the search.",
                    detected_language
                ),
                'message_prefix': chatgpt.translate_message(
                    "Here are the recommended companies, with verified companies listed first. Do you agree with this list?",
                    detected_language
                ),
                'detected_language': detected_language,
                'sector': data.get('sector'),
                'region': data.get('region'),
                'suggested_companies': supply_companies_result.get('content', []),
                'stage': 'response'
            })
            
        elif intention == 'no':
            return jsonify({
                'success': True,
                'message': chatgpt.translate_message(
                    "Understood. I will not include supply chain companies.",
                    detected_language
                ),
                'detected_language': detected_language,
                'sector': data.get('sector'),
                'region': data.get('region'),
                'suggested_companies': [],
                'stage': 'response'
            })
        else:
            return jsonify({
                'success': False,
                'message': chatgpt.translate_message(
                    "Please answer yes or no.",
                    detected_language
                ),
                'detected_language': detected_language
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': chatgpt.translate_message(
                "An error occurred while processing your request.",
                detected_language if 'detected_language' in locals() else 'en-US'
            ),
            'error': str(e),
            'detected_language': detected_language if 'detected_language' in locals() else 'en-US'
        }), 500

    ###############################################################3









@app.route('/api/evaluation-questions', methods=['POST'])
def evaluation_questions():
    try:
        global LAST_DETECTED_LANGUAGE
        data = request.json
        print("\n=== Evaluation Questions Endpoint ===")
        print("Received data:", data)
        print("Answer received:", data.get('answer', ''))
        
        answer = data.get('answer', '')
        stage = data.get('stage', 'initial_question')  # Obtener el stage actual
        chatgpt = ChatGPTHelper()
        
        # Procesar idioma
        text_processing_result = chatgpt.process_text_input(answer if answer else "test", LAST_DETECTED_LANGUAGE)
        detected_language = text_processing_result.get('detected_language', 'en')
        LAST_DETECTED_LANGUAGE = detected_language
        
        print("Detected language:", detected_language)
        print("Current stage:", stage)

        BASE_MESSAGES = {
            'ask_preference': "Would you like to add evaluation questions for the project?",
            'confirmed_yes': "Excellent!",
            'confirmed_no': "Understood. We will proceed without evaluation questions.",
            'processing_error': "An error occurred while processing your request.",
            'invalid_response': "Could not determine your preference. Please answer yes or no."
        }

        # Si no hay respuesta, enviar pregunta inicial
        if not answer:
            translated_question = chatgpt.translate_message(BASE_MESSAGES['ask_preference'], detected_language)
            return jsonify({
                'success': True,
                'message': translated_question,
                'detected_language': detected_language,
                'stage': 'initial_question'
            })

        # Solo validar sí/no en la etapa inicial
        if stage == 'initial_question':
            normalized_answer = answer.lower().strip()
            if normalized_answer in ['si', 'sí', 'yes', 's', 'y']:
                response_message = chatgpt.translate_message(BASE_MESSAGES['confirmed_yes'], detected_language)
                return jsonify({
                    'success': True,
                    'message': response_message,
                    'detected_language': detected_language,
                    'evaluation_required': True,
                    'answer_received': 'yes',
                    'stage': 'questions'
                })
            elif normalized_answer in ['no', 'n']:
                response_message = chatgpt.translate_message(BASE_MESSAGES['confirmed_no'], detected_language)
                return jsonify({
                    'success': True,
                    'message': response_message,
                    'detected_language': detected_language,
                    'evaluation_required': False,
                    'answer_received': 'no',
                    'stage': 'confirmed'
                })
            else:
                error_message = chatgpt.translate_message(BASE_MESSAGES['invalid_response'], detected_language)
                return jsonify({
                    'success': False,
                    'message': error_message,
                    'detected_language': detected_language,
                    'stage': 'error'
                }), 400
        else:
            # Si estamos en cualquier otra etapa, aceptar la respuesta como pregunta válida
            return jsonify({
                'success': True,
                'message': answer,
                'detected_language': detected_language,
                'stage': 'questions_received',
                'evaluation_required': True,
                'answer_received': answer
            })

    except Exception as e:
        print("Error in evaluation_questions:", str(e))
        error_message = chatgpt.translate_message(BASE_MESSAGES['processing_error'], 
            detected_language if 'detected_language' in locals() else 'en')
        return jsonify({
            'success': False,
            'message': error_message,
            'error': str(e),
            'detected_language': detected_language if 'detected_language' in locals() else 'en'
        }), 500
    




@app.route('/api/evaluation-questions-sections', methods=['POST'])
def evaluation_questions_sections():
    try:
        global LAST_DETECTED_LANGUAGE
        data = request.json
        print("\n=== Evaluation Questions Sections Endpoint ===")
        print("Received data:", data)
        
        chatgpt = ChatGPTHelper()
        detected_language = LAST_DETECTED_LANGUAGE if LAST_DETECTED_LANGUAGE else data.get('language', 'en')
        print("Working with language:", detected_language)

        # Verificar campos requeridos
        required_fields = ['sector', 'region', 'selected_categories']
        if not all(field in data for field in required_fields):
            missing_fields = [field for field in required_fields if field not in data]
            print("Missing required fields:", missing_fields)
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}',
                'detected_language': detected_language
            }), 400

        current_questions = data.get('current_questions', {})
        selected_categories = data.get('selected_categories', {})
        current_category = data.get('current_category')
        answer = data.get('answer')
        client_perspective = data.get('clientPerspective', False)
        supply_chain_perspective = data.get('supplyChainPerspective', False)

        print(f"Processing - Current Category: {current_category}")
        print(f"Current Questions State: {current_questions}")
        print(f"Selected Categories: {selected_categories}")
        print(f"Client Perspective: {client_perspective}")
        print(f"Supply Chain Perspective: {supply_chain_perspective}")

        if current_category and answer:
            print(f"Saving answer for {current_category}")
            current_questions[current_category] = answer

        # Determinar categorías pendientes basado en las respuestas del usuario
        pending_categories = []
        
        # Siempre incluir 'main' si está seleccionado y no tiene respuesta
        if selected_categories.get('main', False) and 'main' not in current_questions:
            pending_categories.append('main')
        
        # Incluir 'client' solo si está seleccionado, no tiene respuesta y el usuario mostró interés
        if (selected_categories.get('client', False) and 
            'client' not in current_questions and 
            client_perspective):
            pending_categories.append('client')
        
        # Incluir 'supply_chain' solo si está seleccionado, no tiene respuesta y el usuario mostró interés
        if (selected_categories.get('supply_chain', False) and 
            'supply_chain' not in current_questions and 
            supply_chain_perspective):
            pending_categories.append('supply_chain')

        print(f"Pending categories after filtering: {pending_categories}")

        category_messages = {
            'main': "Please provide screening questions for main companies in the sector.",
            'client': "Please provide screening questions for client companies.",
            'supply_chain': "Please provide screening questions for supply chain companies."
        }

        if pending_categories:
            next_category = pending_categories[0]
            message = category_messages.get(next_category)
            translated_message = chatgpt.translate_message(message, detected_language)
            
            return jsonify({
                'success': True,
                'status': 'pending',
                'message': translated_message,
                'current_category': next_category,
                'remaining_categories': pending_categories[1:],
                'completed_categories': list(current_questions.keys()),
                'current_questions': current_questions,
                'detected_language': detected_language
            })
        else:
            completion_message = "All screening questions have been successfully gathered."
            return jsonify({
                'success': True,
                'status': 'completed',
                'message': chatgpt.translate_message(completion_message, detected_language),
                'screening_questions': current_questions,
                'detected_language': detected_language
            })

    except Exception as e:
        print("Error in evaluation_questions_sections:", str(e))
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your request.',
            'error': str(e),
            'detected_language': detected_language if 'detected_language' in locals() else 'en'
        }), 500


@app.route('/api/save-evaluation', methods=['POST'])
def save_evaluation():
    try:
        data = request.json
        print("\n=== Save Evaluation Endpoint ===")
        print("Received data:", data)

        required_fields = ['project_id', 'evaluation_data']
        if not all(field in data for field in required_fields):
            missing_fields = [field for field in required_fields if field not in data]
            print("Missing required fields:", missing_fields)
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        project_id = data['project_id']
        evaluation_data = data['evaluation_data']
        
        # Agregar timestamp
        evaluation_data['timestamp'] = datetime.utcnow().isoformat()
        
        # Aquí iría la lógica para guardar en la base de datos
        # Por ejemplo:
        # db.evaluations.insert_one({
        #     'project_id': project_id,
        #     'evaluation_data': evaluation_data,
        #     'created_at': datetime.utcnow()
        # })

        print(f"Evaluation saved successfully for project {project_id}")
        return jsonify({
            'success': True,
            'message': 'Evaluation saved successfully',
            'project_id': project_id
        })

    except Exception as e:
        print("Error in save_evaluation:", str(e))
        return jsonify({
            'success': False,
            'message': 'An error occurred while saving the evaluation',
            'error': str(e)
        }), 500

@app.route('/api/get-evaluation/<project_id>', methods=['GET'])
def get_evaluation(project_id):
    try:
        print(f"\n=== Get Evaluation Endpoint ===")
        print(f"Requesting evaluation for project: {project_id}")

        if not project_id:
            return jsonify({
                'success': False,
                'message': 'Project ID is required'
            }), 400

        # Aquí iría la lógica para obtener de la base de datos
        # Por ejemplo:
        # evaluation = db.evaluations.find_one({'project_id': project_id})
        
        # Por ahora, retornamos un mock
        mock_evaluation = {
            'project_id': project_id,
            'evaluation_data': {
                'main': ['Question 1', 'Question 2'],
                'client': ['Client Question 1'],
                'supply_chain': ['Supply Chain Question 1', 'Supply Chain Question 2']
            },
            'timestamp': datetime.utcnow().isoformat()
        }

        print(f"Retrieved evaluation data for project {project_id}")
        return jsonify({
            'success': True,
            'evaluation': mock_evaluation
        })

    except Exception as e:
        print("Error in get_evaluation:", str(e))
        return jsonify({
            'success': False,
            'message': 'An error occurred while retrieving the evaluation',
            'error': str(e)
        }), 500









@app.route('/api/industry-experts', methods=['POST'])
def industry_experts():
    try:
        global LAST_DETECTED_LANGUAGE
        print("\n=== Previous Language State ===")
        print(f"Last detected language was: {LAST_DETECTED_LANGUAGE}")

        data = request.json
        print(f"Received request data: {data}")
        
        chatgpt = ChatGPTHelper()
        zoho_service = ZohoService()
        detected_language = LAST_DETECTED_LANGUAGE if LAST_DETECTED_LANGUAGE else data.get('language', 'en')
        
        LAST_DETECTED_LANGUAGE = detected_language
        print("1. Initial language detection:", detected_language)

        BASE_MESSAGES = {
            'invalid_client_perspective': 'clientPerspective must be a boolean value or empty string',
            'missing_required_fields': 'Missing required fields: sector and region',
            'processing_error': 'An error occurred while processing your request.',
            'experts_found_title': 'Experts Found',
            'main_experts_title': 'Main Company Experts',
            'client_experts_title': 'Client Company Experts',
            'supply_chain_experts_title': 'Supply Chain Experts',
            'selection_instructions': 'Please select an expert by entering their name exactly as it appears in the list.',
            'selection_example': 'For example: "{expert_name}"',
            'selection_prompt': 'Which expert would you like to select?'
        }
        
        # Validar datos requeridos
        sector = data.get('sector')
        region = data.get('region')
        main_companies = data.get('companies', [])
        client_perspective = data.get('clientPerspective', False)
        supply_chain_perspective = data.get('supplyChainRequired', False)

        if not sector or not region:
            return jsonify({
                'success': False,
                'message': chatgpt.translate_message(BASE_MESSAGES['missing_required_fields'], detected_language)
            }), 400

        print("\n=== Collecting Companies ===")
        all_companies = {
            'main_companies': main_companies,
            'client_companies': [],
            'supply_companies': []
        }

        # Obtener empresas cliente si se solicitó
        if client_perspective:
            print("\n=== Getting Client Companies ===")
            client_result = chatgpt.get_client_side_companies(
                sector=sector,
                geography=region
            )
            if client_result['success']:
                all_companies['client_companies'] = client_result['content']

        # Obtener empresas supply chain si se solicitó
        if supply_chain_perspective:
            print("\n=== Getting Supply Chain Companies ===")
            supply_result = chatgpt.get_supply_chain_companies(
                sector=sector,
                geography=region
            )
            if supply_result['success']:
                all_companies['supply_companies'] = supply_result['content']

        print("\n=== Companies Collected ===")
        for category, companies in all_companies.items():
            print(f"{category}: {len(companies)} companies")

        # Obtener todos los candidatos
        print("\n=== Getting All Candidates ===")
        all_candidates = zoho_service.get_candidates()

        # Definir límite máximo de expertos
        MAX_TOTAL_EXPERTS = 25
        total_categories = sum([
            1,  # main_companies siempre cuenta
            bool(client_perspective),
            bool(supply_chain_perspective)
        ])
        experts_per_category = MAX_TOTAL_EXPERTS // total_categories
        print(f"\nExperts per category: {experts_per_category}")

        # Categorizar expertos
        categorized_experts = {
            'main_companies': {'experts': [], 'companies_found': set()},
            'client_companies': {'experts': [], 'companies_found': set()},
            'supply_companies': {'experts': [], 'companies_found': set()}
        }

        if isinstance(all_candidates, list):
            print(f"\n=== Processing {len(all_candidates)} candidates ===")
            for candidate in all_candidates:
                current_employer = candidate.get('Current_Employer', '').lower()
                
                # Crear datos del experto simplificados
                expert_data = {
                    'id': candidate.get('id'),
                    'name': candidate.get('Full_Name'),
                    'current_role': candidate.get('Current_Job_Title'),
                    'current_employer': candidate.get('Current_Employer'),
                    'experience': f"{candidate.get('Experience_in_Years')} years",
                    'location': f"{candidate.get('City', '')}, {candidate.get('Country', '')}"
                }

                # Categorizar basado en la empresa
                for company in all_companies['main_companies']:
                    if company.lower() in current_employer:
                        categorized_experts['main_companies']['experts'].append(expert_data)
                        categorized_experts['main_companies']['companies_found'].add(candidate['Current_Employer'])
                        break

                if client_perspective:
                    for company in all_companies['client_companies']:
                        if company.lower() in current_employer:
                            categorized_experts['client_companies']['experts'].append(expert_data)
                            categorized_experts['client_companies']['companies_found'].add(candidate['Current_Employer'])
                            break

                if supply_chain_perspective:
                    for company in all_companies['supply_companies']:
                        if company.lower() in current_employer:
                            categorized_experts['supply_companies']['experts'].append(expert_data)
                            categorized_experts['supply_companies']['companies_found'].add(candidate['Current_Employer'])
                            break

        # Preparar respuesta final simplificada
        final_response = {
            'success': True,
            'experts': {
                'main': {
                    'experts': categorized_experts['main_companies']['experts'][:experts_per_category],
                    'total_found': len(categorized_experts['main_companies']['experts']),
                    'companies': list(categorized_experts['main_companies']['companies_found'])
                }
            }
        }

        # Agregar categorías adicionales si fueron solicitadas
        if client_perspective:
            final_response['experts']['client'] = {
                'experts': categorized_experts['client_companies']['experts'][:experts_per_category],
                'total_found': len(categorized_experts['client_companies']['experts']),
                'companies': list(categorized_experts['client_companies']['companies_found'])
            }

        if supply_chain_perspective:
            final_response['experts']['supply_chain'] = {
                'experts': categorized_experts['supply_companies']['experts'][:experts_per_category],
                'total_found': len(categorized_experts['supply_companies']['experts']),
                'companies': list(categorized_experts['supply_companies']['companies_found'])
            }

        # Agregar totales generales
        final_response['total_experts_shown'] = sum(
            len(cat['experts']) for cat in final_response['experts'].values()
        )
        final_response['total_experts_found'] = sum(
            cat['total_found'] for cat in final_response['experts'].values()
        )

        # Traducir mensajes
        translated_messages = {
            'experts_found_title': chatgpt.translate_message(BASE_MESSAGES['experts_found_title'], detected_language),
            'main_experts_title': chatgpt.translate_message(BASE_MESSAGES['main_experts_title'], detected_language),
            'client_experts_title': chatgpt.translate_message(BASE_MESSAGES['client_experts_title'], detected_language),
            'supply_chain_experts_title': chatgpt.translate_message(BASE_MESSAGES['supply_chain_experts_title'], detected_language),
            'selection_instructions': chatgpt.translate_message(BASE_MESSAGES['selection_instructions'], detected_language),
            'selection_example': chatgpt.translate_message(BASE_MESSAGES['selection_example'], detected_language),
            'selection_prompt': chatgpt.translate_message(BASE_MESSAGES['selection_prompt'], detected_language)
        }

        final_response['messages'] = translated_messages

        print("\n=== Final Response Statistics ===")
        print(f"Total experts shown: {final_response['total_experts_shown']}")
        print(f"Total experts found: {final_response['total_experts_found']}")
        
        return jsonify(final_response)

    except Exception as e:
        print(f"\n=== Error Handling ===")
        print(f"Error in industry experts: {str(e)}")
        traceback.print_exc()
        error_message = chatgpt.translate_message(
            BASE_MESSAGES['processing_error'],
            detected_language if 'detected_language' in locals() else 'en'
        )
        return jsonify({
            'success': False,
            'message': error_message,
            'error': str(e)
        }), 500



@app.route('/api/select-experts', methods=['POST'])
def select_experts():
    try:
        global LAST_DETECTED_LANGUAGE
        print("\n=== Previous Language State ===")
        print(f"Last detected language was: {LAST_DETECTED_LANGUAGE}")

        data = request.json
        print("\n=== Received Data ===")
        print(f"Received data: {data}")
        
        selected_experts = data.get('selected_experts')
        all_experts_data = data.get('all_experts_data')
        evaluation_questions = data.get('evaluation_questions', {})
        
        chatgpt = ChatGPTHelper()
        detected_language = LAST_DETECTED_LANGUAGE if LAST_DETECTED_LANGUAGE else data.get('language', 'en')

        BASE_MESSAGES = {
            'expert_required': 'At least one expert must be selected',
            'no_data_found': 'No expert data found',
            'expert_selected': 'You have selected the expert(s):',
            'expert_not_found': 'No expert found with the name {name}',
            'processing_error': 'An error occurred while processing your request.',
            'thank_you': 'Thank you for your selection! We will process your request.'
        }

        # Validaciones básicas
        if not selected_experts:
            return jsonify({
                'success': False,
                'message': chatgpt.translate_message(BASE_MESSAGES['expert_required'], detected_language)
            }), 400

        if not all_experts_data or 'experts' not in all_experts_data:
            return jsonify({
                'success': False,
                'message': chatgpt.translate_message(BASE_MESSAGES['no_data_found'], detected_language)
            }), 400

        # Lista para almacenar expertos encontrados
        found_experts = []

        # Buscar expertos que coincidan con el nombre o apellido
        search_term = selected_experts[0].lower()
        name_parts = search_term.split()

        for category, category_data in all_experts_data['experts'].items():
            for expert in category_data.get('experts', []):
                expert_name_lower = expert['name'].lower()
                
                # Verificar si cualquier parte del nombre buscado coincide
                if any(part in expert_name_lower for part in name_parts):
                    found_experts.append({
                        'expert': expert,
                        'category': category
                    })

        if found_experts:
            # Preparar respuesta con todos los expertos encontrados
            expert_responses = []
            for found_expert in found_experts:
                expert = found_expert['expert']
                category = found_expert['category']
                
                expert_response = {
                    'name': expert['name'],
                    'current_role': expert['current_role'],
                    'current_employer': expert['current_employer'],
                    'experience': expert['experience'],
                    'location': expert['location'],
                    'category': category
                }
                expert_responses.append(expert_response)

            # MODIFICACIÓN: Usar directamente todas las preguntas de evaluación disponibles
            category_questions = evaluation_questions.copy()

            print("\n=== Evaluation Questions Debug ===")
            print(f"Original evaluation questions: {evaluation_questions}")
            print(f"Category questions being sent: {category_questions}")

            selection_message = chatgpt.translate_message(
                BASE_MESSAGES['expert_selected'],
                detected_language
            )
            
            thank_you_message = chatgpt.translate_message(
                BASE_MESSAGES['thank_you'],
                detected_language
            )

            response_data = {
                'success': True,
                'message': selection_message,
                'experts_found': len(expert_responses),
                'expert_details': expert_responses,
                'screening_questions': category_questions,
                'final_message': thank_you_message,
                'detected_language': detected_language
            }

            print("\n=== Response Data ===")
            print(f"Sending response: {response_data}")
            return jsonify(response_data)
        else:
            not_found_message = chatgpt.translate_message(
                BASE_MESSAGES['expert_not_found'].format(name=selected_experts[0]),
                detected_language
            )
            return jsonify({
                'success': False,
                'message': not_found_message
            }), 404

    except Exception as e:
        print(f"\n=== Error Handling ===")
        print(f"Error in select experts: {str(e)}")
        traceback.print_exc()
        error_message = chatgpt.translate_message(
            BASE_MESSAGES['processing_error'],
            detected_language if 'detected_language' in locals() else 'en'
        )
        return jsonify({
            'success': False,
            'message': error_message,
            'error': str(e)
        }), 500
################################################################################################3






































@app.route('/api/ai/voice/process', methods=['POST'])
def process_voice():
    print("\n=== New Voice Request ===")
    print("Headers:", dict(request.headers))

    try:
        # Obtener el tipo de procesamiento de los parámetros de la URL
        process_type = request.args.get('type', 'username')  # default a 'username'
        voice_result = voice_handler.handle_voice_request(request, step=process_type)
        
        return jsonify({
            'success': True,
            'detected_language': voice_result.get('detected_language', 'es'),
            'transcription': voice_result.get('transcription'),
            'username': voice_result.get('username') if process_type == 'username' else None,
            'original_transcription': voice_result.get('original_transcription')
        })

    except Exception as e:
        print(f"Error in voice processing: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


    
@app.route('/api/ai/translate', methods=['POST', 'OPTIONS'])
def translate():
    print("\n=== New Request to /api/translate ===")
    print("Method:", request.method)
    print("Headers:", dict(request.headers))
    
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})

    try:
        data = request.json
        print("\n=== Request Data ===")
        print("Received data:", data)

        if 'text' not in data or 'target_language' not in data:
            return jsonify({
                'success': False,
                'message': 'Both text and target_language are required'
            }), 400

        translated_text = chatgpt.translate_message(
            data['text'], 
            data['target_language']
        )
        
        print(f"\n=== Translation Result ===")
        print(f"Original text: {data['text']}")
        print(f"Target language: {data['target_language']}")
        print(f"Translated text: {translated_text}")

        return jsonify({
            'success': True,
            'translated_text': translated_text
        })

    except Exception as e:
        print(f"\n=== Error in translate ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error translating text'
        }), 500
    

# Actualiza la función test para incluir los nuevos endpoints
@app.route('/test', methods=['GET'])
def test():
    return jsonify({
        'message': 'Backend is running!',
        'status': 'OK',
        'endpoints': {
            'webhook': '/',
            'process-messages': '/process-messages',
            'voice': '/api/ai/voice/process',
            'detect-language': '/api/detect-language',
            'translate': '/api/translate',
            'email-capture': '/api/ai/email/capture',
            'process-text': '/api/ai/test/process-text',
            'test': '/test'
        }
    })


@app.route('/api/ai/test/detect-sector', methods=['POST'])
def test_detect_sector():
    try:
        data = request.json
        if 'text' not in data:
            return jsonify({
                'success': False,
                'message': 'Text input is required'
            }), 400

        chatgpt = ChatGPTHelper()
        sector_result = chatgpt.translate_sector(data['text'])

        if sector_result['success']:
            if sector_result['is_valid']:
                return jsonify({
                    'success': True,
                    'sector': sector_result['translated_sector'],
                    'displayed_sector': sector_result['displayed_sector']
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f"Invalid sector. Available sectors: {sector_result.get('available_sectors')}",
                    'available_sectors': sector_result.get('available_sectors')
                })
        
        return jsonify({
            'success': False,
            'message': 'Could not process sector'
        })

    except Exception as e:
        print(f"Error in test_detect_sector: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing sector: {str(e)}'
        }), 500
    

if __name__ == '__main__':
    print("\n=== Starting Server ===")
    print("Server URL: http://127.0.0.1:8080")
    serve(app, host='0.0.0.0', port=8080)





##########################ZOHO RECRUIT######################
@app.route('/api/recruit/candidates', methods=['GET'])
def get_candidates():
    try:
        print("\n=== Getting Candidates from Zoho Recruit ===")
        candidates = zoho_service.get_candidates()
        return jsonify({
            'success': True,
            'candidates': candidates
        })
    except Exception as e:
        print(f"Error getting candidates: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/recruit/jobs', methods=['GET'])
def get_jobs():
    try:
        print("\n=== Getting Jobs from Zoho Recruit ===")
        jobs = zoho_service.get_jobs()
        return jsonify({
            'success': True,
            'jobs': jobs
        })
    except Exception as e:
        print(f"Error getting jobs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    



@app.route('/api/recruit/candidates/search', methods=['GET'])
def search_candidates():
    try:
        criteria = request.args.get('criteria', '')
        url = f"{zoho_service.recruit_base_url}/Candidates/search"
        headers = {
            'Authorization': f'Zoho-oauthtoken {zoho_service.recruit_access_token}'
        }
        params = {
            'criteria': criteria
        }
        
        response = requests.get(url, headers=headers, params=params)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500