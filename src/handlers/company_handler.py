from flask import jsonify
import random

COMPLETE_INFO_RESPONSES = [
    "I'll search for experts from {company} and similar companies in the {sector} sector in {geography}. Let me check our database.",
    "Great choice! I'll find experts with experience at {company}, focusing on the {sector} sector in {geography}",
    "Excellent selection! Let me search for {company} experts in {geography} with {sector} sector experience"
]


COMPANY_ONLY_RESPONSE = [
    "I'll search for experts from {company}. Let me check our database for professionals with the relevant experience.",
    "Great choice! I'll look for experts who have worked ay {company}",
    "I'll find professionals with experience  at {company} who might be suitable for your needs."
]