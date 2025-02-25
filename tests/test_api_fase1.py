import requests
import json

def test_email_capture(base_url, email, text):
    try:
        # Cambiando a la URL específica para email
        url = 'http://127.0.0.1:8080/api/ai/email/capture'
        print(f"Intentando conectar a: {url}")
        data = {
            "email": email,
            "text": text
        }
        response = requests.post(url, json=data)
        print("\nTesting Email Capture:")
        print(f"Request Data: {json.dumps(data, indent=2)}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print(f"Status Code: {response.status_code}")
        return response.json()
    except Exception as e:
        print(f"❌ Error testing email capture: {str(e)}")
        return None

def test_name_capture(base_url, text, is_registered):
    try:
        # Cambiando a la URL específica para nombre
        url = 'http://localhost:8080/api/ai/name/capture'
        print(f"Intentando conectar a: {url}")
        data = {
            "text": text,
            "is_registered": is_registered
        }
        response = requests.post(url, json=data)
        print("\nTesting Name Capture:")
        print(f"Request Data: {json.dumps(data, indent=2)}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print(f"Status Code: {response.status_code}")
        return response.json()
    except Exception as e:
        print(f"❌ Error testing name capture: {str(e)}")
        return None

def test_expert_connection(base_url, text, name, detected_language, previous_step):
    try:
        url = 'http://localhost:8080/api/ai/expert-connection/ask'
        print(f"Intentando conectar a: {url}")
        data = {
            "text": text,
            "name": name,
            "detected_language": detected_language,
            "previous_step": previous_step
        }
        response = requests.post(url, json=data)
        print("\nTesting Expert Connection:")
        print(f"Request Data: {json.dumps(data, indent=2)}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print(f"Status Code: {response.status_code}")
        return response.json()
    except Exception as e:
        print(f"❌ Error testing expert connection: {str(e)}")
        return None

def run_test_flow():
    base_url = 'http://localhost:8080'  # Esta URL base ya no se usa directamente
    
    # Test casos para diferentes idiomas
    test_cases = [
        {
            "email": "test1@test.com",
            "text": "Hello",
            "name": "John",
            "language": "en"
        },
        {
            "email": "prueba1@test.com",
            "text": "Hola",
            "name": "Juan",
            "language": "es"
        },
        {
            "email": "essai1@test.com",
            "text": "Bonjour",
            "name": "Jean",
            "language": "fr"
        }
    ]

    for case in test_cases:
        print(f"\n=== Testing flow for {case['language']} ===")
        
        # 1. Email Capture
        email_response = test_email_capture(base_url, case['email'], case['text'])
        if not email_response:
            continue

        is_registered = email_response.get('is_registered', False)
        detected_language = email_response.get('detected_language', 'en')

        # 2. Name Capture
        name_response = test_name_capture(base_url, case['name'], is_registered)
        if not name_response:
            continue

        # 3. Expert Connection (solo si está registrado)
        if is_registered:
            expert_response = test_expert_connection(
                base_url,
                "yes",
                case['name'],
                detected_language,
                "ask_expert_connection"
            )

def run_individual_test():
    base_url = 'http://localhost:8080'  # Esta URL base ya no se usa directamente
    
    print("\nSeleccione el endpoint a probar:")
    print("1. Email Capture")
    print("2. Name Capture")
    print("3. Expert Connection")
    
    option = input("\nIngrese el número del test: ")
    
    if option == "1":
        email = input("Ingrese email: ")
        text = input("Ingrese texto: ")
        test_email_capture(base_url, email, text)
    
    elif option == "2":
        name = input("Ingrese nombre: ")
        is_registered = input("¿Está registrado? (true/false): ").lower() == "true"
        test_name_capture(base_url, name, is_registered)
    
    elif option == "3":
        text = input("Ingrese respuesta (yes/no): ")
        name = input("Ingrese nombre: ")
        language = input("Ingrese idioma (en/es/fr): ")
        test_expert_connection(base_url, text, name, language, "ask_expert_connection")
    
    else:
        print("Opción no válida")

if __name__ == "__main__":
    print("=== Iniciando pruebas API ===")
    
    print("\nDesea ejecutar:")
    print("1. Flujo completo de pruebas")
    print("2. Prueba individual")
    
    choice = input("\nSeleccione una opción (1/2): ")
    
    if choice == "1":
        run_test_flow()
    elif choice == "2":
        run_individual_test()
    else:
        print("Opción no válida")

    print("\n=== Pruebas finalizadas ===")