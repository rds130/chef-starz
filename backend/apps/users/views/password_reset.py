import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import AllowAny
from ..models import CustomUserModel
from ..twilio_service import send_otp, check_otp

class RequestPasswordResetOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get('email_or_phone')
        if not identifier:
            return Response({"error": "Email or phone number is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = CustomUserModel.objects.filter(email=identifier).first()
        is_phone = False
        if not user:
            user = CustomUserModel.objects.filter(phone_number=identifier).first()
            is_phone = True

        if not user:
            return Response({"error": "Account not found."}, status=status.HTTP_404_NOT_FOUND)

        if is_phone:
            try:
                send_otp(user.phone_number)
            except Exception as e:
                return Response({"error": f"Failed to send SMS: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({"message": "OTP sent to phone.", "channel": "phone"}, status=status.HTTP_200_OK)
        else:
            otp = str(random.randint(100000, 999999))
            user.verification_code = otp
            user.save()
            try:
                send_mail(
                    subject="Password Reset Request",
                    message=f"Your password reset code is: {otp}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"\n[DEV] Email sending failed: {e}")
                print(f"[DEV] Your OTP for {user.email} is: {otp}\n")
            
            return Response({"message": "OTP sent to email.", "channel": "email"}, status=status.HTTP_200_OK)


class ConfirmPasswordResetOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get('email_or_phone')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')

        if not all([identifier, otp, new_password]):
            return Response({"error": "Missing fields. Required: email_or_phone, otp, new_password."}, status=status.HTTP_400_BAD_REQUEST)

        user = CustomUserModel.objects.filter(email=identifier).first()
        is_phone = False
        if not user:
            user = CustomUserModel.objects.filter(phone_number=identifier).first()
            is_phone = True

        if not user:
            return Response({"error": "Account not found."}, status=status.HTTP_404_NOT_FOUND)

        if is_phone:
            try:
                is_valid = check_otp(user.phone_number, otp)
                if not is_valid:
                    return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({"error": f"Failed to verify OTP: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            if user.verification_code != otp:
                return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.verification_code = ""  # Clear code
        user.save()

        return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
