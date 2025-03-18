from flask import Blueprint
from app.controllers.token_controller import TokenController

token_routes = Blueprint('token', __name__)

token_routes.route('/refresh-token', methods=['POST'])(TokenController.refresh_token)