from flask import jsonify
import random
from ...utils.constants import CLIENT_DOMAINS



VERIFIED_CLIENT_RESPONSES = [

    "Thank you. What sector or industry are you looking to explore?",
    "Great, I've verified your account. Which industry sector would you like to explore?",
    "Perfect, I've confirmed your client status. What industry should we focus on?",
    "Excellent! To help you find the right experts, which sector are you interested in?"
]

NEW_CLIENT_RESPONSES = [

    "Thank you. It seems you're new here. Would you like to schedule a call with our team?",
    "I noticed this is your first time here. Would you like to schedule an introduction call?",
    "Welcome! As a new visitor, we'd love to schedule a call to understand your needs better.",
    "As a new user, we'd like to learn more about your needs. Shall we schedule a brief call?"


]

def handle_email_capture(request_json):
    """
    Handle the email capture intent and verify client status

    Args: 
        request_json (dict): The request data from Dialogflow
    
    Returns:
        json: Response with appropiate message based on client status    
    """
    email = request_json ['queryResult']['parameters']['email']
    domain = email.split('@') [1]

    if domain in CLIENT_DOMAINS:
        return jsonify({

            'fulfillmentText': "Thank you. What sector or industry are you looking to explore?",
            'outputContexts' : [
                {

                    'name': f"{request_json['session']}/contexts/awaiting_sector",
                    'lifespanCount' : 5,
                    'parameters' : {'email':email}
                }


            ]
        })
    
    else:
        return jsonify({
                'fulfilmentText': random.choice(NEW_CLIENT_RESPONSES)
            })