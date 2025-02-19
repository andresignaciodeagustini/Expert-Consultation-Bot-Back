import sys
from pathlib import Path
import os
from dotenv import load_dotenv
import requests

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

from flask import Flask, request, jsonify
from flask_cors import CORS
from waitress import serve
from src.handlers.email_handler import handle_email_capture
from src.handlers.sector_handler import handle_sector_capture
from src.handlers.geography_handler import handle_geography_capture
from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.zoho_services import ZohoService
from src.utils.config import VALID_SECTORS

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

print("\n=== Initializing Services ===")
zoho_service = ZohoService()

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

        if 'message' not in data or 'sector' not in data:
            return jsonify({
                'success': False,
                'message': 'Both location (message) and sector are required parameters'
            })

        location = data.get('message')
        sector = data.get('sector')
        
        print(f"\n=== Validating Input ===")
        print(f"Location: {location}")
        print(f"Sector: {sector}")
        
        if not location or not sector:
            return jsonify({
                'success': False,
                'message': 'Location and sector cannot be empty'
            })
        
        if sector not in VALID_SECTORS:
            print(f"Invalid sector. Valid sectors are: {VALID_SECTORS}")
            return jsonify({
                'success': False,
                'message': f'Invalid sector. Must be one of: {", ".join(VALID_SECTORS)}'
            })

        print("\n=== Initializing ChatGPT ===")
        chatgpt = ChatGPTHelper()
       
        print("\n=== Region Identification ===")
        region_result = chatgpt.identify_region(location)
        print(f"Region result: {region_result}")  

        if not region_result['success']:
            return jsonify({
                'success': False,
                'message': 'Location not in supported regions(North America, Europe, Asia)'
            })

        region = region_result['region']
        
        print(f"\n=== Searching Zoho Companies ===")
        print(f"Industry: {sector}")
        print(f"Region: {region}")
        print(f"Using token: {token[:10]}...{token[-10:]}")
        
        zoho_companies = zoho_service.get_accounts_by_industry_and_region(
            industry=sector,
            region=region
        )
        print(f"Found {len(zoho_companies)} companies in Zoho")

        companies_needed = 20 - len(zoho_companies)
        chatgpt_suggestions = []

        if companies_needed > 0:
            print(f"\n=== Getting ChatGPT Suggestions ===")
            print(f"Need {companies_needed} more companies")
            chatgpt_result = chatgpt.get_companies_suggestions(
                sector=sector,
                geography=region
            )
            if chatgpt_result['success']:
                chatgpt_suggestions = chatgpt_result['content'][:companies_needed]
                print(f"Got {len(chatgpt_suggestions)} suggestions from ChatGPT")
        
        print("\n=== Preparing Response ===")
        response = {
            'success': True,
            'message': f'Found {sector} companies in {region}',
            'companies': {
                'zoho_companies': zoho_companies,
                'suggested_companies': [
                    {'name': company} for company in chatgpt_suggestions
                ]
            }
        }
        print("Response prepared successfully")
        return jsonify(response)

    except Exception as e:
        print(f"\n=== Error in process_message ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error processing your request'
        }), 500

@app.route('/test', methods=['GET'])
def test():
    return jsonify({
        'message': 'Backend is running!',
        'status': 'OK'
    })

if __name__ == '__main__':
    print("\n=== Starting Server ===")
    print("Server URL: http://127.0.0.1:8080")
    serve(app, host='0.0.0.0', port=8080)