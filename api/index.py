import sys
from pathlib import Path
import os
from dotenv import load_dotenv
import sys
from pathlib import Path
from datetime import datetime 

# Mover esta línea al inicio
sys.path.append(str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from waitress import serve
from src.handlers.phase1_handlers.email_handler import handle_email_capture
from src.handlers.phase2_handlers.sector_handler import handle_sector_capture
from src.handlers.phase2_handlers.geography_handler import handle_geography_capture
from src.handlers.voice_handler import VoiceHandler
from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.external.zoho_services import ZohoService
from src.utils.config import VALID_SECTORS
from src.routes.ai.voiceRoutes import voice_routes

# Configuración inicial
print("\n=== Environment Setup ===")
current_dir = Path(__file__).parent.absolute()
env_path = current_dir / '.env'

print(f"Current directory: {current_dir}")
print(f"Env file path: {env_path}")
print(f"Env file exists: {env_path.exists()}")

# Carga las variables de entorno
load_dotenv(env_path)

# Verifica el token
token = os.getenv('ZOHO_ACCESS_TOKEN')
print(f"\n=== Token Verification ===")
print(f"Token loaded: {token[:10]}...{token[-10:] if token else 'None'}")

# Prueba el token antes de iniciar la aplicación
if token:
    try:
        test_url = "https://www.zohoapis.com/crm/v2/Accounts"
        headers = {
            'Authorization': f'Zoho-oauthtoken {token}'
        }
        print("\nTesting token with Zoho API...")
        response = requests.get(test_url, headers=headers)
        print(f"Test response status: {response.status_code}")
        if response.status_code != 200:
            print(f"Token test failed: {response.text}")
            print("WARNING: Application may not work correctly with invalid token")
        else:
            print("Token test successful")
    except Exception as e:
        print(f"Error testing token: {str(e)}")
else:
    print("WARNING: No token found in .env file")

sys.path.append(str(Path(__file__).parent.parent))




app = Flask(__name__)

# Configuración actualizada de CORS
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://expert-consultation-bot-front.vercel.app",
            "https://expert-consultation-bot-front-isej4yvne.vercel.app",
            "http://localhost:5173",
            "http://localhost:3000"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

app.register_blueprint(voice_routes, url_prefix='/api/ai/voice')

print("\n=== Initializing Services ===")
zoho_service = ZohoService()
voice_handler = VoiceHandler()
chatgpt = ChatGPTHelper()

@app.route('/refresh-token', methods=['POST'])
def refresh_token():
    try:
        refresh_url = "https://accounts.zoho.com/oauth/v2/token"
        params = {
            'refresh_token': os.getenv('ZOHO_REFRESH_TOKEN'),
            'client_id': os.getenv('ZOHO_CLIENT_ID'),
            'client_secret': os.getenv('ZOHO_CLIENT_SECRET'),
            'grant_type': 'refresh_token'
        }
        
        print("\n=== Refreshing Token ===")
        print(f"Using refresh token: {params['refresh_token'][:10]}...")
        
        response = requests.post(refresh_url, params=params)
        print(f"Refresh response status: {response.status_code}")
        
        if response.status_code == 200:
            new_token = response.json().get('access_token')
            
            # Actualizar token en memoria
            global token
            token = new_token
            zoho_service.access_token = new_token
            
            # Actualizar en Vercel si estamos en producción
            if os.getenv('ENVIRONMENT') == 'production':
                vercel_api_url = f"https://api.vercel.com/v1/projects/{os.getenv('VERCEL_PROJECT_ID')}/env"
                headers = {
                    'Authorization': f'Bearer {os.getenv("VERCEL_TOKEN")}'
                }
                data = {
                    'key': 'ZOHO_ACCESS_TOKEN',
                    'value': new_token,
                    'target': ['production']
                }
                
                print("\n=== Updating Vercel Environment ===")
                vercel_response = requests.post(vercel_api_url, headers=headers, json=data)
                print(f"Vercel update status: {vercel_response.status_code}")
            
            # Actualizar archivo .env local si estamos en desarrollo
            else:
                try:
                    with open(env_path, 'r') as file:
                        lines = file.readlines()
                    
                    with open(env_path, 'w') as file:
                        for line in lines:
                            if line.startswith('ZOHO_ACCESS_TOKEN='):
                                file.write(f'ZOHO_ACCESS_TOKEN={new_token}\n')
                            else:
                                file.write(line)
                    print("\n=== Updated local .env file ===")
                except Exception as e:
                    print(f"Error updating .env file: {str(e)}")
            
            return jsonify({
                'success': True,
                'message': 'Token updated successfully',
                'new_token': new_token[:10] + '...'
            })
            
        return jsonify({
            'success': False,
            'message': f'Failed to refresh token: {response.text}'
        })
        
    except Exception as e:
        print(f"Error in refresh_token: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    







###################################################################################################
######################################FASE 1 !!!!!!!!!!






REGISTERED_TEST_EMAILS = [
    "test@test.com",        # Inglés
    "prueba@prueba.com",      # Español
    "essai@essai.com",       # Francés
    "prova@essai.com",       # Italiano
    "versuch@essai.com",
    "测试@测试.com"      # Alemán
]
def is_email_registered(email: str) -> bool:
    """
    Verifica si un email está en la lista de emails registrados
    
    Args:
        email (str): El email a verificar
        
    Returns:
        bool: True si está registrado, False si no
    """
    return email.lower() in [e.lower() for e in REGISTERED_TEST_EMAILS]


@app.route('/api/ai/email/capture', methods=['POST'])
def capture_email():
    try:
        data = request.json
        if 'email' not in data or 'text' not in data:
            return jsonify({
                'success': False,
                'message': 'Email and text are required'
            }), 400
        

        chatgpt = ChatGPTHelper()
        email_extraction_result = chatgpt.extract_email(data['text'])
        
        if not email_extraction_result['success']:
            return jsonify({
                'success': False,
                'message': 'No valid email found in text'
            }), 400

        email = email_extraction_result['email']
        input_text = data['text']
        
        # Inicializar ChatGPTHelper
        chatgpt = ChatGPTHelper()
        text_processing_result = chatgpt.process_text_input(input_text)
        detected_language = text_processing_result.get('detected_language', 'en')

        # Verificar si el email está registrado
        is_registered = is_email_registered(email)

        # Siempre solicitar el nombre, independientemente del estado de registro
        base_message = "Thank you for your email. What is your name?"
        translated_message = chatgpt.translate_message(base_message, detected_language)

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
            booking_base_message = "Please book a call to complete your registration"
            booking_message = chatgpt.translate_message(booking_base_message, detected_language)
            
            response.update({
                'action_required': "book_call",
                'booking_link': "https://calendly.com/your-booking-link",
                'booking_message': booking_message
            })

        return jsonify(response)

    except Exception as e:
        print(f"Error in email capture: {str(e)}")
        error_message = "An error occurred while processing your request."
        if 'chatgpt' in locals():
            error_message = chatgpt.translate_message(
                error_message, 
                detected_language if 'detected_language' in locals() else 'en'
            )
        return jsonify({
            'success': False,
            'error': error_message
        }), 500







@app.route('/api/ai/name/capture', methods=['POST'])
def capture_name():
    try:
        data = request.json
        if 'text' not in data or 'is_registered' not in data:
            return jsonify({
                'success': False,
                'message': 'Text and registration status are required'
            }), 400

        # AQUÍ implementar extract_name
        chatgpt = ChatGPTHelper()
        name_extraction_result = chatgpt.extract_name(data['text'])

        if not name_extraction_result['success']:
            return jsonify({
                'success': False, 
                'message': 'No valid name found in text'
            }), 400

        name = name_extraction_result['name']
        is_registered = data['is_registered']

        text_processing_result = chatgpt.process_text_input(name)
        detected_language = text_processing_result.get('detected_language', 'en')

        if is_registered:
            # Usuario registrado: preguntar sobre conexión con expertos
            base_message = f"Welcome back {name}! Would you like to connect with our experts?"
            translated_message = chatgpt.translate_message(base_message, detected_language)
            
            # Traducir opciones Sí/No
            yes_option = chatgpt.translate_message("yes", detected_language)
            no_option = chatgpt.translate_message("no", detected_language)

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
            # Usuario no registrado: proponer contacto con agente
            base_message = f"Thank you {name}! To better assist you, we recommend speaking with one of our agents."
            translated_message = chatgpt.translate_message(base_message, detected_language)
            
            # Traducir mensaje de booking
            booking_message = chatgpt.translate_message(
                "Would you like to schedule a call?",
                detected_language
            )

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

        return jsonify(response)

    except Exception as e:
        print(f"Error in name capture: {str(e)}")
        error_message = "An error occurred while processing your request."
        if 'chatgpt' in locals() and 'detected_language' in locals():
            error_message = chatgpt.translate_message(error_message, detected_language)
        return jsonify({
            'success': False,
            'error': error_message
        }), 500
    





    
@app.route('/api/ai/expert-connection/ask', methods=['POST'])
def ask_expert_connection():
    try:
        data = request.json
        
        required_fields = ['text', 'name', 'detected_language']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'message': 'Required fields missing: text, name, detected_language'
            }), 400

        text = data['text']
        name = data['name']
        detected_language = data['detected_language']

        chatgpt = ChatGPTHelper()
        intention_result = chatgpt.extract_intention(text)

        if not intention_result['success']:
            translated_error = chatgpt.translate_message(intention_result['error'], detected_language)
            return jsonify({
                'success': False,
                'error': translated_error,
                'step': 'clarify'  # Indicate that clarification is needed
            }), 400 # Bad request due to unclear input


        intention = intention_result['intention']

        if intention == 'yes':
            base_message = f"Excellent {name}! What sector interests you the most? Choose from:\n\n1. Technology\n2. Healthcare\n3. Finance\n4. Education\n5. Other"
            translated_message = chatgpt.translate_message(base_message, detected_language)
            return jsonify({
                'success': True,
                'name': name,
                'detected_language': detected_language,
                'step': 'select_sector',
                'message': translated_message,
                'next_action': 'process_sector_selection'
            })

        elif intention == 'no':
            base_message = f"I understand, {name}. Feel free to come back when you'd like to connect with our experts. Have a great day!"
            translated_message = chatgpt.translate_message(base_message, detected_language)
            return jsonify({
                'success': True,
                'name': name,
                'detected_language': detected_language,
                'step': 'farewell',
                'message': translated_message,
                'next_action': 'end_conversation'
            })

        else:  # intention is 'unclear'
            base_message = "I'm not sure if that's a yes or no. Could you please clarify?"
            translated_message = chatgpt.translate_message(base_message, detected_language)
            return jsonify({
                'success': True,  # Still success, but needs clarification
                'message': translated_message,
                'detected_language': detected_language,
                'step': 'clarify'
            })


    except Exception as e:
        print(f"Error in expert connection answer: {str(e)}")
        error_message = "An error occurred while processing your request."
        # Try to translate, but use default if language is unknown
        translated_error = chatgpt.translate_message(error_message, detected_language) if 'detected_language' in locals() else error_message
        return jsonify({
            'success': False,
            'error': translated_error
        }), 500
