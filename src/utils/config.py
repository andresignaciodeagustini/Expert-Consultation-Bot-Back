import os
from dotenv import load_dotenv

os.environ.clear()
print("Loading environment variables...")
load_dotenv(override=True)  

class Config:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ZOHO_CLIENT_ID = os.getenv('ZOHO_CLIENT_ID')
    ZOHO_CLIENT_SECRET = os.getenv('ZOHO_CLIENT_SECRET')
    ZOHO_REFRESH_TOKEN = os.getenv('ZOHO_REFRESH_TOKEN')
    ZOHO_BASE_URL = os.getenv('ZOHO_BASE_URL')
    ZOHO_DC_CODE = os.getenv('ZOHO_DC_CODE')  # Agregada nueva variable
   
    print(f"Current working directory: {os.getcwd()}")
    print(f"Environment variable exists: {'OPENAI_API_KEY' in os.environ}")
    print(f"API key loaded (first 10 chars): {OPENAI_API_KEY[:10] if OPENAI_API_KEY else 'None'}")
    print(f"Full .env content:")
    with open('.env', 'r') as f:
        print(f.read())
    
    @staticmethod
    def validate():
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        elif not Config.OPENAI_API_KEY.startswith('sk-'):
            raise ValueError("OPENAI_API_KEY format appears to be invalid")
        
      
        if not all([
            Config.ZOHO_CLIENT_ID,
            Config.ZOHO_CLIENT_SECRET,
            Config.ZOHO_REFRESH_TOKEN,
            Config.ZOHO_BASE_URL,
            Config.ZOHO_DC_CODE
        ]):
            raise ValueError("Missing required Zoho credentials")