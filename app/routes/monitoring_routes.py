from flask import Blueprint, jsonify
from app.controllers.server_monitoring_controller import ServerMonitoringController

monitoring_routes = Blueprint('monitoring', __name__)
server_monitoring_controller = ServerMonitoringController()

@monitoring_routes.route('/ping', methods=['GET'])
def ping():
    return jsonify(server_monitoring_controller.ping())