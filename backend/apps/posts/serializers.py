from rest_framework import serializers
from .models import PostModel, LikeModel, CommentModel, ShareModel, PinModel, SaveModel
from apps.users.serializers import CustomUserModelSerializer

# Create your serializers here.

class BaseInteractionSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    def get_user(self, obj):
        if obj.user.username:
            return obj.user.username
        if obj.user.full_name:
            return obj.user.full_name
        if obj.user.email:
            return obj.user.email.split('@')[0]
        return str(obj.user.phone_number or obj.user.id)
        
    def get_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.user.profile_picture:
            if request:
                return request.build_absolute_uri(obj.user.profile_picture.url)
            return obj.user.profile_picture.url
        return None

class LikeModelSerializer(BaseInteractionSerializer):
    class Meta:
        model = LikeModel
        fields = ['id', 'user', 'profile_picture', 'created_at']

class CommentModelSerializer(BaseInteractionSerializer):
    class Meta:
        model = CommentModel
        fields = ['id', 'user', 'profile_picture', 'comment', 'created_at']

class ShareModelSerializer(BaseInteractionSerializer):
    class Meta:
        model = ShareModel
        fields = ['id', 'user', 'profile_picture', 'created_at']

class PinModelSerializer(BaseInteractionSerializer):
    class Meta:
        model = PinModel
        fields = ['id', 'user', 'profile_picture', 'created_at']

class SaveModelSerializer(BaseInteractionSerializer):
    class Meta:
        model = SaveModel
        fields = ['id', 'user', 'profile_picture', 'created_at']

class PostCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostModel
        fields = ['title', 'description', 'media']

class PostModelSerializer(serializers.ModelSerializer):
    likes_list = LikeModelSerializer(many=True, source='likes', read_only=True)
    comments_list = serializers.SerializerMethodField()
    shares_list = ShareModelSerializer(many=True, source='shares', read_only=True)
    pins_list = PinModelSerializer(many=True, source='pins', read_only=True)
    saves_list = SaveModelSerializer(many=True, source='saved_by', read_only=True)
    
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    user_details = CustomUserModelSerializer(source='user', read_only=True)

    total_likes = serializers.SerializerMethodField()
    total_comments = serializers.SerializerMethodField()
    total_shares = serializers.SerializerMethodField()
    total_pins = serializers.SerializerMethodField()
    total_saves = serializers.SerializerMethodField()

    class Meta:
        model = PostModel
        fields = [
            'id', 'title', 'description', 'media', 'post_type',
            'user', 'user_details',
            'total_likes', 'total_comments', 'total_shares', 'total_pins', 'total_saves',
            'likes_list', 'comments_list', 'shares_list', 'pins_list', 'saves_list',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'user_details', 'post_type', 'total_likes', 'total_comments', 'total_shares', 'total_pins', 'total_saves']


    def get_total_likes(self, obj):
        return obj.likes.count()

    def get_total_comments(self, obj):
        return obj.comments.count()

    def get_total_shares(self, obj):
        return obj.shares.count()

    def get_total_pins(self, obj):
        return obj.pins.count()

    def get_total_saves(self, obj):
        return obj.saved_by.count()

    def get_comments_list(self, obj):
        request = self.context.get('request')
        comments = obj.comments.all()
        if request and request.user.is_authenticated:
            blocked_user_ids = request.user.blocked_users_relationship.values_list('blocked_id', flat=True)
            blocked_by_ids = request.user.blocked_by_relationship.values_list('blocker_id', flat=True)
            comments = comments.exclude(user_id__in=blocked_user_ids).exclude(user_id__in=blocked_by_ids)
        return CommentModelSerializer(comments, many=True, context=self.context).data