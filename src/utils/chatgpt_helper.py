from openai import OpenAI
import logging
import uuid
from typing import Dict
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  

class ChatGPTHelper:
    def __init__(self): 
        load_dotenv()  
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.max_retries = 3
        self.retry_delay = 1

        if not self.api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        try:
            self.client = OpenAI(api_key=self.api_key)
            self.test_connection()
            logger.info("ChatGPT Helper initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize service: {str(e)}")
            raise
    def test_connection(self):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": "Hello, test connection"}
                ]
            )
            logger.info("Connection test successful")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            raise

    def identify_region(self, location: str) -> Dict:
        
        try:
            logger.info(f"Identifying region for location: {location}")
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a geography expert. You must categorize locations into one of these regions: North America, Europe, or Asia. Only respond with one of these three options."
                },
                {
                    "role": "user",
                    "content": f"Which region (North America, Europe, or Asia) does {location} belong to? Only respond with the region name."
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.3
            )

            region = response.choices[0].message.content.strip()
            
            if region not in ["North America", "Europe", "Asia"]:
                logger.warning(f"Invalid region response: {region}")
                return {
                    "success": False,
                    "error": f"Invalid region: {region}"
                }

            logger.info(f"Location '{location}' identified as {region}")
            return {
                "success": True,
                "region": region,
                "original_location": location
            }

        except Exception as e:
            logger.error(f"Error identifying region: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_companies_suggestions(
        self, 
        sector: str, 
        geography: str, 
        temperature: float = 0.7
    ) -> Dict:
        try:
            logger.info(f"Generating companies for sector: {sector}, geography: {geography}")
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a professional business analyst that provides accurate lists of companies based on sector and geography."
                },
                {
                    "role": "user",
                    "content": f"List exactly 20 major companies in the {sector} sector that operate in {geography}. Only provide the company names separated by commas."
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=temperature,
                max_tokens=250
            )

            content = response.choices[0].message.content
            if content is None:
                logger.info("Received None response from API")
                return {
                    "success": True,
                    "content": [],
                    "contentId": str(uuid.uuid4())
                }

            companies_text = content.strip()
            if not companies_text:
                logger.info("Received empty response from API")
                return {
                    "success": True,
                    "content": [],
                    "contentId": str(uuid.uuid4())
                }

            companies = [
                company.strip() 
                for company in companies_text.split(',') 
                if company.strip() and not company.strip().isspace()
            ]

            if len(companies) < 20:
                logger.warning(f"Received only {len(companies)} companies, requesting more")
                return self.get_companies_suggestions(sector, geography, temperature)
            
            logger.info(f"Successfully generated {len(companies)} companies")
            
            return {
                "success": True,
                "content": companies[:20],
                "contentId": str(uuid.uuid4())
            }

        except Exception as e:
            logger.error(f"Error generating companies: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "contentId": None
            }

    def process_dialogflow_request(self, request_json: Dict) -> Dict:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": str(request_json)}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            if content is None:
                return {
                    "fulfillmentText": "Sorry, I could not process the request."
                }
            
            return {
                "fulfillmentText": content.strip()
            }
            
        except Exception as e:
            logger.error(f"Error processing Dialogflow request: {str(e)}")
            return {
                "fulfillmentText": "Sorry, there was an error processing your request."
            }