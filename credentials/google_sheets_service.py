import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime

# Ruta al archivo de credenciales desde la raíz del proyecto
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                               'credentials', 'credentials.json')

# ID de tu hoja de Google Sheets
SHEET_ID = '1NS_uTN64VChgFWyRQusGk5W1Vc_JKczFuJFJZvNwSwA'

def send_to_sheets(data):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
        client = gspread.authorize(credentials)
        
        # Abrir la hoja usando el ID
        sheet = client.open_by_key(SHEET_ID).sheet1
        
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
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            expert['name'],
            expert['role'],
            expert['experience'],
            ', '.join(expert['expertise']),
            ', '.join(expert['companies_experience']),
            ', '.join(expert['region_experience']),
            data.get('detected_language', ''),
            evaluation_questions.get('clientes', '').replace('\n', ' | '),
            evaluation_questions.get('empresas', '').replace('\n', ' | '),
            evaluation_questions.get('proveedores', '').replace('\n', ' | '),
            str(data.get('success', False)),
            data.get('final_message', '')
        ]
        
        sheet.append_row(row)
        return True, "Data successfully sent to Google Sheets"
        
    except Exception as e:
        return False, f"Error sending data to Google Sheets: {str(e)}"