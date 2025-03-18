from flask import Blueprint, request, jsonify
from app.controllers.email_capture_controller import EmailCaptureController
from app.controllers.name_capture_controller import NameCaptureController
from app.controllers.expert_connection_controller import ExpertConnectionController
from app.controllers.sector_experience_controller import SectorExperienceController
from app.controllers.text_processing_controller import TextProcessingController
from app.controllers.simple_expert_connection_controller import SimpleExpertConnectionController
from app.controllers.company_suggestions_controller import CompanySuggestionsController
from app.controllers.companies_agreement_controller import CompaniesAgreementController
from app.controllers.employment_status_controller import EmploymentStatusController
from app.controllers.exclude_companies_controller import ExcludeCompaniesController
from app.controllers.client_perspective_controller import ClientPerspectiveController
from app.controllers.supply_chain_experience_controller import SupplyChainExperienceController
from app.controllers.evaluation_questions_controller import EvaluationQuestionsController

from app.controllers.evaluation_questions_sections_controller import EvaluationQuestionsSectionsController
from app.controllers.evaluation_controller import EvaluationController
from app.controllers.evaluation_retrieval_controller import EvaluationRetrievalController
from app.controllers.industry_experts_controller import IndustryExpertsController
from app.controllers.expert_selection_controller import ExpertSelectionController


conversation_routes = Blueprint('conversation', __name__)

email_capture_controller = EmailCaptureController()
name_capture_controller = NameCaptureController()
expert_connection_controller = ExpertConnectionController()
sector_experience_controller = SectorExperienceController()
text_processing_controller = TextProcessingController()
simple_expert_connection_controller = SimpleExpertConnectionController()
company_suggestions_controller = CompanySuggestionsController()
companies_agreement_controller = CompaniesAgreementController()
employment_status_controller = EmploymentStatusController()
exclude_companies_controller = ExcludeCompaniesController()
client_perspective_controller = ClientPerspectiveController()
supply_chain_experience_controller = SupplyChainExperienceController()
evaluation_questions_controller = EvaluationQuestionsController()
evaluation_questions_sections_controller = EvaluationQuestionsSectionsController()
evaluation_controller = EvaluationController()
evaluation_retrieval_controller = EvaluationRetrievalController()
industry_experts_controller = IndustryExpertsController()
expert_selection_controller = ExpertSelectionController()


@conversation_routes.route('/ai/email/capture', methods=['POST'])
def capture_email():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = email_capture_controller.capture_email(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@conversation_routes.route('/ai/name/capture', methods=['POST'])
def capture_name():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = name_capture_controller.capture_name(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@conversation_routes.route('/ai/expert-connection/ask', methods=['POST'])
def ask_expert_connection():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = expert_connection_controller.ask_expert_connection(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@conversation_routes.route('/sector-experience', methods=['POST'])
def sector_experience():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = sector_experience_controller.process_sector_experience(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@conversation_routes.route('/ai/test/process-text', methods=['POST'])
def test_process_text():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = text_processing_controller.process_text(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
@conversation_routes.route('/simple-expert-connection', methods=['POST'])
def simple_expert_connection():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = simple_expert_connection_controller.process_simple_expert_connection(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    


@conversation_routes.route('/company-suggestions-test', methods=['POST'])
def company_suggestions_test():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = company_suggestions_controller.get_company_suggestions(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@conversation_routes.route('/process-companies-agreement', methods=['POST'])
def process_companies_agreement():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = companies_agreement_controller.process_companies_agreement(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    


@conversation_routes.route('/specify-employment-status', methods=['POST'])
def specify_employment_status():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = employment_status_controller.process_employment_status(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@conversation_routes.route('/exclude-companies', methods=['POST'])
def exclude_companies():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = exclude_companies_controller.process_exclude_companies(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    

@conversation_routes.route('/client-perspective', methods=['POST'])
def client_perspective():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = client_perspective_controller.process_client_perspective(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@conversation_routes.route('/supply-chain-experience', methods=['POST'])
def supply_chain_experience():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = supply_chain_experience_controller.process_supply_chain_experience(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@conversation_routes.route('/evaluation-questions', methods=['POST'])
def evaluation_questions():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = evaluation_questions_controller.process_evaluation_questions(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    


@conversation_routes.route('/evaluation-questions-sections', methods=['POST'])
def evaluation_questions_sections():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = evaluation_questions_sections_controller.process_evaluation_questions_sections(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
@conversation_routes.route('/save-evaluation', methods=['POST'])
def save_evaluation():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = evaluation_controller.save_evaluation(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
@conversation_routes.route('/get-evaluation/<project_id>', methods=['GET'])
def get_evaluation(project_id):
    try:
        # Elimina la asignación de status_code
        response = evaluation_retrieval_controller.get_evaluation(project_id)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 404
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    


@conversation_routes.route('/industry-experts', methods=['POST'])
def industry_experts():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = industry_experts_controller.get_industry_experts(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@conversation_routes.route('/select-experts', methods=['POST'])
def select_experts():
    try:
        data = request.json
        # Elimina la asignación de status_code
        response = expert_selection_controller.select_experts(data)
        
        # Determina el código de estado basado en la respuesta
        status_code = 200 if response.get('success', False) else 400
        
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500