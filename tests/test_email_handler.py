import pytest
from src.handlers.phase1_handlers.email_handler import is_email_registered

def test_is_email_registered_with_valid_email():
    assert is_email_registered("test1@test.com") is True

def test_is_email_registered_with_invalid_email():
    assert is_email_registered("nonexistent@test.com") is False

def test_is_email_registered_case_insensitive():
    assert is_email_registered("TEST1@TEST.COM") is True