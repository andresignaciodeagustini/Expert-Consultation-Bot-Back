from flask import Blueprint, jsonify

test_routes = Blueprint('test', __name__)

@test_routes.route('/test', methods=['GET'])
def test():
    return jsonify({
        'message': 'Backend is running!',
        'status': 'OK',
        'endpoints': {
            'webhook': '/',
            'process-messages': '/process-messages',
            'voice': '/api/ai/voice/process',
            'detect-language': '/api/detect-language',
            'translate': '/api/ai/translate',
            'email-capture': '/api/ai/email/capture',
            'process-text': '/api/ai/test/process-text',
            'test': '/test',
            'welcome-message': '/api/welcome-message',
            'name-capture': '/api/ai/name/capture',
            'expert-connection': '/api/ai/expert-connection/ask',
            'sector-experience': '/api/sector-experience',
            'company-suggestions': '/api/company-suggestions-test',
            'companies-agreement': '/api/process-companies-agreement',
            'industry-experts': '/api/industry-experts',
            'select-experts': '/api/select-experts',
            'evaluation-questions': '/api/evaluation-questions',
            'evaluation-questions-sections': '/api/evaluation-questions-sections',
            'save-evaluation': '/api/save-evaluation',
            'get-evaluation': '/api/get-evaluation/<project_id>',
            'exclude-companies': '/api/exclude-companies',
            'client-perspective': '/api/client-perspective',
            'zoho-candidates': '/api/recruit/candidates',
            'zoho-jobs': '/api/recruit/jobs',
             'zoho-candidates-search': '/api/recruit/candidates/search',
            'server-ping': '/api/ping',
            'supply-chain-experience': '/api/supply-chain-experience'
        }
    })