# Expert Consultation Bot - Testing Guide

This guide provides instructions for setting up and running automated tests for the Expert Consultation Bot. The test suite includes coverage for email handling, geography processing, sector management, and ChatGPT integration.

## Project Structure
expert-consultation-bot/
├── src/
│ ├── handlers/
│ │ ├── email_handler.py
│ │ ├── geography_handler.py
│ │ └── sector_handler.py
│ └── utils/
│ ├── chatgpt_helper.py
│ └── constants.py
└── tests/
├── test_email_handler.py
├── test_geography_handler.py
└── test_chatgpt_helper.py



## Prerequisites

- Python 3.9 or higher
- pip (Python package installer)

## Setup

Clone the repository:
git clone [repository-url]
cd expert-consultation-bot



Create and activate a virtual environment:

**Windows:**
python -m venv venv
venv\Scripts\activate



**Linux/Mac:**
python3 -m venv venv
source venv/bin/activate



Install dependencies:
pip install -r requirements.txt



## Running Tests

### Running All Tests
python -m unittest discover -s tests -v



### Running Specific Test Files

**Email handler tests:**
python -m unittest tests/test_email_handler.py -v



**Geography handler tests:**
python -m unittest tests/test_geography_handler.py -v



**ChatGPT helper tests:**
python -m unittest tests/test_chatgpt_helper.py -v



### Running with Coverage Report

Install coverage tool:
pip install pytest-cov



Run tests with coverage:
pytest --cov=src tests/ --cov-report=term-missing


Collapse

## Test Categories

### Email Handler Tests

- Valid client email handling
- New client email handling
- Email domain extraction
- Response formatting

### Geography Handler Tests

- Geography capture processing
- Missing geography handling
- Missing sector handling
- Error handling
- ChatGPT integration

### ChatGPT Helper Tests

- API connection
- Company suggestions generation
- Response formatting
- Error handling
- Empty response handling

## Common Issues and Solutions

### Import Errors

Ensure your PYTHONPATH includes the src directory:
export PYTHONPATH="${PYTHONPATH}:./src"



### API Key Issues

Verify ChatGPT API key is properly set in `src/utils/chatgpt_helper.py`:
self.api_key = "your-api-key"



### Missing Dependencies

Reinstall all dependencies:
pip install -r requirements.txt


Collapse

## Contributing

- Create a new branch for your tests
- Write tests following existing patterns
- Ensure all tests pass locally
- Submit a pull request

## Best Practices

- Keep tests atomic and independent
- Use meaningful test names
- Follow the AAA pattern (Arrange, Act, Assert)
- Mock external dependencies
- Maintain test coverage above 80%

## Continuous Integration

Tests are automatically run on:

- Pull request creation
- Push to main branch
- Daily scheduled runs

## Additional Tools

- **pytest**: Alternative test runner with more features
pip install pytest
pytest tests/ -v



- **pytest-watch**: Continuous test running during development
pip install pytest-watch
ptw tests/