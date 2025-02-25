import requests
import json

def test_search_flow():
    base_url = 'http://localhost:8080/api'
    session = requests.Session()

    try:
        # Test 1: Sector Experience
        print("\n1. Testing Sector Experience...")
        sector_data = {
            "sector": "technologie",  # Cambiado a francés
            "language": "fr",         # Corregido de "ft" a "fr"
            "additional_info": "cloud computing"
        }
        sector_response = session.post(
            f'{base_url}/sector-experience',
            json=sector_data
        )
        print(f"Response: {sector_response.json()}")
        print(f"Status Code: {sector_response.status_code}")

        # Test 2: Simple Expert Connection
        print("\n2. Testing Simple Expert Connection...")
        expert_data = {
            "answer": "oui",          # Cambiado a francés
            "companies": ["Microsoft", "Amazon", "Google"],
            "language": "fr"
        }
        expert_response = session.post(
            f'{base_url}/simple-expert-connection',
            json=expert_data
        )
        print(f"Response: {expert_response.json()}")
        print(f"Status Code: {expert_response.status_code}")

        # Test 3: Specify Countries
        print("\n3. Testing Specify Countries...")
        countries_data = {
            "countries": ["France", "Canada"],  # Cambiado para incluir Francia
            "language": "fr"
        }
        countries_response = session.post(
            f'{base_url}/specify-countries',
            json=countries_data
        )
        print(f"Response: {countries_response.json()}")
        print(f"Status Code: {countries_response.status_code}")

        # Test 4: Company Suggestions
        print("\n4. Testing Company Suggestions...")
        suggestions_data = {
            "sector": "technologie",  # Cambiado a francés
            "location": "France, Canada",
            "experience_type": "cloud computing",
            "language": "fr"
        }
        suggestions_response = session.post(
            f'{base_url}/company-suggestions-test',
            json=suggestions_data
        )
        print(f"Response: {suggestions_response.json()}")
        print(f"Status Code: {suggestions_response.status_code}")

    except requests.exceptions.ConnectionError:
        print(f"❌ Error: No se pudo conectar al servidor en {base_url}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la solicitud: {str(e)}")
    except json.JSONDecodeError:
        print("❌ Error: La respuesta no es un JSON válido")
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")

def run_individual_test(endpoint, data):
    base_url = 'http://localhost:8080/api'
    try:
        response = requests.post(f'{base_url}/{endpoint}', json=data)
        print(f"\nTesting {endpoint}...")
        print(f"Request Data: {json.dumps(data, indent=2)}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print(f"Status Code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing {endpoint}: {str(e)}")

if __name__ == "__main__":
    print("=== Démarrage des tests API ===")  # Cambiado a francés
    
    print("\n🚀 Exécution des tests complets...")  # Cambiado a francés
    test_search_flow()
    
    print("\n🔍 Voulez-vous exécuter un test individuel? (o/n)")  # Cambiado a francés
    if input().lower() in ['o', 'oui']:  # Adaptado para francés
        print("\nSélectionnez l'endpoint à tester:")  # Cambiado a francés
        print("1. sector-experience")
        print("2. simple-expert-connection")
        print("3. specify-countries")
        print("4. company-suggestions-test")
        
        option = input("\nEntrez le numéro du test: ")  # Cambiado a francés
        
        test_cases = {
            "1": ("sector-experience", {
                "sector": "technologie",
                "language": "fr",
                "additional_info": "cloud computing"
            }),
            "2": ("simple-expert-connection", {
                "answer": "oui",
                "companies": ["Microsoft", "Amazon", "Google"],
                "language": "fr"
            }),
            "3": ("specify-countries", {
                "countries": ["France", "Canada"],
                "language": "fr"
            }),
            "4": ("company-suggestions-test", {
                "sector": "technologie",
                "location": "France, Canada",
                "experience_type": "cloud computing",
                "language": "fr"
            })
        }
        
        if option in test_cases:
            endpoint, data = test_cases[option]
            run_individual_test(endpoint, data)
        else:
            print("Option non valide")  # Cambiado a francés

    print("\n=== Tests terminés ===")  # Cambiado a francésn
    