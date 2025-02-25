from flask import jsonify
from src.utils.chatgpt_helper import ChatGPTHelper

def handle_sector_capture(request_json):
    chatgpt = ChatGPTHelper()
    
    raw_sector = request_json['queryResult']['parameters'].get('sector')
    
    if not raw_sector:
        return jsonify({
            'fulfillmentText': "I didn't catch the sector. Could you please specify which industry sector you're interested in?"
        })

    sector = raw_sector.strip()
    
    # Traducir y validar el sector
    sector_result = chatgpt.translate_sector(sector)
    
    if not sector_result["success"] or not sector_result["is_valid"]:
        error_message = "I didn't recognize that sector. Please choose from: Technology, Financial Services, Manufacturing."
        # Traducir mensaje de error al idioma del usuario si es necesario
        if chatgpt.current_language != 'en':
            error_message = chatgpt.translate_message(error_message, chatgpt.current_language)
        
        return jsonify({
            'fulfillmentText': error_message
        })

    # Usar el sector traducido para el contexto interno
    validated_sector = sector_result["translated_sector"]
    
    # Traducir la respuesta al idioma del usuario si es necesario
    response_text = f"Great, you're interested in the {validated_sector} sector. Which geographical region would you like to focus on?"
    if chatgpt.current_language != 'en':
        response_text = chatgpt.translate_message(response_text, chatgpt.current_language)

    return jsonify({
        'fulfillmentText': response_text,
        'outputContexts': [
            {
                'name': f"{request_json['session']}/contexts/awaiting_geography",
                'lifespanCount': 5,
                'parameters': {'sector': validated_sector}
            }
        ]
    })