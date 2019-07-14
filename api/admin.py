from django.contrib import admin
from .models import Post, PostReaction, SavedPost, Profile, Comment, ForgetPassword, CommentReply, CommentVote, \
    ReplyVote, WikiPedia, FollowedPeople, TopStories, UserGroup, GroupCommentary, ProfileCommentary


class PostAdmin(admin.ModelAdmin):
    change_list_template = 'changeadmin.html'


admin.site.register(Post, PostAdmin)

# Register your models here.
admin.site.register(WikiPedia)
admin.site.register(PostReaction)
admin.site.register(SavedPost)
admin.site.register(Profile)
admin.site.register(Comment)
admin.site.register(CommentVote)
admin.site.register(CommentReply)
admin.site.register(UserGroup)
admin.site.register(ReplyVote)
admin.site.register(ForgetPassword)
admin.site.register(FollowedPeople)
admin.site.register(TopStories)
admin.site.register(GroupCommentary)
admin.site.register(ProfileCommentary)
