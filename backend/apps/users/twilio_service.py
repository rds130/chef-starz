"""
Twilio Verify helper — sends and checks OTPs via SMS.
Used for kid phone number verification during signup.
Email OTP flows bypass this module entirely.

Uses API Key authentication (SK... + secret + AC account SID).
"""
from twilio.rest import Client
from django.conf import settings


def get_twilio_client():
    """
    Return a configured Twilio REST client using API Key auth.
    Requires: TWILIO_API_KEY_SID (SK...), TWILIO_API_KEY_SECRET, TWILIO_ACCOUNT_SID (AC...).
    """
    return Client(
        settings.TWILIO_API_KEY_SID,
        settings.TWILIO_API_KEY_SECRET,
        settings.TWILIO_ACCOUNT_SID,
    )


def send_otp(phone_number: str) -> str:
    """
    Send a verification OTP to the given phone number via SMS.
    Phone number must be in E.164 format (e.g. +8801712345678).
    Returns the verification status ('pending' on success).
    """
    client = get_twilio_client()
    verification = (
        client.verify.v2
        .services(settings.TWILIO_VERIFY_SERVICE_SID)
        .verifications.create(to=phone_number, channel='sms')
    )
    return verification.status  # 'pending'


def check_otp(phone_number: str, code: str) -> str:
    """
    Verify the OTP code for the given phone number.
    Returns 'approved' on success, 'pending' if the code is wrong.
    """
    client = get_twilio_client()
    verification_check = (
        client.verify.v2
        .services(settings.TWILIO_VERIFY_SERVICE_SID)
        .verification_checks.create(to=phone_number, code=code)
    )
    return verification_check.status  # 'approved' or 'pending'
