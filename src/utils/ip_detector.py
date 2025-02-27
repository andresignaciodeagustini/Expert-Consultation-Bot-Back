import requests

class IPDetector:
    @staticmethod
    def get_ip_info(test_ip=None):
        try:
            # Usar IP de prueba si se proporciona
            if test_ip:
                ip_address = test_ip
            else:
                ip_response = requests.get('https://api.ipify.org?format=json')
                ip_address = ip_response.json()['ip']
            
            # Obtener información detallada de la IP
            response = requests.get(f'https://ipapi.co/{ip_address}/json/')
            data = response.json()
            
            # Verificar si hay error en la respuesta
            if response.status_code != 200 or 'error' in data:
                raise Exception(f"Error en la API: {data.get('error', 'Unknown error')}")
            
            return {
                'ip': ip_address,
                'country': data.get('country_name'),
                'country_code': data.get('country_code'),
                'city': data.get('city'),
                'region': data.get('region'),
                'languages': data.get('languages', '').split(',')[0]
            }
            
        except Exception as e:
            print(f"Error en la detección de IP: {e}")
            return {
                'ip': ip_address if 'ip_address' in locals() else None,
                'country': 'Unknown',
                'country_code': 'XX',
                'city': 'Unknown',
                'region': 'Unknown',
                'languages': 'en'
            }

    @staticmethod
    def get_user_language(test_ip=None):
        """
        Obtiene solo el idioma del usuario
        """
        ip_info = IPDetector.get_ip_info(test_ip)
        return ip_info['languages']