#############################################################################################################3
#############################################################################################################
##SEGUNDA FASE###




@app.route('/api/sector-experience', methods=['POST'])
def sector_experience():
    try:
        data = request.json
        if 'sector' not in data:
            base_error = 'A sector specification is required'
            return jsonify({
                'success': False,
                'message': base_error
            }), 400

        chatgpt = ChatGPTHelper()
        detected_language = data.get('language', 'en')  # Default to 'en'
        
        # Extract sector from user input
        raw_sector_text = data['sector']
        sector = chatgpt.extract_sector(raw_sector_text)
        
        if not sector:
            return jsonify({
                'success': False,
                'message': 'Could not identify a valid sector from the provided text'
            }), 400

        # Base messages in English
        BASE_MESSAGES = {
            'sector_received': "Thank you for specifying the {sector} sector.",
            'ask_region': "Which region are you interested in? (e.g., North America, Europe, Asia, etc.)",
            'processing_error': "Error processing your request"
        }

        # Build the base message
        base_message = (
            f"{BASE_MESSAGES['sector_received'].format(sector=sector)} "
            f"{BASE_MESSAGES['ask_region']}"
        )
        response_message = chatgpt.translate_message(base_message, detected_language)

        # Prepare additional messages if needed
        additional_messages = {}
        if 'additional_info' in data:
            confirmation_message = "Additional information has been registered successfully"
            additional_messages['confirmation'] = chatgpt.translate_message(
                confirmation_message,
                detected_language
            )

        response = {
            'success': True,
            'message': response_message,
            'has_additional_info': 'additional_info' in data and bool(data['additional_info']),
            'sector': sector,
            'language': detected_language
        }

        if additional_messages:
            response['additional_messages'] = additional_messages

        return jsonify(response)

    except Exception as e:
        print(f"Error in sector experience: {str(e)}")
        error_message = BASE_MESSAGES['processing_error']
        translated_error = chatgpt.translate_message(error_message, detected_language)
        return jsonify({
            'success': False,
            'message': translated_error,
            'error': str(e),
            'language': detected_language
        }), 500





