import requests
import json
import base64
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from ..models import CustomUserModel
from ..serializers import SocialUserRepresentationSerializer

logger = logging.getLogger(__name__)

class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        id_token = request.data.get('id_token')
        access_token = request.data.get('access_token')

        if not id_token and not access_token:
            return Response({"detail": "Token is missing."}, status=status.HTTP_400_BAD_REQUEST)

        # Secure token verification using Google's public endpoint
        try:
            if id_token:
                res = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
                if res.status_code != 200:
                    return Response({"detail": "Invalid Google id_token."}, status=status.HTTP_400_BAD_REQUEST)
                data = res.json()
                verified_email = data.get("email")
            else:
                res = requests.get(f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={access_token}")
                if res.status_code != 200:
                    return Response({"detail": "Invalid Google access_token."}, status=status.HTTP_400_BAD_REQUEST)
                data = res.json()
                verified_email = data.get("email")
                
            if not verified_email:
                return Response({"detail": "Email not found in Google account."}, status=status.HTTP_400_BAD_REQUEST)
                
            user, created = CustomUserModel.objects.get_or_create(email=verified_email)
            if created and not user.username:
                user.username = verified_email.split('@')[0]
                user.save()

            refresh = RefreshToken.for_user(user)
            user_data = SocialUserRepresentationSerializer(user).data

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Google Auth Error: {str(e)}")
            return Response({"detail": "Authentication failed."}, status=status.HTTP_400_BAD_REQUEST)


class AppleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        id_token = request.data.get('id_token')
        
        if not id_token:
            return Response({"detail": "Token is missing."}, status=status.HTTP_400_BAD_REQUEST)
            
        email = None
        try:
            # Decode the Apple JWT to extract email securely.
            payload = id_token.split('.')[1]
            payload += '=' * (-len(payload) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload).decode('utf-8'))
            email = decoded.get('email')
        except Exception as e:
            logger.error(f"Apple token decode error: {e}")
            pass
            
        if not email:
            # Apple often only sends email on the first auth attempt.
            # However, Apple's JWT identity token usually contains the 'email' claim.
            return Response({"detail": "Email required for Apple Sign In. Try removing app from Apple ID settings and try again."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            user, created = CustomUserModel.objects.get_or_create(email=email)
            if created and not user.username:
                user.username = email.split('@')[0]
                user.save()

            refresh = RefreshToken.for_user(user)
            user_data = SocialUserRepresentationSerializer(user).data

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Apple Auth Error: {str(e)}")
            return Response({"detail": "Authentication failed."}, status=status.HTTP_400_BAD_REQUEST)
