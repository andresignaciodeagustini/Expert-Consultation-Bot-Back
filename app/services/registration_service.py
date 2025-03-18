from app.constants.emails import REGISTERED_TEST_EMAILS

class RegistrationService:
    @staticmethod
    def is_email_registered(email: str) -> bool:
        """
        Verificar si un email está registrado
        
        :param email: Email a verificar
        :return: Booleano indicando si el email está registrado
        """
        return email.lower() in [e.lower() for e in REGISTERED_TEST_EMAILS]