@app.route('/api/ai/test/process-text', methods=['POST'])
def test_process_text():
    try:
        data = request.json
        if 'text' not in data:
            base_error = 'Text is required'
            return jsonify({
                'success': False,
                'message': base_error
            }), 400

        chatgpt = ChatGPTHelper()
        detected_language = data.get('language', 'en')  # Default to 'en'
        
        # Extract region from user input
        raw_region_text = data['text']
        region = chatgpt.extract_region(raw_region_text)
        
        if not region:
            return jsonify({
                'success': False,
                'message': 'Could not identify a valid region from the provided text'
            }), 400

        # Base messages in English
        BASE_MESSAGES = {
            'region_received': "Thank you for specifying the {region} region.",
            'ask_companies': "Are there specific companies where you would like experts to have experience? Please enter the names separated by commas or answer 'no'.",
            'processing_error': "Error processing your request"
        }

        # Build the base message
        base_message = (
            f"{BASE_MESSAGES['region_received'].format(region=region)} "
            f"{BASE_MESSAGES['ask_companies']}"
        )
        next_question = chatgpt.translate_message(base_message, detected_language)  # Mantenemos next_question

        # Prepare additional messages if needed
        additional_messages = {}
        if 'additional_info' in data:
            confirmation_message = "Additional information has been registered successfully"
            additional_messages['confirmation'] = chatgpt.translate_message(
                confirmation_message,
                detected_language
            )

        result = {
            'success': True,
            'processed_region': region,
            'next_question': next_question,
            'language': detected_language
        }

        if additional_messages:
            result['additional_messages'] = additional_messages

        return jsonify(result)

    except Exception as e:
        print(f"Error in test_process_text: {str(e)}")
        error_message = BASE_MESSAGES['processing_error']
        translated_error = chatgpt.translate_message(error_message, detected_language)
        return jsonify({
            'success': False,
            'message': translated_error,
            'error': str(e),
            'language': detected_language
        }), 500
    


@app.route('/api/simple-expert-connection', methods=['POST'])
def simple_expert_connection():
    try:
        data = request.json
        if 'answer' not in data:
            base_error = 'An answer is required'
            return jsonify({
                'success': False,
                'message': base_error
            }), 400

        chatgpt = ChatGPTHelper()
        detected_language = data.get('language', 'en')  # Default to 'en'
        
        # Extract companies from user input
        answer = data['answer']
        companies_response = chatgpt.process_company_response(answer)
        
        if companies_response is None:
            return jsonify({
                'success': False,
                'message': 'Could not process the company response properly'
            }), 400

        # Base messages in English
        BASE_MESSAGES = {
            'positive_response': "We have registered your interest in the following companies: {companies}",
            'negative_response': "No problem! We will proceed with the general process.",
            'processing_error': "Error processing your request"
        }

        # Build the base message - AQUÍ ESTÁ LA MODIFICACIÓN PRINCIPAL
        if companies_response == "no":
            response_message = BASE_MESSAGES['negative_response']
            interested_in_companies = False
            companies = []
        elif isinstance(companies_response, dict):
            response_message = BASE_MESSAGES['positive_response'].format(
                companies=", ".join(companies_response['companies'])
            )
            interested_in_companies = companies_response['interested_in_companies']
            companies = companies_response['companies']
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid response format'
            }), 400
            
        message = chatgpt.translate_message(response_message, detected_language)

        # Prepare additional messages if needed
        additional_messages = {}
        if 'additional_info' in data:
            confirmation_message = "Additional information has been registered successfully"
            additional_messages['confirmation'] = chatgpt.translate_message(
                confirmation_message,
                detected_language
            )

        response = {
            'success': True,
            'message': message,
            'interested_in_companies': interested_in_companies,
            'companies': companies,
            'language': detected_language
        }

        if additional_messages:
            response['additional_messages'] = additional_messages

        return jsonify(response)

    except Exception as e:
        print(f"Error in simple expert connection: {str(e)}")
        error_message = BASE_MESSAGES['processing_error']
        translated_error = chatgpt.translate_message(error_message, detected_language)
        return jsonify({
            'success': False,
            'message': translated_error,
            'error': str(e),
            'language': detected_language
        }), 500





@app.route('/api/company-suggestions-test', methods=['POST'])
def company_suggestions_test():
    try:
        data = request.json
        
        # Validación de campos requeridos
        required_fields = ['sector', 'processed_region']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'message': 'Sector and region are required'
            }), 400

        # Inicialización de variables y configuración
        chatgpt = ChatGPTHelper()
        sector = data['sector']
        location = data['processed_region']
        detected_language = data.get('language', 'en')
        interested_in_companies = data.get('interested_in_companies', False)
        companies_list = data.get('companies', [])

        # Definición de compañías ficticias para el sector tecnológico
        TECH_FICTIONAL_COMPANIES = [
            "Company 1 Tech Solutions",
            "Company 2 Digital Systems",
            "Company 3 Innovation Labs"
        ]

        # Obtener sugerencias de ChatGPT
        chatgpt_result = chatgpt.get_companies_suggestions(
            sector=sector,
            geography=location
        )

        # Procesamiento de compañías según el sector
        if sector.lower() in ['technology', 'tecnología', 'tech', 'tecnologia']:
            all_companies = TECH_FICTIONAL_COMPANIES + chatgpt_result['content']
        else:
            all_companies = chatgpt_result['content']

        # Procesamiento de compañías de interés
        if interested_in_companies and companies_list:
            final_companies = [comp for comp in all_companies if comp not in companies_list]
            final_companies = companies_list + final_companies
        else:
            final_companies = all_companies

        # Limitar a 20 compañías
        final_companies = final_companies[:20]

        # Preparación del mensaje de respuesta
        if interested_in_companies and companies_list:
            companies_str = ", ".join(companies_list)
            base_message = f"We have registered your interest in the following companies: {companies_str}."
        else:
            base_message = f"Suggested companies for the {sector} sector in {location}."

        message = chatgpt.translate_message(base_message, detected_language)

        # Agregar pregunta de confirmación
        confirmation_question = "\n\nDo you agree with this list?"
        confirmation_question = chatgpt.translate_message(confirmation_question, detected_language)

        final_message = message + confirmation_question

        return jsonify({
            'success': True,
            'companies': final_companies,
            'interested_in_companies': interested_in_companies,
            'language': detected_language,
            'message': final_message
        })

    except Exception as e:
        print(f"Error in company suggestions: {str(e)}")
        error_message = "An error occurred while processing your request."
        error_message = chatgpt.translate_message(error_message, detected_language)
        return jsonify({
            'success': False,
            'message': error_message,
            'companies': [],
            'interested_in_companies': False,
            'language': detected_language if 'detected_language' in locals() else 'en'
        }), 500
    



@app.route('/api/process-companies-agreement', methods=['POST'])
def process_companies_agreement():
    try:
        data = request.json
        if 'text' not in data:
            return jsonify({
                'success': False,
                'message': 'Text is required'
            }), 400

        chatgpt = ChatGPTHelper()
        detected_language = data.get('language', 'en')
        
        # Extract agreement using existing extract_intention
        text = data['text']
        intention = chatgpt.extract_intention(text)
        
        if intention is None:
            return jsonify({
                'success': False,
                'message': 'Could not determine if you agree with the list. Please answer yes or no.'
            }), 400

        # Base messages in English
        BASE_MESSAGES = {
            'positive_response': "Great! Let's proceed with these companies.",
            'negative_response': "I'll help you find different company suggestions.",
            'processing_error': "Error processing your request"
        }

        # Verificar la intención correctamente
        is_positive = intention.get('intention', '').lower() == 'yes'
        
        # Select appropriate message based on intention
        response_message = BASE_MESSAGES['positive_response'] if is_positive else BASE_MESSAGES['negative_response']
        translated_message = chatgpt.translate_message(response_message, detected_language)

        return jsonify({
            'success': True,
            'message': translated_message,
            'agreed': intention,
            'language': detected_language
        })

    except Exception as e:
        print(f"Error in process companies agreement: {str(e)}")
        error_message = BASE_MESSAGES['processing_error']
        translated_error = chatgpt.translate_message(error_message, detected_language)
        return jsonify({
            'success': False,
            'message': translated_error,
            'error': str(e),
            'language': detected_language
        }), 500
    """"""""""""""""""""""""""""""""""""""""2"""
