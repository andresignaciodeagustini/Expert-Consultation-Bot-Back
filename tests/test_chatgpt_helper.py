import unittest
from unittest.mock import patch, MagicMock
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from src.utils.chatgpt_helper import ChatGPTHelper

class TestChatGPTHelper(unittest.TestCase):
    @patch('src.utils.chatgpt_helper.OpenAI')
    def setUp(self, mock_openai):
        self.mock_openai = mock_openai
        self.mock_client = MagicMock()
        mock_openai.return_value = self.mock_client
        self.mock_client.chat.completions.create.return_value = MagicMock()
        self.helper = ChatGPTHelper()
        self.mock_client.chat.completions.create.reset_mock()

    def test_initialization(self):
        self.assertIsNotNone(self.helper)
        self.assertEqual(self.helper.max_retries, 3)
        self.assertEqual(self.helper.retry_delay, 1)
        self.assertIsNotNone(self.helper.api_key)

    @patch('src.utils.chatgpt_helper.OpenAI')
    def test_initialization_failure(self, mock_openai):
        mock_openai.side_effect = Exception("API Key invalid")
        
        with self.assertRaises(Exception) as context:
            ChatGPTHelper()
        
        self.assertIn("API Key invalid", str(context.exception))

    def test_test_connection(self):
        mock_response = MagicMock()
        self.mock_client.chat.completions.create.return_value = mock_response
        
        result = self.helper.test_connection()
        
        self.assertTrue(result)
        self.mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello, test connection"}]
        )

    def test_test_connection_failure(self):
        self.mock_client.chat.completions.create.side_effect = Exception("Connection failed")
        
        with self.assertRaises(Exception) as context:
            self.helper.test_connection()
        
        self.assertIn("Connection failed", str(context.exception))

    def test_get_companies_suggestions_success(self):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="Apple, Google, Microsoft, Amazon, Meta"
                )
            )
        ]
        self.mock_client.chat.completions.create.return_value = mock_response

        result = self.helper.get_companies_suggestions("technology", "United States")

        self.assertTrue(result['success'])
        self.assertIsInstance(result['content'], list)
        self.assertEqual(len(result['content']), 5)
        self.assertIn('Apple', result['content'])
        self.assertIsInstance(result['contentId'], str)
        
        self.mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional business analyst that provides accurate lists of companies based on sector and geography."
                },
                {
                    "role": "user",
                    "content": "List 15 major companies in the technology sector that operate in United States. Only provide the company names separated by commas."
                }
            ],
            temperature=0.7,
            max_tokens=150
        )

    def test_get_companies_suggestions_failure(self):
        self.mock_client.chat.completions.create.side_effect = Exception("API error")
        result = self.helper.get_companies_suggestions("technology", "United States")
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIsNone(result['contentId'])

    def test_get_companies_suggestions_parameters(self):
        test_cases = [
            ("healthcare", "Europe", 0.5),
            ("technology", "Asia", 0.8),
            ("retail", "South America", 0.3)
        ]

        for sector, geography, temp in test_cases:
            with self.subTest(sector=sector, geography=geography, temperature=temp):
                mock_response = MagicMock()
                mock_response.choices = [
                    MagicMock(
                        message=MagicMock(
                            content="Company1, Company2, Company3"
                        )
                    )
                ]
                self.mock_client.chat.completions.create.return_value = mock_response

                result = self.helper.get_companies_suggestions(
                    sector=sector,
                    geography=geography,
                    temperature=temp
                )

                call_args = self.mock_client.chat.completions.create.call_args[1]
                self.assertEqual(call_args['temperature'], temp)
                self.assertEqual(call_args['model'], "gpt-4")
                self.assertIn(sector, call_args['messages'][1]['content'])
                self.assertIn(geography, call_args['messages'][1]['content'])

    def test_response_formatting(self):
        test_cases = [
            (" Company1 , Company2 , Company3 ", ['Company1', 'Company2', 'Company3']),
            ("Company1,Company2,Company3", ['Company1', 'Company2', 'Company3']),
            (" , Company1, , Company2, , ", ['Company1', 'Company2']),
            ("   ", []),
            (",,,", []),
            ("Company1;Company2,Company3", ['Company1;Company2', 'Company3']),
            ("1. Company1, 2. Company2", ['1. Company1', '2. Company2'])
        ]

        for input_content, expected_output in test_cases:
            with self.subTest(input_content=input_content):
                mock_response = MagicMock()
                mock_response.choices = [
                    MagicMock(
                        message=MagicMock(
                            content=input_content
                        )
                    )
                ]
                self.mock_client.chat.completions.create.return_value = mock_response
                result = self.helper.get_companies_suggestions("tech", "US")
                self.assertTrue(result['success'])
                self.assertEqual(result['content'], expected_output)

    @patch('uuid.uuid4')
    def test_content_id_generation(self, mock_uuid):
        test_cases = [
            ("normal response", "Company1, Company2", "test-uuid-1"),
            ("empty response", "", "test-uuid-2"),
            ("None response", None, "test-uuid-3")
        ]

        for case_name, content, uuid_value in test_cases:
            with self.subTest(case=case_name):
                mock_uuid.return_value = uuid_value
                mock_response = MagicMock()
                mock_response.choices = [
                    MagicMock(
                        message=MagicMock(
                            content=content
                        )
                    )
                ]
                self.mock_client.chat.completions.create.return_value = mock_response
                result = self.helper.get_companies_suggestions("tech", "US")
                self.assertEqual(result['contentId'], uuid_value)

    def test_empty_response_handling(self):
        empty_responses = [
            ("empty string", ""),
            ("whitespace", "  "),
            ("commas only", ",,,"),
            ("spaces and commas", ", ,  ,"),
            ("None value", None),
            ("None message", MagicMock(message=None))
        ]
        
        for case_name, empty_response in empty_responses:
            with self.subTest(case=case_name):
                mock_response = MagicMock()
                if isinstance(empty_response, MagicMock):
                    mock_response.choices = [empty_response]
                else:
                    mock_response.choices = [
                        MagicMock(
                            message=MagicMock(
                                content=empty_response
                            )
                        )
                    ]
                self.mock_client.chat.completions.create.return_value = mock_response
                result = self.helper.get_companies_suggestions("tech", "US")
                self.assertTrue(result['success'])
                self.assertEqual(result['content'], [])
                self.assertIsInstance(result['contentId'], str)

    def test_process_dialogflow_request(self):
        test_cases = [
            ("normal response", "Test response", "Test response"),
            ("empty response", "", ""),
            ("None response", None, "Sorry, I could not process the request.")
        ]

        for case_name, content, expected_response in test_cases:
            with self.subTest(case=case_name):
                mock_response = MagicMock()
                mock_response.choices = [
                    MagicMock(
                        message=MagicMock(
                            content=content
                        )
                    )
                ]
                self.mock_client.chat.completions.create.return_value = mock_response
                test_request = {"test": "data"}
                result = self.helper.process_dialogflow_request(test_request)
                self.assertIn('fulfillmentText', result)
                self.assertEqual(result['fulfillmentText'], expected_response)

    def test_process_dialogflow_request_failure(self):
        error_cases = [
            Exception("API error"),
            ValueError("Invalid input"),
            ConnectionError("Network error")
        ]

        for error in error_cases:
            with self.subTest(error_type=type(error).__name__):
                self.mock_client.chat.completions.create.side_effect = error
                test_request = {"test": "data"}
                result = self.helper.process_dialogflow_request(test_request)
                self.assertIn('fulfillmentText', result)
                self.assertIn('error', result['fulfillmentText'].lower())

if __name__ == '__main__':
    unittest.main()