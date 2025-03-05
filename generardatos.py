import pandas as pd
import random
from datetime import datetime

# Listas expandidas de nombres y apellidos internacionales
nombres = [
    # Europeos
    'Alexander', 'Sophie', 'Lucas', 'Isabella', 'Maximilian', 'Elena', 'Felix', 'Victoria', 
    'Henrik', 'Camille', 'Leonardo', 'Beatrice', 'Sebastian', 'Sophia', 'Nicolas', 'Clara',
    
    # Asiáticos
    'Hiroshi', 'Yuki', 'Wei', 'Ming', 'Jin', 'Seo-yeon', 'Kai', 'Ling', 
    'Takeshi', 'Sakura', 'Hyun', 'Mei', 'Ryu', 'Jia', 'Kazuo', 'Yuna',
    
    # Anglosajones
    'Oliver', 'Charlotte', 'William', 'Amelia', 'Theodore', 'Harper', 'Benjamin', 'Evelyn',
    'Adrian', 'Penelope', 'Julian', 'Scarlett', 'Xavier', 'Aurora', 'Nathan', 'Chloe',
    
    # Mediterráneos/Latinos
    'Alessandro', 'Valentina', 'Marco', 'Lucia', 'Rafael', 'Sofia', 'Gabriel', 'Adriana',
    'Matteo', 'Chiara', 'Diego', 'Carmen', 'Paulo', 'Isabel', 'Antonio', 'Daniela'
]

apellidos = [
    # Europeos
    'Mueller', 'Schmidt', 'Dubois', 'Laurent', 'Fischer', 'Weber', 'Wagner', 'Bauer',
    'Hoffmann', 'Bergström', 'Kowalski', 'Virtanen', 'Larsson', 'Nielsen', 'Peeters', 'Jansen',
    
    # Asiáticos
    'Tanaka', 'Yamamoto', 'Zhang', 'Wang', 'Liu', 'Kim', 'Park', 'Lee',
    'Nakamura', 'Sato', 'Suzuki', 'Watanabe', 'Chen', 'Yang', 'Wu', 'Huang',
    
    # Anglosajones
    'Harrison', 'Mitchell', 'Reynolds', 'Crawford', 'Morrison', 'Henderson', 'Campbell', 'Robertson',
    'Phillips', 'Richards', 'Watson', 'Brooks', 'Bennett', 'Wood', 'Russell', 'Hughes',
    
    # Mediterráneos/Latinos
    'Rossi', 'Ferrari', 'Romano', 'Esposito', 'Santos', 'Silva', 'Ferreira', 'Rodriguez',
    'Moretti', 'Conti', 'Marino', 'Costa', 'Almeida', 'Carvalho', 'Ricci', 'Fontana'
]

# Empresas categorizadas
empresas = {
    'financial_services': {
        'name': 'Financial Services',
        'companies': ['Goldman Sachs', 'JP Morgan', 'Morgan Stanley', 'Deutsche Bank', 'HSBC', 'Barclays', 'UBS', 'Credit Suisse']
    },
    'client_side': {
        'name': 'Client Companies',
        'companies': ['Volkswagen AG', 'Siemens AG', 'BMW Group', 'Nestlé SA', 'Unilever', 'L\'Oréal', 'SAP SE', 'Airbus']
    },
    'supply_chain': {
        'name': 'Supply Chain',
        'companies': ['Bloomberg', 'Refinitiv', 'FIS Global', 'Broadridge', 'Finastra', 'Temenos', 'FNZ Group', 'SS&C Technologies']
    }
}

# Títulos categorizados
titulos = {
    'financial_services': [
        'Senior Investment Analyst',
        'Vice President',
        'Executive Director',
        'Managing Director',
        'Portfolio Manager'
    ],
    'client_side': [
        'CFO',
        'Treasury Manager',
        'Financial Controller',
        'Head of Finance',
        'Investment Relations Director'
    ],
    'supply_chain': [
        'Solutions Architect',
        'Integration Specialist',
        'Product Manager',
        'Technical Consultant',
        'Implementation Manager'
    ]
}

paises = ['United States', 'UK', 'Singapore', 'Germany', 'France', 'Spain', 'Hong Kong', 'Switzerland']
ciudades = ['New York', 'London', 'Singapore', 'Frankfurt', 'Paris', 'Madrid', 'Hong Kong', 'Zurich']

def generar_registro():
    # Seleccionar categoría
    categoria = random.choice(['financial_services', 'client_side', 'supply_chain'])
    
    # Seleccionar empresa y título basado en la categoría
    empresa = random.choice(empresas[categoria]['companies'])
    titulo = random.choice(titulos[categoria])
    
    nombre = random.choice(nombres)
    apellido = random.choice(apellidos)
    pais = random.choice(paises)
    ciudad = random.choice(ciudades)
    
    # Ajustar rangos salariales según la categoría
    if categoria == 'financial_services':
        salario_min, salario_max = 245, 310
    elif categoria == 'client_side':
        salario_min, salario_max = 200, 280
    else:  # supply_chain
        salario_min, salario_max = 180, 250
    
    # Generar email usando inicial del nombre y apellido completo
    email = f"{nombre.lower()[0]}{apellido.lower()}@{empresa.lower().replace(' ', '')}.com"
    
    return {
        'Correo electrónico': email,
        'Teléfono': f"1172094{random.randint(75000, 79999)}",
        'Sr.': nombre,
        'Apellidos': apellido,
        'Móvil': f"1172094{random.randint(75000, 79999)}",
        'Ciudad': ciudad,
        'País': pais,
        'Moneda': 'USD',
        'Experiencia en años': random.randint(5, 20),
        'Puesto laboral actual': titulo,
        'Salario pretendido': random.randint(salario_min, salario_max),
        'Conjunto de habilidades': f"{titulo} Skills",
        'Empleador actual': empresa,
        'Salario actual': random.randint(salario_min, salario_max),
        'Candidato Estado': random.choice(['Active', 'Inactive']),
        'Origen': random.choice(['Referral', 'LinkedIn', 'Direct', 'Internal']),
        'Categoría': empresas[categoria]['name']
    }

# Generar 150 registros (50 por categoría aproximadamente)
registros = [generar_registro() for _ in range(150)]

# Crear DataFrame
df = pd.DataFrame(registros)

# Agregar algunas estadísticas
print("\n=== Estadísticas de los datos generados ===")
print("\nDistribución por categoría:")
print(df['Categoría'].value_counts())
print("\nDistribución por empresa:")
print(df['Empleador actual'].value_counts())
print("\nDistribución por título:")
print(df['Puesto laboral actual'].value_counts())

# Guardar como CSV
df.to_csv('candidatos_ejemplo.csv', index=False, encoding='utf-8')

print("\nArchivo CSV generado exitosamente!")

# Mostrar algunas estadísticas adicionales
print("\n=== Estadísticas Adicionales ===")
print(f"\nNúmero total de candidatos: {len(df)}")
print(f"Candidatos activos: {len(df[df['Candidato Estado'] == 'Active'])}")
print(f"Salario promedio: {df['Salario actual'].mean():.2f} USD")
print(f"Años de experiencia promedio: {df['Experiencia en años'].mean():.2f}")

# Mostrar distribución por país
print("\nDistribución por país:")
print(df['País'].value_counts())