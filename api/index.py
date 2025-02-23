import sys
from pathlib import Path
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

# Mover esta línea al inicio
sys.path.append(str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from waitress import serve
from src.handlers.email_handler import handle_email_capture
from src.handlers.sector_handler import handle_sector_capture
from src.handlers.geography_handler import handle_geography_capture
from src.handlers.voice_handler import VoiceHandler
from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.zoho_services import ZohoService
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

@app.route('/', methods=['POST'])
def webhook():
    try:
        request_json = request.get_json()
        intent_name = request_json['queryResult']['intent']['displayName']

        if intent_name == 'Capture_Email':
            return handle_email_capture(request_json)
        elif intent_name == 'Capture_Sector':
            return handle_sector_capture(request_json)
        elif intent_name == 'Capture_Geography':
            return handle_geography_capture(request_json)
        
        return jsonify({
            'fulfillmentText': "Sorry, I couldn't process that request."
        })

    except Exception as e:
        print(f"Error in webhook: {str(e)}")
        return jsonify({
            'fulfillmentText': "An error occurred while processing your request."
        })
    

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
            },
            'messages': {
                'companies_found': chatgpt.translate_message("Companies Found:", detected_language),
                'from_database': chatgpt.translate_message("From Database:", detected_language),
                'additional_suggestions': chatgpt.translate_message("Additional Suggestions:", detected_language)
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
    

@app.route('/api/ai/test/process-text', methods=['POST'])
def test_process_text():
    try:
        data = request.json
        if 'text' not in data:
            return jsonify({
                'success': False,
                'message': 'Text is required'
            }), 400

        chatgpt = ChatGPTHelper()
        result = chatgpt.process_text_input(data['text'])
        
        return jsonify(result)

    except Exception as e:
        print(f"Error in test_process_text: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error processing text'
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