######################################################################################################
####################################### FASE3##########################################################




@app.route('/api/specify-employment-status', methods=['POST'])
def specify_employment_status():
    try:
        data = request.json
        detected_language = data.get('language', 'en')
        chatgpt = ChatGPTHelper()

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
            if detected_language == 'en':
                return message
            return chatgpt.translate_message(message, detected_language)

        def normalize_status(status_text):
            status_text = status_text.strip().lower()
            
            status_mapping = {
                'current': ['current', 'currently', 'presente', 'actual', 'now', 'present'],
                'previous': ['previous', 'previously', 'former', 'past', 'anterior', 'antes'],
                'both': ['both', 'all', 'todos', 'ambos', 'both options', 'all options']
            }
            
            for status, variants in status_mapping.items():
                if any(variant in status_text for variant in variants):
                    return status
                    
            return None

        # Si no hay status, devolver la pregunta
        if 'status' not in data:
            return jsonify({
                'success': True,
                'message': get_message(BASE_MESSAGES['ask_preference']),
                'has_status': False,
                'language': detected_language
            })

        # Intentar primero con extract_work_timing
        status = chatgpt.extract_work_timing(data['status'])
        
        # Si no funciona, seguir con la normalización normal
        if not status:
            # Normalizar el status recibido
            user_status = data['status'].strip().lower()
            status = normalize_status(user_status)

            # Si no se pudo normalizar y no es inglés, intentar con ChatGPT
            if status is None and detected_language != 'en':
                normalize_prompt = BASE_MESSAGES['normalize_prompt'] + data['status']
                normalized_status = chatgpt.translate_message(normalize_prompt, 'en').strip().lower()
                status = normalize_status(normalized_status)

        if status:
            status_message = BASE_MESSAGES['status_options'][status]
            response_message = get_message(status_message)
            
            return jsonify({
                'success': True,
                'message': response_message,
                'has_status': True,
                'employment_status': status,
                'language': detected_language
            })
        else:
            error_message = get_message(BASE_MESSAGES['invalid_option'])
            return jsonify({
                'success': False,
                'message': error_message,
                'has_status': False,
                'language': detected_language
            }), 400

    except Exception as e:
        print(f"Error in specify employment status: {str(e)}")
        error_message = get_message(BASE_MESSAGES['processing_error'])
        return jsonify({
            'success': False,
            'message': error_message,
            'error': str(e),
            'language': detected_language
        }), 500


@app.route('/api/exclude-companies', methods=['POST'])
def exclude_companies():
    try:
        data = request.json
        detected_language = data.get('language', 'en')
        chatgpt = ChatGPTHelper()

        # Mensajes base en inglés
        BASE_MESSAGES = {
            'ask_exclusions': "Are there any companies that should be excluded from the search? Please enter the names separated by commas or answer 'no'.",
            'no_exclusions': "Understood, there are no companies to exclude.",
            'exclusions_confirmed': "Understood, we will exclude the following companies from the search: {companies}",
            'processing_error': "An error occurred while processing your request."
        }

        # Función para obtener el mensaje según el idioma
        def get_message(message):
            if detected_language == 'en':
                return message
            return chatgpt.translate_message(message, detected_language)

        # Si no hay answer, devolver la pregunta inicial
        if 'answer' not in data:
            return jsonify({
                'success': True,
                'message': get_message(BASE_MESSAGES['ask_exclusions']),
                'detected_language': detected_language,
                'has_excluded_companies': False,
                'excluded_companies': None
            })

        # Procesar la respuesta con ChatGPT
        processed_response = chatgpt.process_company_response(data['answer'])

        # Procesar la respuesta
        if processed_response == "no" or data['answer'].lower() in ['no', 'n']:
            base_message = BASE_MESSAGES['no_exclusions']
            excluded_companies = None
            has_excluded_companies = False
        elif isinstance(processed_response, dict):
            companies_list = ", ".join(processed_response['companies'])
            base_message = BASE_MESSAGES['exclusions_confirmed'].format(
                companies=companies_list
            )
            excluded_companies = processed_response['companies']
            has_excluded_companies = True
        else:
            base_message = BASE_MESSAGES['ask_exclusions']
            excluded_companies = None
            has_excluded_companies = False

        # Obtener mensaje según el idioma
        response_message = get_message(base_message)

        return jsonify({
            'success': True,
            'message': response_message,
            'detected_language': detected_language,
            'has_excluded_companies': has_excluded_companies,
            'excluded_companies': excluded_companies
        })

    except Exception as e:
        print(f"Error in exclude companies: {str(e)}")
        error_message = get_message(BASE_MESSAGES['processing_error'])
        return jsonify({
            'success': False,
            'message': error_message,
            'error': str(e)
        }), 500



@app.route('/api/client-perspective', methods=['POST'])
def client_perspective():
    try:
        data = request.json
        if 'answer' not in data:
            base_error = 'Answer is required'
            return jsonify({
                'success': False,
                'message': base_error
            }), 400

        chatgpt = ChatGPTHelper()
        detected_language = data.get('language', 'en')

        # Procesar la respuesta con ChatGPT primero
        intention_result = chatgpt.extract_intention(data['answer'])
        intention = intention_result.get('intention') if intention_result.get('success') else None

        # Mensajes base en inglés
        BASE_MESSAGES = {
            'ask_preference': "Would you be interested in receiving industry perspectives from the client side?",
            'confirmed_yes': "Great! I will include experts with client-side perspective in the search.",
            'confirmed_no': "Understood. I will focus on other perspectives in the search.",
            'processing_error': "An error occurred while processing your request."
        }

        # Procesar la respuesta basada en la intención extraída
        if intention == 'yes':
            base_message = BASE_MESSAGES['confirmed_yes']
            client_perspective = True
        elif intention == 'no':
            base_message = BASE_MESSAGES['confirmed_no']
            client_perspective = False
        else:
            base_message = BASE_MESSAGES['ask_preference']
            client_perspective = None

        # Traducir mensaje
        response_message = chatgpt.translate_message(base_message, detected_language)

        return jsonify({
            'success': True,
            'message': response_message,
            'detected_language': detected_language,
            'client_perspective': client_perspective,
            'answer_received': intention if client_perspective is not None else None
        })

    except Exception as e:
        print(f"Error in client perspective: {str(e)}")
        error_message = chatgpt.translate_message(
            BASE_MESSAGES['processing_error'],
            detected_language if 'detected_language' in locals() else 'en'
        )
        return jsonify({
            'success': False,
            'message': error_message,
            'error': str(e)
        }), 500


    ############################################




