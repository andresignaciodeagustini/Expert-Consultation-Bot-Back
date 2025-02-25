import functions_framework
from flask import jsonify
from src.handlers.phase1_handlers.email_handler import handle_email_capture
from src.handlers.sector_handler import handle_sector_capture
from src.handlers.geography_handler import handle_geography_capture




@functions_framework.http

def webhook(request):
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
        
            print (f"Error:{str(e)}")
            return jsonify({
                 'fulfillmentText': "An error ocurred while processing your request."
            })
        

if __name__ == "__main__":
    import os
    os.environ["FUNCTION_TARGET"] = "webhook"
    functions_framework.start()