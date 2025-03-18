from flask import Blueprint, jsonify, request
from app.controllers.zoho_recruit_controller import ZohoRecruitController

zoho_routes = Blueprint('zoho', __name__)
zoho_recruit_controller = ZohoRecruitController()

@zoho_routes.route('/recruit/candidates', methods=['GET'])
def get_candidates():
    try:
        response, status_code = zoho_recruit_controller.get_candidates()
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@zoho_routes.route('/recruit/jobs', methods=['GET'])
def get_jobs():
    try:
        response, status_code = zoho_recruit_controller.get_jobs()
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@zoho_routes.route('/recruit/candidates/search', methods=['GET'])
def search_candidates():
    try:
        criteria = request.args.get('criteria', '')
        response, status_code = zoho_recruit_controller.search_candidates(criteria)
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500