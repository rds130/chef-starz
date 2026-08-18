from rest_framework import serializers
from .models import CustomUserModel, UserBlockModel
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from dj_rest_auth.serializers import JWTSerializer

# Create your serializers here.
class CustomUserModelSerializer(serializers.ModelSerializer):
    follower_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUserModel
        fields = [
            'id', 'email', 'phone_number', 'username', 'age_group', 
            'profile_picture', 'bio', 'location', 
            'parent_email', 'is_email_verified', 'is_phone_verified', 'is_parent_approved', 'is_active',
            'follower_count', 'following_count', 'posts_count', 'recipes_count'
        ]
        read_only_fields = ['id', 'email', 'is_staff', 'is_superuser', 'is_active', 'is_email_verified', 'is_phone_verified', 'is_parent_approved']

    def get_follower_count(self, obj):
        return obj.followers.count()

    def get_following_count(self, obj):
        return obj.following.count()

    def get_posts_count(self, obj):
        return obj.posts.count()

    def get_recipes_count(self, obj):
        return obj.recipes.count()

class KidSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CustomUserModel
        fields = ['email', 'phone_number', 'password']

    def validate(self, attrs):
        email = attrs.get('email', '').strip()
        phone_number = attrs.get('phone_number', '').strip()
        if not email and not phone_number:
            raise serializers.ValidationError(
                "You must provide either an email or a phone number."
            )
        # Clean empty strings to None so the model doesn't store blanks
        if not email:
            attrs['email'] = None
        if not phone_number:
            attrs['phone_number'] = None
        return attrs

    def create(self, validated_data):
        # Using the manager you wrote to handle password hashing
        return CustomUserModel.objects.create_user(
            email=validated_data.get('email') or '',
            password=validated_data['password'],
            phone_number=validated_data.get('phone_number'),
        )


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUserModel
        fields = ['email', 'password', 'age_group', 'parent_email']

    def create(self, validated_data):
        # Use the manager you already wrote to hash the password properly
        return CustomUserModel.objects.create_user(**validated_data)

class OtpVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False)
    code = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs):
        if not attrs.get('email') and not attrs.get('phone_number'):
            raise serializers.ValidationError(
                "You must provide either an email or a phone number."
            )
        return attrs

class ResendOtpSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False)

    def validate(self, attrs):
        if not attrs.get('email') and not attrs.get('phone_number'):
            raise serializers.ValidationError(
                "You must provide either an email or a phone number."
            )
        return attrs




class ProfileCompletionSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)

    class Meta:
        model = CustomUserModel
        fields = ['email', 'username', 'age_group', 'parent_email']
        extra_kwargs = {
            'username': {'required': True},
            'age_group': {'required': True},
            'parent_email': {'required': True},
        }


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add custom fields to the response for Flutter
        data['username'] = self.user.username
        data['is_active'] = self.user.is_active
        data['profile_picture'] = self.user.profile_picture.url if self.user.profile_picture else None
        
        return data



from dj_rest_auth.serializers import PasswordResetSerializer

from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm

class CustomPasswordResetSerializer(PasswordResetSerializer):
    password_reset_form_class = DjangoPasswordResetForm

    def save(self):
        request = self.context.get('request')
        opts = {
            'use_https': request.is_secure() if request else True,
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL'),
            'request': request,
            'domain_override': request.get_host() if request else None,
            'email_template_name': 'registration/password_reset_email.txt',
            'html_email_template_name': 'registration/password_reset_email.html',
            'subject_template_name': 'registration/password_reset_subject.txt',
        }
        self.reset_form.save(**opts)

class UserBlockSerializer(serializers.Serializer):
    blocked_user_id = serializers.IntegerField()

    def validate_blocked_user_id(self, value):
        if not CustomUserModel.objects.filter(id=value).exists():
            raise serializers.ValidationError("User to block does not exist.")
        return value

class BlockedUserListSerializer(serializers.ModelSerializer):
    blocked_user = CustomUserModelSerializer(source='blocked')

    class Meta:
        model = UserBlockModel
        fields = ['id', 'blocked_user', 'created_at']


class SocialUserRepresentationSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = CustomUserModel
        fields = ['id', 'email', 'full_name', 'profile_image']

    def get_full_name(self, obj):
        if obj.username:
            return obj.username
        return obj.email.split('@')[0]

    def get_profile_image(self, obj):
        if obj.profile_picture:
            return obj.profile_picture.url
        return "https://prommt.cc/profile_images/default_avatar.png"


class GoogleLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()


class AppleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
