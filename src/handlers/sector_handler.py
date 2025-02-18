
from flask import jsonify

def handle_sector_capture(request_json):
    
    raw_sector = request_json['queryResult']['parameters'].get('sector')
    
    
    sector = raw_sector.strip().lower() if raw_sector else ''

    if sector:
        return jsonify({
            'fulfillmentText': f"Great, you're interested in the {sector} sector. Which geographical region would you like to focus on?",
            'outputContexts': [
                {
                    'name': f"{request_json['session']}/contexts/awaiting_geography",
                    'lifespanCount': 5,
                    'parameters': {'sector': sector}
                }
            ]
        })
    else:
        return jsonify({
            'fulfillmentText': "I didn't catch the sector. Could you please specify which industry sector you're interested in?"
        })