import unittest
from unittest.mock import patch
from flask import Flask
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(current_dir), 'src')
sys.path.append(src_dir)

from src.handlers.email_handler import handle_email_capture
from src.utils.constants import CLIENT_DOMAINS, VERIFIED_CLIENT_RESPONSES, NEW_CLIENT_RESPONSES

class TestEmailCapture(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        self.valid_request = {
            'queryResult': {
                'parameters': {
                    'email': 'test@clientdomain.com'
                }
            },
            'session': 'test_session'
        }
        
        self.invalid_request = {
            'queryResult': {
                'parameters': {
                    'email': 'test@unknown.com'
                }
            },
            'session': 'test_session'
        }

    def tearDown(self):
        self.app_context.pop()

    def test_handle_email_capture_valid_client(self):
        with patch('src.handlers.email_handler.CLIENT_DOMAINS', ['clientdomain.com']):
            response = handle_email_capture(self.valid_request)
            response_data = response.get_json()
            
            self.assertIn('fulfillmentText', response_data)
            self.assertIn('outputContexts', response_data)
            self.assertEqual(
                response_data['outputContexts'][0]['name'],
                'test_session/contexts/awaiting_sector'
            )
            self.assertEqual(
                response_data['outputContexts'][0]['lifespanCount'],
                5
            )
            self.assertEqual(
                response_data['outputContexts'][0]['parameters']['email'],
                'test@clientdomain.com'
            )

    def test_handle_email_capture_new_client(self):
        with patch('src.handlers.email_handler.CLIENT_DOMAINS', ['clientdomain.com']):
            response = handle_email_capture(self.invalid_request)
            response_data = response.get_json()
            
            self.assertIn('fulfilmentText', response_data)
            self.assertIn(response_data['fulfilmentText'], NEW_CLIENT_RESPONSES)

    def test_email_domain_extraction(self):
        test_email = "test@example.com"
        domain = test_email.split('@')[1]
        self.assertEqual(domain, "example.com")

    def test_verified_client_responses_not_empty(self):
        self.assertTrue(len(VERIFIED_CLIENT_RESPONSES) > 0)

    def test_new_client_responses_not_empty(self):
        self.assertTrue(len(NEW_CLIENT_RESPONSES) > 0)

    @patch('random.choice')
    def test_random_response_selection(self, mock_choice):
        mock_choice.return_value = NEW_CLIENT_RESPONSES[0]
        with patch('src.handlers.email_handler.CLIENT_DOMAINS', ['clientdomain.com']):
            response = handle_email_capture(self.invalid_request)
            response_data = response.get_json()
            self.assertEqual(
                response_data['fulfilmentText'],
                NEW_CLIENT_RESPONSES[0]
            )

if __name__ == '__main__':
    unittest.main()