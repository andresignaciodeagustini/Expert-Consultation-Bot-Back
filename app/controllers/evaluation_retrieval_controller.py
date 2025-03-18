from app.services.evaluation_retrieval_service import EvaluationRetrievalService

class EvaluationRetrievalController:
    def __init__(self, evaluation_retrieval_service=None):
        """
        Inicializar controlador de recuperación de evaluación
        
        :param evaluation_retrieval_service: Servicio de recuperación de evaluación
        """
        self.evaluation_retrieval_service = (
            evaluation_retrieval_service or 
            EvaluationRetrievalService()
        )

    def validate_input(self, project_id):
        """
        Validar el ID del proyecto
        
        :param project_id: ID del proyecto
        :return: Resultado de validación
        """
        if not project_id:
            return {
                'is_valid': False,
                'error': 'Project ID is required'
            }
        
        if not isinstance(project_id, (str, int)):
            return {
                'is_valid': False,
                'error': 'Invalid project ID format'
            }
        
        return {
            'is_valid': True,
            'project_id': str(project_id)
        }

    def get_evaluation(self, project_id):
        """
        Obtener evaluación
        
        :param project_id: ID del proyecto
        :return: Resultado de la recuperación
        """
        try:
            # Validar entrada
            validation_result = self.validate_input(project_id)
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'status_code': 400
                }
            
            # Recuperar evaluación
            result = self.evaluation_retrieval_service.get_evaluation_by_project_id(
                validation_result['project_id']
            )
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200 if result.get('success', False) else 404
            
            return result

        except Exception as e:
            return {
                'success': False,
                'message': 'An error occurred while retrieving the evaluation',
                'error': str(e),
                'status_code': 500
            }

    def reset_last_detected_language(self, language='en'):
        """
        Método placeholder para mantener consistencia con otros controladores
        
        :param language: Idioma por defecto
        """
        # Este método puede ser útil si se añade funcionalidad de detección de idioma en el futuro
        pass