@app.route('/api/supply-chain-experience', methods=['POST'])
def supply_chain_experience():
    try:
        data = request.json
        if 'answer' not in data:
            base_error = 'Answer is required'
            return jsonify({
                'success': False,
                'message': base_error
            }), 400

        chatgpt = ChatGPTHelper()
        detected_language = data.get('language', 'en')

        # Procesar la respuesta con ChatGPT primero
        intention_result = chatgpt.extract_intention(data['answer'])
        intention = intention_result.get('intention') if intention_result.get('success') else None

        # Mensajes base en inglés
        BASE_MESSAGES = {
            'ask_preference': "Would you like to include experts with supply chain experience?",
            'confirmed_yes': "Perfect! I will include experts with supply chain experience in the search.",
            'confirmed_no': "Understood. I will not prioritize supply chain experience in the search.",
            'processing_error': "An error occurred while processing your request."
        }

        # Procesar la respuesta basada en la intención extraída
        if intention == 'yes':
            base_message = BASE_MESSAGES['confirmed_yes']
            supply_chain_required = True
        elif intention == 'no':
            base_message = BASE_MESSAGES['confirmed_no']
            supply_chain_required = False
        else:
            base_message = BASE_MESSAGES['ask_preference']
            supply_chain_required = None

        # Traducir mensaje
        response_message = chatgpt.translate_message(base_message, detected_language)

        return jsonify({
            'success': True,
            'message': response_message,
            'detected_language': detected_language,
            'supply_chain_required': supply_chain_required,
            'answer_received': intention if supply_chain_required is not None else None
        })

    except Exception as e:
        print(f"Error in supply chain experience: {str(e)}")
        error_message = chatgpt.translate_message(
            BASE_MESSAGES['processing_error'],
            detected_language if 'detected_language' in locals() else 'en'
        )
        return jsonify({
            'success': False,
            'message': error_message,
            'error': str(e)
        }), 500






    ###############################################################3



@app.route('/api/evaluation-questions', methods=['POST'])
def evaluation_questions():
    try:
        data = request.json
        if 'answer' not in data:
            base_error = 'Answer is required'
            return jsonify({
                'success': False,
                'message': base_error
            }), 400

        chatgpt = ChatGPTHelper()
        detected_language = data.get('language', 'en')

        # Procesar la respuesta con ChatGPT primero
        intention_result = chatgpt.extract_intention(data['answer'])
        intention = intention_result.get('intention') if intention_result.get('success') else None

        # Mensajes base en inglés
        BASE_MESSAGES = {
            'ask_preference': "Would you like to add evaluation questions for the project?",
            'confirmed_yes': "Excellent! Please provide your evaluation questions for the project.",
            'confirmed_no': "Understood. We will proceed without evaluation questions.",
            'processing_error': "An error occurred while processing your request."
        }

        # Procesar la respuesta basada en la intención extraída
        if intention == 'yes':
            base_message = BASE_MESSAGES['confirmed_yes']
            evaluation_required = True
        elif intention == 'no':
            base_message = BASE_MESSAGES['confirmed_no']
            evaluation_required = False
        else:
            base_message = BASE_MESSAGES['ask_preference']
            evaluation_required = None

        # Traducir mensaje
        response_message = chatgpt.translate_message(base_message, detected_language)

        return jsonify({
            'success': True,
            'message': response_message,
            'detected_language': detected_language,
            'evaluation_required': evaluation_required,
            'answer_received': intention if evaluation_required is not None else None
        })

    except Exception as e:
        print(f"Error in evaluation questions: {str(e)}")
        error_message = chatgpt.translate_message(
            BASE_MESSAGES['processing_error'],
            detected_language if 'detected_language' in locals() else 'en'
        )
        return jsonify({
            'success': False,
            'message': error_message,
            'error': str(e)
        }), 500
    

##################################################
@app.route('/api/evaluation-questions-sections', methods=['POST'])
def evaluation_questions_sections():
    try:
        data = request.json
        if 'sections' not in data:
            base_error = 'Sections are required'
            return jsonify({
                'success': False,
                'message': base_error
            }), 400

        chatgpt = ChatGPTHelper()
        detected_language = data.get('language', 'en')

        # Mensajes base en inglés
        BASE_MESSAGES = {
            'request_questions': "Please provide evaluation questions for the {section} section.",
            'all_completed': "All evaluation questions have been collected successfully.",
            'processing_error': "An error occurred while processing your request."
        }

        # Solo procesar las secciones que el cliente envía
        sections = data['sections']  # Puede ser ["proveedores"] o ["empresas", "clientes"], etc.
        questions = data.get('questions', {})

        # Encontrar secciones que faltan
        missing_sections = [section for section in sections if section not in questions]

        if missing_sections:
            current_section = missing_sections[0]
            base_message = BASE_MESSAGES['request_questions'].format(section=current_section)
            response_message = chatgpt.translate_message(base_message, detected_language)

            return jsonify({
                'success': True,
                'status': 'pending',
                'message': response_message,
                'current_section': current_section,
                'remaining_sections': missing_sections[1:],
                'completed_sections': list(questions.keys()),
                'detected_language': detected_language
            })
        else:
            base_message = BASE_MESSAGES['all_completed']
            response_message = chatgpt.translate_message(base_message, detected_language)

            return jsonify({
                'success': True,
                'status': 'completed',
                'message': response_message,
                'sections_with_questions': questions,
                'detected_language': detected_language
            })

    except Exception as e:
        print(f"Error in evaluation sections: {str(e)}")
        error_message = chatgpt.translate_message(
            BASE_MESSAGES['processing_error'],
            detected_language if 'detected_language' in locals() else 'en'
        )
        return jsonify({
            'success': False,
            'message': error_message,
            'error': str(e)
        }), 500







