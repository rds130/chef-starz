import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from ..serializers import *
from ..models import CustomUserModel
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from ..twilio_service import send_otp, check_otp

class Stage1SignupView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(request_body=KidSignupSerializer)
    def post(self, request):
        serializer = KidSignupSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            phone_number = user.phone_number
            email = user.email

            # --- Phone path: use Twilio Verify ---
            if phone_number:
                try:
                    send_otp(phone_number)
                except Exception as e:
                    user.delete()
                    return Response(
                        {"error": f"Failed to send SMS: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
                return Response({
                    "message": "Step 1 complete. OTP sent to kid's phone.",
                    "phone_number": phone_number,
                    "verification_channel": "phone",
                }, status=status.HTTP_201_CREATED)

            # --- Email path: generate code and send via email ---
            otp = str(random.randint(100000, 999999))
            user.verification_code = otp
            user.save()

            try:
                send_mail(
                    subject="Verify your Email",
                    message=f"Your verification code is: {otp}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception as e:
                # If email fails (e.g., missing credentials in .env), log the OTP for testing
                print(f"\n[DEV] Email sending failed: {e}")
                print(f"[DEV] Your OTP for {email} is: {otp}\n")
                # Do not delete the user, let them continue so they can test locally.

            return Response({
                "message": "Step 1 complete. OTP sent to kid's email.",
                "email": email,
                "verification_channel": "email",
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class VerifyKidOTPView(APIView):
    """Verify kid's OTP — supports both email and phone verification."""
    permission_classes = [AllowAny]
    @swagger_auto_schema(request_body=OtpVerificationSerializer)
    def post(self, request):
        serializer = OtpVerificationSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            phone_number = serializer.validated_data.get('phone_number')
            code = serializer.validated_data['code']

            # Look up user by phone or email
            try:
                if phone_number:
                    user = CustomUserModel.objects.get(phone_number=phone_number)
                else:
                    user = CustomUserModel.objects.get(email=email)
            except CustomUserModel.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            # --- Phone path: verify via Twilio ---
            if phone_number:
                try:
                    result = check_otp(phone_number, code)
                except Exception:
                    return Response(
                        {"error": "Failed to verify OTP. Please try again."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                if result == 'approved':
                    user.is_phone_verified = True
                    user.save()

                    refresh = RefreshToken.for_user(user)
                    return Response({
                        "message": "Phone verified!",
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                    }, status=status.HTTP_200_OK)
                
                return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)

            # --- Email path: check verification_code locally ---
            if user.verification_code == code:
                user.is_email_verified = True
                user.verification_code = None 
                user.save()

                refresh = RefreshToken.for_user(user)
                return Response({
                    "message": "Email verified!",
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                }, status=status.HTTP_200_OK)
            
            return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.permissions import IsAuthenticated

class CompleteProfileView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(request_body=ProfileCompletionSerializer)
    def post(self, request):
        user = request.user
        
        # Ensure they verified via EITHER email or phone first!
        if not user.is_email_verified and not user.is_phone_verified:
            return Response({"error": "Verify your email or phone first"}, status=status.HTTP_403_FORBIDDEN)

        # Update the user instance with the rest of the data
        serializer = ProfileCompletionSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            
            # 1. Generate code for the PARENT
            parent_otp = str(random.randint(100000, 999999))
            user.verification_code = parent_otp
            user.save()
            
            # 2. Send email to the PARENT
            try:
                send_mail(
                    subject="Action Required: Parental Consent",
                    message=f"Your child is signing up. Provide them this code to approve: {parent_otp}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.parent_email],
                    fail_silently=False,
                )
            except Exception:
                return Response(
                    {"error": "Failed to send email to parent. Please check email configuration."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response({"message": "Profile updated. Code sent to parent."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class VerifyParentApprovalView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(request_body=OtpVerificationSerializer)
    def post(self, request):
        serializer = OtpVerificationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            code = serializer.validated_data['code']
            
            try:
                user = CustomUserModel.objects.get(email=email)
            except CustomUserModel.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if user.verification_code == code:
            user.is_parent_approved = True
            user.verification_code = None
            user.save()
            return Response({"message": "Account activated!"})
        
        return Response({"error": "Invalid parent code"}, status=status.HTTP_400_BAD_REQUEST)
# Resend OTP View
class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(request_body=ResendOtpSerializer)
    def post(self, request):
        serializer = ResendOtpSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            phone_number = serializer.validated_data.get('phone_number')

            # Look up user by phone or email
            try:
                if phone_number:
                    user = CustomUserModel.objects.get(phone_number=phone_number)
                else:
                    user = CustomUserModel.objects.get(email=email)
            except CustomUserModel.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            if (user.is_email_verified or user.is_phone_verified) and user.is_parent_approved:
                return Response({"message": "Account already fully verified"}, status=status.HTTP_400_BAD_REQUEST)

            # --- Kid not yet verified: resend kid OTP ---
            if not user.is_email_verified and not user.is_phone_verified:
                # Phone path
                if phone_number and user.phone_number:
                    try:
                        send_otp(user.phone_number)
                        return Response({"message": "New OTP sent to kid's phone."}, status=status.HTTP_200_OK)
                    except Exception:
                        return Response(
                            {"error": "Failed to send SMS. Please try again."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )
                # Email path
                otp = str(random.randint(100000, 999999))
                user.verification_code = otp
                user.save()
                try:
                    send_mail(
                        subject="Verify your Email",
                        message=f"Your new verification code is: {otp}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    return Response({"message": "New OTP sent to kid's email."}, status=status.HTTP_200_OK)
                except Exception:
                    return Response(
                        {"error": "Failed to send email. Please check email configuration."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            # --- Kid verified but parent not approved: resend parent OTP ---
            if not user.parent_email:
                return Response({"error": "Parent email not set. Complete profile first."}, status=status.HTTP_400_BAD_REQUEST)

            otp = str(random.randint(100000, 999999))
            user.verification_code = otp
            user.save()
            try:
                send_mail(
                    subject="Action Required: Parental Consent (Resent)",
                    message=f"Your child is signing up. Provide them this code to approve: {otp}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.parent_email],
                    fail_silently=False,
                )
                return Response({"message": "New OTP sent to parent's email."}, status=status.HTTP_200_OK)
            except Exception:
                return Response(
                    {"error": "Failed to send email. Please check email configuration."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)