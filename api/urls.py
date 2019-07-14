from django.conf.urls import url, include
from django.urls import path
from rest_framework import routers
from .views import PostViewSet, PostReactionViewSet, SavedPostViewSet, Login, Signup, ForgetPassword, UserViewSet, \
    CommentViewSet,CommentaryViewSet, UserGroupViewSet, ProfileViewSet, ResetPassword, CommentReplyViewSet, CommentVoteViewSet, ReplyVoteViewSet, \
    sendVerificationEmail, generate_graph, export_all_posts, search, follow_people, get_posts_people_follow_status, \
    get_profile_content, get_trending_search, follow_user, get_top_stories, get_home_posts, get_notifications, \
    get_profile_owner_of_post, update_profile_settings, pin_commentary, pin_my_post, pin_following_profile, \
    like_commentary,get_group_count_by_user,create_new_group, get_groups_by_user, get_group_feeds_by_user, get_groupinfo_by_id, \
    get_group_posts_by_group, get_all_groupinfo, join_group, add_group_comment, unjoin_group_by_user,get_all_groups, \
    get_group_feeds_by_group, add_comment, search_group_by_name, pin_group, vote_comment, remove_group_feed_by_id, \
    add_pin_to_group, get_all_posts, get_saved_comments_by_post, get_comment_replies_by_comment, exists_profile_uid, get_total_commments_count, \
    get_total_replies_count, get_saved_comments_by_user, get_posts_by_user, vote_post, pin_post, add_reply, search_invite_users, \
    add_users_to_group, get_search_keywords, check_group_alert, add_group_photo, check_notification

from django.conf.urls import url

router = routers.DefaultRouter()
router.register(r'post', PostViewSet)
router.register(r'post-reaction', PostReactionViewSet)
router.register(r'saved-post', SavedPostViewSet)
router.register(r'user', UserViewSet)
router.register(r'comment', CommentViewSet)
router.register(r'commentary', CommentaryViewSet)
router.register(r'usergroup', UserGroupViewSet)
router.register(r'user-profile', ProfileViewSet)
router.register(r'comment-vote', CommentVoteViewSet)
router.register(r'comment-reply', CommentReplyViewSet)
router.register(r'reply-vote', ReplyVoteViewSet)

urlpatterns = [
    url(r'', include(router.urls)),
    url('generate_graph/', generate_graph),
    url('export_all_posts/', export_all_posts),
    url('forget-password/', ForgetPassword),
    url('reset-password/', ResetPassword),
    url('send-verification-email/', sendVerificationEmail),
    url('get_trending_search/', get_trending_search),
    url('search/', search),
    url('follow_people/', follow_people),
    url('get_posts_people_follow_status/', get_posts_people_follow_status),
    url('get_profile_content/', get_profile_content),
    url('follow_user/', follow_user),
    url('get_top_stories/', get_top_stories),
    url('get_home_posts/', get_home_posts),
    url('get_notifications/', get_notifications),
    url('get_profile_owner_of_post/', get_profile_owner_of_post),
    url('update_profile_settings/', update_profile_settings),
    url('pin_commentary/', pin_commentary),
    url('pin_my_post/', pin_my_post),
    url('pin_group/', pin_group),
    url('pin_following_profile/', pin_following_profile),
    url('like_commentary/', like_commentary),
    url('get_group_count_by_user/', get_group_count_by_user),
    url('create_new_group/', create_new_group),
    url('get_groups_by_user/', get_groups_by_user),
    url('get_all_groups/', get_all_groups),
    url('get_group_feeds_by_user/', get_group_feeds_by_user),
    url('get_group_feeds_by_group/', get_group_feeds_by_group),
    url('get_groupinfo_by_id/', get_groupinfo_by_id),
    url('get_group_posts_by_group/', get_group_posts_by_group),
    url('search_group_by_name/', search_group_by_name),
    url('get_all_groupinfo/', get_all_groupinfo),
    url('join_group/', join_group),
    url('add_group_comment/', add_group_comment),
    url('add_comment/', add_comment),
    url('unjoin_group_by_user/', unjoin_group_by_user),
    url('vote_comment/', vote_comment),
    url('get_all_posts/', get_all_posts),
    url('remove_group_feed_by_id/', remove_group_feed_by_id),
    url('add_pin_to_group/', add_pin_to_group),
    url('get_saved_comments_by_post/', get_saved_comments_by_post),
    url('get_comment_replies_by_comment/', get_comment_replies_by_comment),
    url('exists_profile_uid/', exists_profile_uid),
    url('get_total_commments_count/', get_total_commments_count),
    url('get_total_replies_count/', get_total_replies_count),
    url('get_saved_comments_by_user/', get_saved_comments_by_user),
    url('get_posts_by_user/', get_posts_by_user),
    url('vote_post/', vote_post),
    url('pin_post/', pin_post),
    url('add_reply/', add_reply),
    url('search_invite_users/', search_invite_users),
    url('add_users_to_group/', add_users_to_group),
    url('get_search_keywords/', get_search_keywords),
    url('check_group_alert/', check_group_alert),
    url('add_group_photo/', add_group_photo),
    url('check_notification/', check_notification),
]
