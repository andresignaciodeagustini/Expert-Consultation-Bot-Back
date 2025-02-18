import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(current_dir), 'src')
sys.path.append(src_dir)

from src.handlers.geography_handler import handle_geography_capture

class TestGeographyCapture(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        self.valid_request = {
            'queryResult': {
                'parameters': {
                    'geography': 'United States'
                },
                'outputContexts': [
                    {
                        'name': 'projects/bot-test/agent/sessions/123/contexts/awaiting_geography',
                        'parameters': {
                            'sector': 'technology'
                        }
                    }
                ]
            },
            'session': 'projects/bot-test/agent/sessions/123'
        }

    def tearDown(self):
        self.app_context.pop()

    @patch('src.handlers.geography_handler.ChatGPTHelper')
    def test_handle_geography_capture_success(self, mock_chatgpt):
        mock_chatgpt_instance = mock_chatgpt.return_value
        mock_chatgpt_instance.process_dialogflow_request.return_value = {
            'fulfillmentText': 'Thank you for providing the geography information.'
        }

        response = handle_geography_capture(self.valid_request)
        response_data = response.get_json()

        self.assertIn('fulfillmentText', response_data)
        self.assertIn('outputContexts', response_data)
        
        output_context = response_data['outputContexts'][0]
        self.assertEqual(output_context['name'], 
                        'projects/bot-test/agent/sessions/123/contexts/ready_for_suggestions')
        self.assertEqual(output_context['lifespanCount'], 5)
        self.assertEqual(output_context['parameters']['geography'], 'United States')
        self.assertEqual(output_context['parameters']['sector'], 'technology')

    @patch('src.handlers.geography_handler.ChatGPTHelper')
    def test_handle_geography_capture_missing_geography(self, mock_chatgpt):
        request_without_geography = {
            'queryResult': {
                'parameters': {},
                'outputContexts': []
            },
            'session': 'test_session'
        }

        mock_chatgpt_instance = mock_chatgpt.return_value
        mock_chatgpt_instance.process_dialogflow_request.return_value = {
            'fulfillmentText': 'Processing request'
        }

        response = handle_geography_capture(request_without_geography)
        response_data = response.get_json()

        self.assertIn('outputContexts', response_data)
        self.assertEqual(response_data['outputContexts'][0]['parameters']['geography'], None)

    @patch('src.handlers.geography_handler.ChatGPTHelper')
    def test_handle_geography_capture_missing_sector(self, mock_chatgpt):
        request_without_sector = {
            'queryResult': {
                'parameters': {
                    'geography': 'United States'
                },
                'outputContexts': []
            },
            'session': 'test_session'
        }

        mock_chatgpt_instance = mock_chatgpt.return_value
        mock_chatgpt_instance.process_dialogflow_request.return_value = {
            'fulfillmentText': 'Processing request'
        }

        response = handle_geography_capture(request_without_sector)
        response_data = response.get_json()

        self.assertIn('outputContexts', response_data)
        self.assertEqual(response_data['outputContexts'][0]['parameters']['sector'], None)

    @patch('src.handlers.geography_handler.ChatGPTHelper')
    def test_handle_geography_capture_error(self, mock_chatgpt):
        mock_chatgpt_instance = mock_chatgpt.return_value
        mock_chatgpt_instance.process_dialogflow_request.side_effect = Exception("Test error")

        response = handle_geography_capture(self.valid_request)
        response_data = response.get_json()

        self.assertIn('fullfilmentText', response_data)
        self.assertIn('Test error', response_data['fullfilmentText'])

    @patch('src.handlers.geography_handler.ChatGPTHelper')
    def test_chatgpt_integration(self, mock_chatgpt):
        mock_chatgpt_instance = mock_chatgpt.return_value
        mock_chatgpt_instance.process_dialogflow_request.return_value = {
            'fulfillmentText': 'Custom ChatGPT response'
        }

        response = handle_geography_capture(self.valid_request)
        response_data = response.get_json()

        self.assertEqual(response_data['fulfillmentText'], 'Custom ChatGPT response')
        mock_chatgpt_instance.process_dialogflow_request.assert_called_once_with(self.valid_request)

if __name__ == '__main__':
    unittest.main()