@app.route('/api/industry-experts', methods=['POST'])
def industry_experts():
    try:
        data = request.json
        print(f"Received request data: {data}")
        print(f"ClientPerspective type: {type(data.get('clientPerspective'))}")
        print(f"ClientPerspective value: {data.get('clientPerspective')}")
        
        # Inicializar ChatGPTHelper y configurar idioma
        chatgpt = ChatGPTHelper()
        detected_language = data.get('language', 'en')
        print("1. Initial language detection:", detected_language)

        # Mensajes base en inglés
        BASE_MESSAGES = {
            'invalid_client_perspective': 'clientPerspective must be a boolean value or empty string',
            'invalid_employment_status': 'Invalid employment status. Must be one of: current, previous, or both',
            'missing_required_fields': 'Missing required fields: sector and processed_region',
            'processing_error': 'An error occurred while processing your request.'
        }
        
        # Extraer datos de phase2Data y phase3Data
        phase2_data = {
            'sector': data.get('sector', ''),
            'processed_region': data.get('processed_region', ''),
            'language': data.get('language', 'en'),
            'companies': data.get('companies', [])
        }

        # Modificar la validación de clientPerspective
        client_perspective = data.get('clientPerspective')
        if client_perspective == '':  # Si es una cadena vacía, convertir a False
            client_perspective = False
        elif client_perspective is not None and not isinstance(client_perspective, bool):
            return jsonify({
                'success': False,
                'message': chatgpt.translate_message(BASE_MESSAGES['invalid_client_perspective'], detected_language)
            }), 400

        # Manejar supplyChainRequired de manera similar
        supply_chain_required = data.get('supplyChainRequired')
        if supply_chain_required == '':
            supply_chain_required = False
        elif supply_chain_required is not None and not isinstance(supply_chain_required, bool):
            supply_chain_required = False

        phase3_data = {
            'employmentStatus': data.get('employmentStatus', ''),
            'excludedCompanies': data.get('excludedCompanies', []),
            'clientPerspective': client_perspective,
            'supplyChainRequired': supply_chain_required
        }

        # Validar que employmentStatus tenga un valor válido
        valid_employment_statuses = ['current', 'previous', 'both']
        if phase3_data['employmentStatus'] and phase3_data['employmentStatus'].lower() not in valid_employment_statuses:
            return jsonify({
                'success': False,
                'message': chatgpt.translate_message(BASE_MESSAGES['invalid_employment_status'], detected_language)
            }), 400

        # Validación de datos mínimos requeridos
        if not phase2_data['sector'] or not phase2_data['processed_region']:
            return jsonify({
                'success': False,
                'message': chatgpt.translate_message(BASE_MESSAGES['missing_required_fields'], detected_language)
            }), 400

        # Crear expertos base
        base_experts = [
            {
                'name': 'John Doe',
                'role': 'Senior Manager',
                'experience': '10 years',
                'companies_experience': ['Company A', 'Company B'],
                'expertise': ['Strategy', 'Operations'],
                'region_experience': ['North America', 'Europe'],
                'relevance_score': 0.9
            }
        ]
        print("2. Base experts before processing:", base_experts)

        # Agregar expertos de prueba si es tecnología en Norteamérica
        if phase2_data['sector'].lower() == 'technology' and 'north america' in phase2_data['processed_region'].lower():
            test_experts = [
                {
                    'name': 'expert_test1',
                    'role': 'Technology Director',
                    'experience': '15 years',
                    'companies_experience': ['Microsoft', 'Google'],
                    'expertise': ['Cloud Computing', 'AI Development'],
                    'region_experience': ['North America'],
                    'relevance_score': 0.95
                },
                {
                    'name': 'expert_test2',
                    'role': 'Software Architecture Lead',
                    'experience': '12 years',
                    'companies_experience': ['Amazon', 'Apple'],
                    'expertise': ['Software Architecture', 'System Design'],
                    'region_experience': ['North America'],
                    'relevance_score': 0.92
                }
            ]
            print("3. Test experts before adding:", test_experts)
            base_experts.extend(test_experts)
            print("4. Combined experts after extension:", base_experts)

        # Datos de ejemplo de expertos
        categorized_experts = {
            'companies': base_experts,
            'clients': [
                {
                    'name': 'Jane Smith',
                    'role': 'Client Relations Director',
                    'experience': '8 years',
                    'companies_experience': ['Company C', 'Company D'],
                    'expertise': ['Client Management', 'Business Development'],
                    'region_experience': ['Asia', 'Europe'],
                    'relevance_score': 0.85
                }
            ],
            'suppliers': [
                {
                    'name': 'Mike Johnson',
                    'role': 'Supply Chain Manager',
                    'experience': '12 years',
                    'companies_experience': ['Company E', 'Company F'],
                    'expertise': ['Supply Chain', 'Logistics'],
                    'region_experience': ['Global'],
                    'relevance_score': 0.95
                }
            ]
        }
        print("5. Initial categorized_experts:", categorized_experts)

        # Ordenar cada categoría por relevance_score
        for category in categorized_experts:
            categorized_experts[category] = sorted(
                categorized_experts[category],
                key=lambda x: x.get('relevance_score', 0),
                reverse=True
            )[:30]
        print("6. Categorized experts after sorting:", categorized_experts)

        # Definir títulos para cada categoría
        category_titles = {
            'companies': chatgpt.translate_message('Company Experts', detected_language),
            'clients': chatgpt.translate_message('Client Experts', detected_language),
            'suppliers': chatgpt.translate_message('Supplier Experts', detected_language)
        }

        selection_message = chatgpt.translate_message(
            "To select an expert, please write their full name.",
            detected_language
        )

        # Formatear respuesta final
        final_response = {
            'success': True,
            'experts_by_category': {
                'companies': {
                    'title': category_titles['companies'],
                    'experts': categorized_experts['companies']
                },
                'clients': {
                    'title': category_titles['clients'],
                    'experts': categorized_experts['clients']
                },
                'suppliers': {
                    'title': category_titles['suppliers'],
                    'experts': categorized_experts['suppliers']
                }
            },
            'total_experts': sum(len(cat) for cat in categorized_experts.values()),
            'filters_applied': {
                'sector': phase2_data['sector'],
                'processed_region': phase2_data['processed_region'],
                'companies': phase2_data['companies'],
                'employmentStatus': phase3_data['employmentStatus'].lower() if phase3_data['employmentStatus'] else '',
                'excludedCompanies': phase3_data['excludedCompanies'],
                'clientPerspective': phase3_data['clientPerspective'],
                'supplyChainRequired': phase3_data['supplyChainRequired']
            },
            'selection_message': selection_message,
            'detected_language': detected_language
        }
        print("7. Final response data:", final_response)

        return jsonify(final_response)

    except Exception as e:
        print(f"Error in industry experts: {str(e)}")
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
        data = request.json
        selected_experts = data.get('selected_experts')
        all_experts_data = data.get('all_experts_data')
        evaluation_questions = data.get('evaluation_questions', {})
        detected_language = data.get('all_experts_data', {}).get('detected_language', 'en')
        
        chatgpt = ChatGPTHelper()

        # Procesar el nombre del experto con ChatGPT primero
        if selected_experts and len(selected_experts) > 0:
            expert_name_result = chatgpt.extract_expert_name(selected_experts[0])
            expert_name = expert_name_result.get('name') if expert_name_result.get('success') else None
            if expert_name:
                selected_experts[0] = expert_name

        # Mensajes base en inglés
        BASE_MESSAGES = {
            'expert_required': 'At least one expert must be selected',
            'no_data_found': 'No expert data found',
            'expert_selected': 'You have selected the expert {name}.',
            'expert_not_found': 'No expert found with the name {name}',
            'processing_error': 'An error occurred while processing your request.',
            'thank_you': 'Thank you for contacting us! We will get in touch with you shortly.'
        }

        if not selected_experts:
            return jsonify({
                'success': False,
                'message': chatgpt.translate_message(BASE_MESSAGES['expert_required'], detected_language)
            }), 400

        if not all_experts_data:
            return jsonify({
                'success': False,
                'message': chatgpt.translate_message(BASE_MESSAGES['no_data_found'], detected_language)
            }), 400

        # Buscar el experto en todas las categorías
        selected_expert = None
        for category in all_experts_data['experts_by_category'].values():
            for expert in category['experts']:
                if expert['name'].lower() == selected_experts[0].lower():
                    selected_expert = expert
                    break
            if selected_expert:
                break

        if selected_expert:
            selection_message = chatgpt.translate_message(
                BASE_MESSAGES['expert_selected'].format(name=selected_experts[0]),
                detected_language
            )
            
            print(f"Detected language: {detected_language}")
            print(f"Original thank you message: {BASE_MESSAGES['thank_you']}")
            
            test_translation1 = chatgpt.translate_message(BASE_MESSAGES['thank_you'], detected_language)
            test_translation2 = chatgpt.translate_message(BASE_MESSAGES['thank_you'], detected_language)
            print(f"Test translation 1: {test_translation1}")
            print(f"Test translation 2: {test_translation2}")
            
            thank_you_message = chatgpt.translate_message(
                BASE_MESSAGES['thank_you'],
                detected_language
            )
            print(f"Translated thank you message: {thank_you_message}")

            response_data = {
                'success': True,
                'message': selection_message,
                'expert_details': selected_expert,
                'final_message': thank_you_message,
                'detected_language': detected_language
            }
            
            if evaluation_questions:
                response_data['evaluation_questions'] = evaluation_questions

            print(f"Response data being sent: {response_data}")
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


































    #########################################################################3
