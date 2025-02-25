from flask import jsonify
from src.utils.chatgpt_helper import ChatGPTHelper
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_geography_capture(request_json):
    try:
        logger.info("Starting geography capture handler")

        chatgpt = ChatGPTHelper()
        logger.info("ChatGPT initialized")

      
        location = request_json['queryResult']['parameters'].get('geography')
        
        
        region_result = chatgpt.identify_region(location)
        
        if not region_result['success']:
            return jsonify({
                "fulfillmentText": "I'm sorry, but I can only search in North America, Europe, or Asia at the moment. Could you specify a location in one of these regions?"
            })

      
        sector = None
        for context in request_json['queryResult']['outputContexts']:
            if 'awaiting_geography' in context['name']:
                sector = context['parameters'].get('sector')
                break

        output_context = {
            "name": f"{request_json['session']}/contexts/ready_for_suggestions",
            "lifespanCount": 5,
            "parameters": {
                "geography": region_result['region'],
                "original_location": location,
                "sector": sector
            }
        }
        
        message = f"I'll look for companies in {region_result['region']} (based on your location: {location})"
        
        return jsonify({
            "fulfillmentText": message,
            "outputContexts": [output_context]
        })
    
    except Exception as e:
        logger.error(f"Error in geography handler: {str(e)}")
        return jsonify({
            "fulfillmentText": f"An error occurred: {str(e)}"
        })