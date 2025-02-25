from flask import Blueprint, request, jsonify
from ...handlers.phase2_handlers import sector_handler, company_handler

phase2_routes = Blueprint('phase2', __name__)

@phase2_routes.route('/sector-experience', methods=['POST'])
def handle_sector_experience():
    return sector_handler.handle_sector_experience(request)