import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime

CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                               'credentials', 'credentials.json')

def send_to_sheets(data):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(credentials)
    
    # Abrir la hoja (reemplaza con el nombre de tu hoja)
    sheet = client.open('Nombre_de_tu_hoja').sheet1
    
    # Si es la primera vez, configurar los encabezados
    if sheet.row_count == 0:
        headers = [
            'Date',
            'Expert Name',
            'Role',
            'Experience',
            'Expertise Areas',
            'Companies Experience',
            'Region Experience',
            'Language',
            'Customer Questions',
            'Company Questions',
            'Supplier Questions',
            'Success Status',
            'Final Message'
        ]
        sheet.append_row(headers)

    # Preparar los datos
    expert = data['expert_details']
    evaluation_questions = data.get('evaluation_questions', {})
    
    row = [
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Fecha y hora
        expert['name'],
        expert['role'],
        expert['experience'],
        ', '.join(expert['expertise']),
        ', '.join(expert['companies_experience']),
        ', '.join(expert['region_experience']),
        data.get('detected_language', ''),
        evaluation_questions.get('clientes', '').replace('\n', ' | '),  # Customer questions
        evaluation_questions.get('empresas', '').replace('\n', ' | '),  # Company questions
        evaluation_questions.get('proveedores', '').replace('\n', ' | '),  # Supplier questions
        str(data.get('success', False)),
        data.get('final_message', '')
    ]
    
    sheet.append_row(row)