class ExpertSearch:
    def __init__(self):
        # Aquí podrías inicializar conexión a base de datos o configuraciones
        self.experts_db = self._mock_experts_database()  # Por ahora usamos datos mock

    def _mock_experts_database(self):
        # Base de datos simulada de expertos
        return [
            {
                "id": "exp001",
                "name": "John Smith",
                "sector": "Technology",
                "region": "North America",
                "current_company": "Tech Solutions Inc",
                "previous_companies": ["Google", "Microsoft"],
                "years_experience": 15,
                "expertise_level": "senior",
                "languages": ["english", "spanish"],
                "availability": "flexible",
                "specialties": ["cloud computing", "AI", "digital transformation"]
            },
            {
                "id": "exp002",
                "name": "Maria García",
                "sector": "Technology",
                "region": "Europe",
                "current_company": "Digital Innovators",
                "previous_companies": ["Amazon", "IBM"],
                "years_experience": 10,
                "expertise_level": "senior",
                "languages": ["english", "spanish", "french"],
                "availability": "part-time",
                "specialties": ["cybersecurity", "blockchain"]
            },
            {
                "id": "exp003",
                "name": "David Chen",
                "sector": "Finance",
                "region": "Asia",
                "current_company": "FinTech Solutions",
                "previous_companies": ["JP Morgan", "Goldman Sachs"],
                "years_experience": 12,
                "expertise_level": "senior",
                "languages": ["english", "mandarin"],
                "availability": "flexible",
                "specialties": ["investment banking", "risk management"]
            }
        ]

    def find_experts(self, sector, region=None, target_companies=None, excluded_companies=None, preferences=None):
        filtered_experts = []
        
        for expert in self.experts_db:
            # Filtro por sector (obligatorio)
            if expert['sector'].lower() != sector.lower():
                continue

            # Filtro por región
            if region and expert['region'].lower() != region.lower():
                continue

            # Filtro por empresas objetivo
            if target_companies:
                companies_match = False
                all_companies = [expert['current_company']] + expert['previous_companies']
                for company in target_companies:
                    if company in all_companies:
                        companies_match = True
                        break
                if not companies_match:
                    continue

            # Filtro por empresas excluidas
            if excluded_companies:
                skip_expert = False
                all_companies = [expert['current_company']] + expert['previous_companies']
                for company in excluded_companies:
                    if company in all_companies:
                        skip_expert = True
                        break
                if skip_expert:
                    continue

            # Filtro por preferencias
            if preferences:
                if 'years_experience' in preferences:
                    if expert['years_experience'] < preferences['years_experience']:
                        continue
                
                if 'expertise_level' in preferences:
                    if expert['expertise_level'] != preferences['expertise_level']:
                        continue
                
                if 'languages' in preferences:
                    if not any(lang in expert['languages'] for lang in preferences['languages']):
                        continue
                
                if 'availability' in preferences:
                    if expert['availability'] != preferences['availability']:
                        continue

            filtered_experts.append(expert)

        return filtered_experts
    







@app.route('/api/experts/search', methods=['POST'])
def search_experts():
    try:
        data = request.json
        
        # Validación de campos requeridos
        if 'sector' not in data:
            return jsonify({
                'success': False,
                'message': 'Sector is required'
            }), 400

        # Extraer parámetros de búsqueda
        sector = data.get('sector')
        region = data.get('region')
        target_companies = data.get('target_companies', [])
        excluded_companies = data.get('excluded_companies', [])
        expert_preferences = data.get('expert_preferences', {})
        
        # Inicializar búsqueda de expertos
        expert_search = ExpertSearch()
        
        # Aplicar filtros de búsqueda
        experts = expert_search.find_experts(
            sector=sector,
            region=region,
            target_companies=target_companies,
            excluded_companies=excluded_companies,
            preferences=expert_preferences
        )

        return jsonify({
            'success': True,
            'experts': experts,
            'total_found': len(experts),
            'filters_applied': {
                'sector': sector,
                'region': region,
                'target_companies': target_companies,
                'excluded_companies': excluded_companies,
                'preferences': expert_preferences
            }
        })

    except Exception as e:
        print(f"Error in expert search: {str(e)}")
        return jsonify({
            'success': False,
            'error': "An error occurred while searching for experts"
        }), 500
    





