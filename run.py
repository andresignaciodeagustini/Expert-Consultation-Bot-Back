from flask import Flask, request, jsonify
from flask_cors import CORS
from waitress import serve
from src.handlers.email_handler import handle_email_capture
from src.handlers.sector_handler import handle_sector_capture
from src.handlers.geography_handler import handle_geography_capture
from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.zoho_services import ZohoService

app = Flask(__name__)
CORS(app)

VALID_SECTORS = ["Technology", "Financial Services", "Manufacturing"]


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
        print(f"Error: {str(e)}")
        return jsonify({
            'fulfillmentText': "An error occurred while processing your request."
        })

@app.route('/process-message', methods=['POST'])
def process_message():
    try:
        data = request.json
        print("Received data:", data)  

        if 'message' not in data or 'sector' not in data:
            return jsonify({
                'success': False,
                'message': 'Both location (message) and sector are required parameters'
            })

        location = data.get('message')
        sector = data.get('sector')

        
        if not location or not sector:
            return jsonify({
                'success': False,
                'message': 'Location and sector cannot be empty'
            })

        
        if sector not in VALID_SECTORS:
            return jsonify({
                'success': False,
                'message': f'Invalid sector. Must be one of: {", ".join(VALID_SECTORS)}'
            })

        chatgpt = ChatGPTHelper()
        zoho_service = ZohoService()

       
        region_result = chatgpt.identify_region(location)
        print(f"Region result: {region_result}")  

        if not region_result['success']:
            return jsonify({
                'success': False,
                'message': 'Location not in supported regions(North America, Europe, Asia)'
            })

        region = region_result['region']

        
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
            }
        })

    except Exception as e:
        print(f"Error processing message: {str(e)}")
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
    print("Starting server on http://127.0.0.1:8080")
    serve(app, host='0.0.0.0', port=8080)