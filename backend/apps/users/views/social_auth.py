from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from allauth.socialaccount.providers.apple.client import AppleOAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

class GoogleLoginView(SocialLoginView):
    """
    Secure Google login using dj-rest-auth.
    Expects 'access_token' or 'id_token' in the request body.
    """
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

class AppleLoginView(SocialLoginView):
    """
    Secure Apple login using dj-rest-auth.
    Expects 'id_token' in the request body.
    """
    adapter_class = AppleOAuth2Adapter
    client_class = AppleOAuth2Client
