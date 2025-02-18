
import unittest
from unittest.mock import patch
from flask import Flask
import os
import sys


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from src.handlers.sector_handler import handle_sector_capture

class TestSectorCapture(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        
        self.valid_request = {
            'queryResult': {
                'parameters': {
                    'sector': 'Technology'
                }
            },
            'session': 'projects/bot-test/agent/sessions/123'
        }

    def tearDown(self):
        self.app_context.pop()

    def test_handle_sector_capture_success(self):
        
        response = handle_sector_capture(self.valid_request)
        response_data = response.get_json()
        
        self.assertIn('fulfillmentText', response_data)
        self.assertIn('outputContexts', response_data)
        self.assertIn('technology', response_data['fulfillmentText'].lower())
        self.assertIn('geographical region', response_data['fulfillmentText'].lower())
        
        output_context = response_data['outputContexts'][0]
        self.assertEqual(
            output_context['name'],
            'projects/bot-test/agent/sessions/123/contexts/awaiting_geography'
        )
        self.assertEqual(output_context['lifespanCount'], 5)
        self.assertEqual(output_context['parameters']['sector'], 'technology')

    def test_handle_sector_capture_empty_sector(self):
        
        request_without_sector = {
            'queryResult': {
                'parameters': {}
            },
            'session': 'test_session'
        }

        response = handle_sector_capture(request_without_sector)
        response_data = response.get_json()
        
        self.assertIn('fulfillmentText', response_data)
        self.assertIn("didn't catch the sector", response_data['fulfillmentText'])
        self.assertNotIn('outputContexts', response_data)

    def test_handle_sector_capture_null_sector(self):
        
        request_with_null_sector = {
            'queryResult': {
                'parameters': {
                    'sector': None
                }
            },
            'session': 'test_session'
        }

        response = handle_sector_capture(request_with_null_sector)
        response_data = response.get_json()
        
        self.assertIn('fulfillmentText', response_data)
        self.assertIn("didn't catch the sector", response_data['fulfillmentText'])
        self.assertNotIn('outputContexts', response_data)

    def test_handle_sector_capture_case_insensitive(self):
        
        test_cases = ['TECHNOLOGY', 'Technology', 'technology']
        
        for sector in test_cases:
            with self.subTest(sector=sector):
                request = {
                    'queryResult': {
                        'parameters': {
                            'sector': sector
                        }
                    },
                    'session': 'test_session'
                }
                
                response = handle_sector_capture(request)
                response_data = response.get_json()
                
                self.assertEqual(
                    response_data['outputContexts'][0]['parameters']['sector'],
                    'technology'
                )

    def test_handle_sector_capture_whitespace(self):
        
        request_with_whitespace = {
            'queryResult': {
                'parameters': {
                    'sector': '  Technology  '
                }
            },
            'session': 'test_session'
        }

        response = handle_sector_capture(request_with_whitespace)
        response_data = response.get_json()
        
        self.assertIn('outputContexts', response_data)
        self.assertEqual(
            response_data['outputContexts'][0]['parameters']['sector'],
            'technology'
        )

if __name__ == '__main__':
    unittest.main()