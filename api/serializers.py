from .models import Post, PostReaction, SavedPost, Comment, Profile, ForgetPassword, CommentReply, CommentVote, \
    ReplyVote, UserGroup
from rest_framework import routers, serializers, viewsets
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


from drf_extra_fields.fields import Base64ImageField


# class PostSerializer(serializers.ModelSerializer):
#     thumbnail_image = Base64ImageField()
#     embedded_image = Base64ImageField()
#
#     # get_relevant_post_json = serializers.JSONField()
#     get_relevant_post_json = serializers.ReadOnlyField()
#

#     class Meta:
#
#
#         model = Post
#         fields = "__all__"

class PostSerializer(serializers.ModelSerializer):
    thumbnail_image = Base64ImageField()
    embedded_image = Base64ImageField()
    json_data = serializers.SerializerMethodField()
    recommended_json = serializers.SerializerMethodField()
    created_at_str = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = '__all__'

    def get_json_data(self, obj):
        return obj.get_json

    def get_recommended_json(self, obj):
        request = self.context.get('request')
        return obj.get_recommended(request)

    def get_created_at_str(self, obj):
        return obj.get_created_at_str

class UserGroupSerializer(serializers.ModelSerializer):
    json_data = serializers.SerializerMethodField()
    users_json = serializers.SerializerMethodField()
    class Meta:
        model = UserGroup
        fields = '__all__'
    def get_users_json(self, obj):
        request = self.context.get('request')
        return obj.get_users(request)


class CommentVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentVote
        fields = "__all__"


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = "__all__"


class PostReactionSerializer(serializers.ModelSerializer):
    # user = UserSerializer(many=False, read_only=False)
    class Meta:
        model = PostReaction
        fields = "__all__"


class ForgetPasswordSerializer(serializers.ModelSerializer):
    # user = UserSerializer(many=False, read_only=False)
    class Meta:
        model = ForgetPassword
        fields = "__all__"


class SavedPostSerializer(serializers.ModelSerializer):
    # post = PostSerializer(many=False, read_only=False)

    class Meta:
        model = SavedPost
        fields = "__all__"


class CommentReplySerializer(serializers.ModelSerializer):
    # user = UserSerializer(many=False, read_only=False)
    class Meta:
        model = CommentReply
        fields = "__all__"


class CommentSerializer(serializers.ModelSerializer):
    # user = UserSerializer(many=False, read_only=False)
    class Meta:
        model = Comment
        fields = "__all__"

class UserGroupSerializer(serializers.ModelSerializer):
    # user = UserSerializer(many=False, read_only=False)
    class Meta:
        model = UserGroup
        fields = "__all__"


class ReplyVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReplyVote
        fields = "__all__"