""""

def process_message_internal(data):
    try:
        print("\n=== Processing Message ===")
        print("Data:", data)

        location = data.get('message')
        sector = data.get('sector')
        detected_language = data.get('language') or chatgpt.detected_language_from_content(location)

        if not location:
            error_message = chatgpt.translate_message(
                'Location cannot be empty',
                detected_language
            )
            return jsonify({
                'success': False,
                'message': error_message
            })

        # Si no hay sector, solo procesar la región
        if not sector:
            region_result = chatgpt.identify_region(location)
            if region_result['success']:
                response_message = chatgpt.translate_message(
                    f"He identificado la región como {region_result['region']}. Por favor, especifique el sector empresarial.",
                    detected_language
                )
                return jsonify({
                    'success': True,
                    'region': region_result['region'],
                    'message': response_message,
                    'language': detected_language,
                    'needsSector': True
                })
            else:
                error_message = chatgpt.translate_message(
                    "Por favor, proporciona una región válida (Norte América, Europa o Asia)",
                    detected_language
                )
                return jsonify({
                    'success': False,
                    'message': error_message,
                    'language': detected_language
                })

        # Si hay sector, procesar sector
        sector_result = chatgpt.translate_sector(sector)
        if sector_result.get('success') and sector_result.get('is_valid'):
            translated_sector = sector_result['translated_sector']
            region_result = chatgpt.identify_region(location)
            
            if region_result['success']:
                zoho_companies = zoho_service.get_accounts_by_industry_and_region(
                    industry=translated_sector,
                    region=region_result['region']
                )

                companies_needed = 20 - len(zoho_companies)
                chatgpt_suggestions = []

                if companies_needed > 0:
                    chatgpt_result = chatgpt.get_companies_suggestions(
                        sector=translated_sector,
                        geography=region_result['region']
                    )
                    if chatgpt_result['success']:
                        chatgpt_suggestions = chatgpt_result['content'][:companies_needed]

                response_message = chatgpt.translate_message(
                    f"Has seleccionado el sector {sector_result['displayed_sector']}",
                    detected_language
                )

                return jsonify({
                    'success': True,
                    'sector': translated_sector,
                    'displayed_sector': sector_result['displayed_sector'],
                    'message': response_message,
                    'language': detected_language,
                    'companies': {
                        'zoho_companies': zoho_companies,
                        'suggested_companies': [{'name': company} for company in chatgpt_suggestions]
                    }
                })

        error_message = chatgpt.translate_message(
            f"Sector no válido. Por favor, elija entre: {sector_result.get('available_sectors')}",
            detected_language
        )
        return jsonify({
            'success': False,
            'message': error_message,
            'language': detected_language
        })

    except Exception as e:
        print(f"\n=== Error in process_message_internal ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error processing request'
        }), 500
    


"""
@app.route('/api/ai/voice/process', methods=['POST'])
def process_voice():
    print("\n=== New Voice Request ===")
    print("Headers:", dict(request.headers))

    try:
        # Usar el VoiceHandler existente
        voice_result = voice_handler.handle_voice_request(request)
        
        # Devolver solo la transcripción y el idioma
        return jsonify({
            'success': True,
            'detected_language': voice_result.get('detected_language', 'es'),
            'transcription': voice_result.get('transcription')
        })

    except Exception as e:
        print(f"Error in voice processing: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


"""
def process_message_with_language(data: dict, detected_language: str):
    print("\n=== New Request with Language===")
    print("Data:", data)
    print("Detected Language:", detected_language)

    try:
        if 'message' not in data:
            return jsonify({
                'success': False,
                'message': 'Location (message) is required',
                'language': detected_language
            })

        location = data.get('message')
        sector = data.get('sector')

        print(f"\n===Validating Input===")
        print(f"Location: {location}")
        print(f"Sector: {sector}")

        if not location:
            return jsonify({
                'success': False,
                'message': 'Location cannot be empty',
                'language': detected_language
            })

        print("\n=== Initializing ChatGPT===")
        chatgpt = ChatGPTHelper()
        
        # Usar el nuevo método process_text_input
        if not sector:
            text_result = chatgpt.process_text_input(location)
            if not text_result['success']:
                return jsonify({
                    'success': False,
                    'message': text_result['message'],
                    'language': detected_language
                })
            
            return jsonify({
                'success': True,
                'message': text_result['message'],
                'region': text_result['region'],
                'language': text_result['detected_language'],
                'needsSector': True
            })

        # El resto del código para cuando hay sector permanece igual
        region_result = chatgpt.identify_region(location)
        if not region_result['success']:
            return jsonify({
                'success': False,
                'message': 'Location not in supported regions (North America, Europe, Asia)',
                'language': detected_language
            })

        region = region_result['region']

        if sector not in VALID_SECTORS:
            return jsonify({
                'success': False,
                'message': f'Invalid sector. Must be one of: {",".join(VALID_SECTORS)}',
                'language': detected_language
            })

        zoho_companies = zoho_service.get_accounts_by_industry_and_region(
            industry=sector,
            region=region
        )

        companies_needed = 20 - len(zoho_companies)
        chatgpt_suggestions = []

        if companies_needed > 0:
            chatgpt_result = chatgpt.get_companies_suggestions(
                sector=sector,
                geography=region
            )

            if chatgpt_result['success']:
                chatgpt_suggestions = chatgpt_result['content'][:companies_needed]

        return jsonify({
            'success': True,
            'message': f'Found {sector} companies in {region}',
            'companies': {
                'zoho_companies': zoho_companies,
                'suggested_companies': [
                    {'name': company} for company in chatgpt_suggestions
                ]
            },
            'language': detected_language
        })

    except Exception as e:
        print(f"\n=== Error in message processing===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error processing your request',
            'language': detected_language
        }), 500





@app.route('/process-message', methods=['POST', 'OPTIONS'])
def process_message():
    print("\n=== New Request to /process-message ===")
    print("Method:", request.method)
    print("Headers:", dict(request.headers))
    
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})

    try:
        data = request.json
        print("\n=== Request Data ===")
        print("Received data:", data)  

        location = data.get('message')
        sector = data.get('sector')
        detected_language = data.get('language') or chatgpt.detected_language_from_content(location)

        print(f"\n=== Processing with parameters ===")
        print(f"Location: {location}")
        print(f"Sector: {sector}")
        print(f"Language: {detected_language}")

        # Validar entrada
        if not location or sector is None:
            error_message = chatgpt.translate_message(
                'Both location and sector are required',
                detected_language
            )
            return jsonify({
                'success': False,
                'message': error_message,
                'language': detected_language
            })

        # Traducir sector
        sector_result = chatgpt.translate_sector(sector)
        if not sector_result['success'] or not sector_result['is_valid']:
            error_message = f'Invalid sector. Must be one of: {sector_result.get("available_sectors", ", ".join(VALID_SECTORS))}'
            translated_error = chatgpt.translate_message(error_message, detected_language)
            return jsonify({
                'success': False,
                'message': translated_error,
                'language': detected_language
            })

        translated_sector = sector_result['translated_sector']
        displayed_sector = sector_result['displayed_sector']

        # Identificar región
        region_result = chatgpt.identify_region(location)
        if not region_result['success']:
            error_message = chatgpt.translate_message(
                'Location not in supported regions (North America, Europe, Asia)',
                detected_language
            )
            return jsonify({
                'success': False,
                'message': error_message,
                'language': detected_language
            })

        region = region_result['region']

        # Obtener empresas de Zoho
        zoho_companies = zoho_service.get_accounts_by_industry_and_region(
            industry=translated_sector,
            region=region
        )

        # Obtener sugerencias de ChatGPT
        companies_needed = 20 - len(zoho_companies)
        chatgpt_suggestions = []

        if companies_needed > 0:
            print(f"\n=== Getting ChatGPT Suggestions ===")
            print(f"Need {companies_needed} more companies")
            
            chatgpt_result = chatgpt.get_companies_suggestions(
                sector=translated_sector,
                geography=region
            )
            
            if chatgpt_result['success']:
                chatgpt_suggestions = chatgpt_result['content'][:companies_needed]
                print(f"Got {len(chatgpt_suggestions)} suggestions from ChatGPT")

        # Preparar respuesta
        response_message = chatgpt.translate_message(
            f"Found {displayed_sector} companies in {region}",
            detected_language
        )

        response = {
            'success': True,
            'message': response_message,
            'detected_language': detected_language,
            'region': region,
            'sector': {
                'translated': translated_sector,
                'displayed': displayed_sector
            },
            'companies': {
                'zoho': zoho_companies,
                'suggestions': [{'name': company} for company in chatgpt_suggestions],
                'total_count': len(zoho_companies) + len(chatgpt_suggestions)
            }
           
        }

        print("\n=== Response prepared successfully ===")
        print("Companies found:", response['companies']['total_count'])
        return jsonify(response)

    except Exception as e:
        print(f"\n=== Error in process_message ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        error_message = chatgpt.translate_message(
            'Error processing your request',
            detected_language if 'detected_language' in locals() else 'en'
        )
        return jsonify({
            'success': False,
            'message': error_message,
            'error_details': str(e)
        }), 500
    """
    
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