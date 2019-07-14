import base64
import json
import mimetypes
import random
import smtplib
import string
import time

from django.utils import timezone
import requests
from coreapi.auth import SessionAuthentication, BasicAuthentication
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
# import django_filters.rest_framework
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action, detail_route
from rest_framework.parsers import MultiPartParser, FileUploadParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import Post, PostReaction, SavedPost, Comment, Profile, CommentReply, CommentVote, \
    ForgetPassword as ForgetPasswordModel, ReplyVote, PeoplePostRelationship, UserPostViewed, TopPeopleInSavedPost, \
    TopPeopleInLikedPost, WikiPedia, FollowedPeople, TrendingSearch, TopStories, Notification, VOTE_TYPE_CHOICES, \
    VoteSavedPost, UserGroup, GroupComment, VoteComment, PostVote, GroupCommentary, ProfileCommentary

from .serializers import PostSerializer, PostReactionSerializer, SavedPostSerializer, UserSerializer, CommentSerializer, \
    ProfileSerializer, CommentReplySerializer, CommentVoteSerializer, ReplyVoteSerializer, UserGroupSerializer
import csv
from wsgiref.util import FileWrapper
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from django.contrib.auth.decorators import login_required


# Create your views here.

## TODO: delete
# my_user = User.objects.all().first()  # request.user
# current_profile = Profile.objects.filter(user=my_user).first()


def get_user_obj(user_id):
    user_obj = User.objects.filter(id=user_id).first()
    return user_obj


def get_user_profile_obj(user):
    profile_obj = Profile.objects.filter(user=user).first()
    return profile_obj


def get_primary_people_from_post(post_obj):
    primary_people = None
    people1 = post_obj.people1
    if people1:
        primary_people = str(people1).lower().strip("")
    return primary_people


def is_required_reaction(post_reaction_object):
    if post_reaction_object.reaction_type == "like" or \
                    post_reaction_object.reaction_type == "funny":
        return True
    return False


def increment_count_top_people_in_liked_post(reaction_obj, data_dic, force_update=False):
    try:
        if is_required_reaction(reaction_obj) or force_update:
            user_obj = None
            if 'user' in data_dic:
                user_obj = get_user_obj(data_dic['user'])
            primary_people = get_primary_people_from_post(reaction_obj.post)
            if user_obj and primary_people:
                print("incremented by:", user_obj.email, primary_people)
                existing_object = TopPeopleInLikedPost.objects.filter(user=user_obj,
                                                                      people_name__iexact=primary_people).first()
                if existing_object:
                    existing_object.total_count += 1
                else:
                    existing_object = TopPeopleInLikedPost.objects.create(user=user_obj, people_name=primary_people,
                                                                          total_count=1)
                existing_object.save()
                print(existing_object.people_name, existing_object.total_count)
    except Exception as e:
        print("exception in increment_count_top_people_in_liked_post", str(e))


def decrease_count_top_people_in_liked_post(reaction_obj, data_dic, force=False):
    try:
        if is_required_reaction(reaction_obj):
            print("if")
            if not force and 'reaction_type' in data_dic:
                if data_dic['reaction_type'] == "like" or \
                                data_dic['reaction_type'] == "funny":
                    return
            user_obj = None
            if 'user' in data_dic:
                user_obj = get_user_obj(data_dic['user'])
            primary_people = get_primary_people_from_post(reaction_obj.post)
            if user_obj and primary_people:
                print("decrmented by:", user_obj.email, primary_people)
                existing_object = TopPeopleInLikedPost.objects.filter(user=user_obj,
                                                                      people_name__iexact=primary_people).first()
                if existing_object:
                    if existing_object.total_count > 0:
                        existing_object.total_count -= 1
                existing_object.save()
                print(existing_object.people_name, existing_object.total_count)
        else:
            print("else")
            if 'reaction_type' in data_dic:
                if data_dic['reaction_type'] == "like" or \
                                data_dic['reaction_type'] == "funny":
                    increment_count_top_people_in_liked_post(reaction_obj, data_dic, True)
    except Exception as e:
        print("exception in decrease_count_top_people_in_liked_post", str(e))


def get_related_posts_list(people_name, published_in_24_hours=False):
    people_name = str(people_name).lower().strip(" ")
    if published_in_24_hours:
        date_from = timezone.now() - timezone.timedelta(days=1)
        people_posts_list = PeoplePostRelationship.objects.filter(people_name__icontains=people_name,
                                                                  post_id__created_at__gte=date_from).order_by('-id')
    else:
        people_posts_list = PeoplePostRelationship.objects.filter(people_name__icontains=people_name).order_by('-id')
    return people_posts_list


def pick_next_post(filled_list, searchable_list, user_saved_post_list, current_post, user_obj, lower_score_range,
                   upper_score_range,
                   probability_value):
    try:
        filled_list = list(filled_list)
        new_post_probability = random.randint(1, 100)
        new_only = True
        if new_post_probability >= probability_value:
            new_only = False
        score_range_probability = random.randint(1, 100)
        check_score_range = True
        if score_range_probability >= probability_value:
            check_score_range = False
        recommended_post = None
        if searchable_list:
            for search_related_object in searchable_list:
                if not search_related_object.post_id == current_post:
                    if not user_saved_post_list.__contains__(search_related_object.post_id):
                        if not filled_list.__contains__(search_related_object.post_id):
                            if not new_only:
                                recommended_post = search_related_object.post_id
                                print("old recommended", recommended_post)
                            else:
                                already_viewed = UserPostViewed.objects.filter(user=user_obj,
                                                                               post_id=search_related_object.post_id).first()
                                if not already_viewed:
                                    # if check_score_range:
                                    #     if lower_score_range <= search_related_object.post_id.positive_score <= upper_score_range:
                                    #         recommended_post = search_related_object.post_id
                                    #         print("new+score recommended", recommended_post)
                                    # else:
                                    recommended_post = search_related_object.post_id
                                    print("new recommended", recommended_post)
                if recommended_post:
                    break

    except Exception as e:
        print("exception in pick_next_post", str(e))
    finally:
        return recommended_post


def calculate_recommended_posts(current_post_obj, user_obj, is_creating=True):
    try:
        saved_post_list = SavedPost.objects.filter(user=user_obj)
        user_saved_post_list = []
        for saved_post in saved_post_list:
            user_saved_post_list.append(saved_post.post)
        # print("user saved list", user_saved_post_list)
        max_posts_count = 12
        score_delta = 20.0
        lower_score_range = current_post_obj.positive_score - score_delta
        upper_score_range = current_post_obj.positive_score + score_delta
        if lower_score_range < 0.0:
            lower_score_range = 0
        if upper_score_range > 100.0:
            upper_score_range = 100.0

        final_recommended_list = []

        top_liked_posts_recommended = []
        top_saved_posts_recommended = []
        current_article_related_posts = list(get_related_posts_list(current_post_obj.people1))

        top_liked_people_list = TopPeopleInLikedPost.objects.filter(user=user_obj).order_by('-total_count')[:3]
        for top_liked_people in top_liked_people_list:
            result = get_related_posts_list(top_liked_people.people_name)
            if result:
                top_liked_posts_recommended += list(result)
                # print(top_liked_people.people_name)

        # print(top_liked_posts_recommended)
        top_saved_people_list = TopPeopleInSavedPost.objects.filter(user=user_obj).order_by('-total_count')[:3]
        for top_save_people in top_saved_people_list:
            result = get_related_posts_list(top_save_people.people_name)
            if result:
                top_saved_posts_recommended += list(result)

        for total_sets in range(3):
            new_post_probability = 80
            if total_sets == 0:
                new_post_probability = 80
            for i in range(4):
                source_list = None
                if i == 0 or i == 1:
                    source_list = current_article_related_posts
                elif i == 2:
                    source_list = top_liked_posts_recommended
                elif i == 3:
                    source_list = top_saved_posts_recommended
                # print(str(i), source_list)
                recommended_obj = pick_next_post(final_recommended_list, source_list, user_saved_post_list,
                                                 current_post_obj, user_obj, lower_score_range, upper_score_range,
                                                 new_post_probability)
                if recommended_obj:
                    print(total_sets, i, recommended_obj)
                    final_recommended_list.append(recommended_obj)

        current_post_obj.recommended_post_list.clear()
        counter = 0
        # final_recommended_list = Post.objects.all()
        for post in final_recommended_list:
            if (get_user_profile_obj(post.user)).verified:
                current_post_obj.recommended_post_list.add(post)
                counter += 1
                if counter == max_posts_count:
                    break
        current_post_obj.save()

        print("RELEVANT LIST:", current_post_obj.recommended_post_list.all())
    except Exception as e:
        print("exception in calculate_related_posts", str(e))


def get_filtered_top_list(filled_list, searchable_list, user_saved_post_list):
    try:
        filled_list = list(filled_list)
        recommended_list = []
        if searchable_list:
            for search_related_object in searchable_list:
                if not user_saved_post_list.__contains__(search_related_object.post_id):
                    if not filled_list.__contains__(search_related_object.post_id):
                        recommended_list.append(search_related_object.post_id)
                        break
    except Exception as e:
        print("exception in pick_next_post", str(e))
    finally:
        return recommended_list


def calculate_top_stories(user_obj, fixed_posts_list, max_total_posts):
    try:
        saved_post_list = SavedPost.objects.filter(user=user_obj)
        user_saved_post_list = [] + fixed_posts_list
        for saved_post in saved_post_list:
            user_saved_post_list.append(saved_post.post)
        max_posts_count = 24
        top_posts_picked = []
        final_recommended_list = []

        top_liked_posts_recommended = []
        top_saved_posts_recommended = []

        top_liked_people_list = TopPeopleInLikedPost.objects.filter(user=user_obj).order_by('-total_count')[:3]
        for top_liked_people in top_liked_people_list:
            result = get_related_posts_list(top_liked_people.people_name, True)
            if result:
                top_liked_posts_recommended += list(result)
                # print(top_liked_people.people_name)

        # print("top_liked_posts_recommended", top_liked_posts_recommended)
        top_saved_people_list = TopPeopleInSavedPost.objects.filter(user=user_obj).order_by('-total_count')[:3]
        for top_save_people in top_saved_people_list:
            result = get_related_posts_list(top_save_people.people_name, True)
            if result:
                top_saved_posts_recommended += list(result)
        # print("top_saved_posts_recommended", top_saved_posts_recommended)

        filtered_top_liked_list = get_filtered_top_list(final_recommended_list,
                                                        top_liked_posts_recommended,
                                                        user_saved_post_list)
        final_recommended_list += filtered_top_liked_list

        filtered_top_saved_list = get_filtered_top_list(final_recommended_list,
                                                        top_saved_posts_recommended,
                                                        user_saved_post_list)
        final_recommended_list += filtered_top_saved_list

        if final_recommended_list.__len__() < max_total_posts:
            max_total_posts = final_recommended_list.__len__()
        while len(top_posts_picked) != max_total_posts:
            post_index = random.randint(0, (final_recommended_list.__len__() - 1))
            top_posts_picked.append(final_recommended_list[post_index])
            del final_recommended_list[post_index]

    except Exception as e:
        print("exception in calculate_top_stories", str(e))
    finally:
        return top_posts_picked


def calculate_related_posts(post_obj, is_creating=True):
    try:
        max_posts_count = 3
        new_people_1 = str(post_obj.people1).strip(" ")
        new_people_2 = str(post_obj.people2).strip(" ")
        new_people_3 = str(post_obj.people3).strip(" ")
        new_people_4 = str(post_obj.people4).strip(" ")
        people_posts_all = []

        if new_people_1.__len__() > 0:
            people_posts_list = PeoplePostRelationship.objects.filter(people_name__icontains=new_people_1)
            people_posts_all += list(people_posts_list)
        if new_people_2.__len__() > 0:
            people_posts_list = PeoplePostRelationship.objects.filter(people_name__icontains=new_people_2)
            people_posts_all += list(people_posts_list)
        if new_people_3.__len__() > 0:
            people_posts_list = PeoplePostRelationship.objects.filter(people_name__icontains=new_people_3)
            people_posts_all += list(people_posts_list)
        if new_people_4.__len__() > 0:
            people_posts_list = PeoplePostRelationship.objects.filter(people_name__icontains=new_people_4)
            people_posts_all += list(people_posts_list)

        post_list = list(set([people_post.post_id for people_post in people_posts_all]))
        post_obj.relevant_post_list.clear()
        counter = 0
        # print("POST LIST BEFORE", post_list)
        # post_list = sorted(post_list, key=lambda x: x.created_at, reverse=True)
        # print("POST LIST After", post_list)
        for post in post_list:
            if not post == post_obj:
                if get_user_profile_obj(post.user).verified:
                    post_obj.relevant_post_list.add(post)
                    counter += 1
            if counter == max_posts_count:
                break
        post_obj.save()

        if (not post_obj.is_private_post) and is_creating:
            people_str = ""
            all_people_in_post = []
            if new_people_1.__len__() > 0:
                people_str += new_people_1 + ","
                all_people_in_post.append(new_people_1)
            if new_people_2.__len__() > 0:
                people_str += new_people_2 + ","
                all_people_in_post.append(new_people_2)
            if new_people_3.__len__() > 0:
                people_str += new_people_3 + ","
                all_people_in_post.append(new_people_3)
            if new_people_4.__len__() > 0:
                people_str += new_people_4 + ","
                all_people_in_post.append(new_people_4)
            people_str = people_str.strip(",")

            people_post_obj = PeoplePostRelationship.objects.create(post_id=post_obj, people_name=people_str)
            people_post_obj.save()

            for people_name in all_people_in_post:
                all_users_qs = FollowedPeople.objects.filter(people_name__iexact=people_name).select_related('user'). \
                    values_list('user', flat=True)
                # print(people_name, "all_users", all_users_qs)
                if all_users_qs:
                    related_profiles = Profile.objects.filter(user__in=all_users_qs)
                    # creating notification
                    notification = Notification.objects.create(
                        notification_type=Notification.Notification_Type_Post)
                    if notification:
                        notification.related_profile.add(*list(related_profiles))
                        notification.people_keyword = people_name
                        notification.save()
    except Exception as e:
        print("exception in calculate_related_posts", str(e))


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.filter(is_private_post=False).order_by('-id')
    serializer_class = PostSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'title', 'category')

    def create(self, request, *args, **kwargs):
        print(request.data)
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        print("//////////////////////////////////////////////////////")
        print(request.is_ajax())
        # if not serializer.instance.user.is_superuser:
        #     serializer.instance.is_private_post = True
        #     serializer.instance.save()

        get_graph_json_from_object(request, serializer.instance)
        calculate_related_posts(serializer.instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['POST'])
    def add_friend(self, request, pk=None):
        print("add_friend")
        pid = self.request.GET.get('pk')
        instance = Post.objects.filter(id=pid).first()
        user_obj = get_user_obj(request.data['user'])
        get_graph_json_from_object(request, instance, user_obj)
        serializer = self.get_serializer(instance, context={"request": request})
        # calculating first recommendation engine
        calculate_related_posts(serializer.instance, False)
        # print(request.data)
        # recording this post have viewed by this logged in user
        if user_obj:
            serializer.instance.total_views += 1
            serializer.instance.save()
            calculate_recommended_posts(instance, user_obj)
            is_already_viewed = UserPostViewed.objects.filter(post_id=instance, user=user_obj).first()
            if not is_already_viewed:
                viewed_obj = UserPostViewed.objects.create(post_id=instance, user=user_obj)
                print("viewed by", user_obj.email)
                viewed_obj.save()
            else:
                print("already viewed by", user_obj.email)

                # adding notification for
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        # print("I am retrv")
        instance = self.get_object()
        # get_graph_json_from_object(instance)
        serializer = self.get_serializer(instance)
        self.calculate_related_posts(serializer.instance, False)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        print("update")
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={"request": request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    @action(detail=False, methods=['POST'])
    def delete_post(self, request, pk=None):
        try:
            pid = self.request.GET.get('pk')
            instance = Post.objects.filter(id=pid).first()
            instance.delete()
                    
        except Exception as es:
            print("Exception in delete_post", str(es))
        finally:
            return Response(status=status.HTTP_204_NO_CONTENT)

  
class CommentVoteViewSet(viewsets.ModelViewSet):
    queryset = CommentVote.objects.all()
    serializer_class = CommentVoteSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('comment', 'user', 'vote_type')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        notification_type = Notification.Notification_Type_Like
        if  (serializer.instance.comment.user.id != serializer.instance.user.id):
            if str(serializer.instance.vote_type) == "DOWN_VOTE":
                notification_type = Notification.Notification_Type_Dislike
            related_profile_obj = get_user_profile_obj(get_user_obj(serializer.instance.comment.user.id))
            activity_profile_obj = get_user_profile_obj(get_user_obj( serializer.instance.user.id))
            if related_profile_obj and activity_profile_obj:
                notification = Notification.objects.create(
                    notification_type=notification_type)
                if notification:
                    notification.related_profile.add(related_profile_obj)
                    notification.profile_id = activity_profile_obj.id
                    notification.post_id = -1
                    notification.comment_id = serializer.instance.comment.id
                    notification.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'user')

class UserGroupViewSet(viewsets.ModelViewSet):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'name')


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'user', 'post', 'kind')
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.kind == 2:
            ProfileCommentary.objects.filter(post=instance.post, user=instance.user, comment=instance.comment).delete()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
# class UserGroupViewSet(viewsets.ModelViewSet):
#     queryset = UserGroup.objects.all()
#     serializer_class = UserGroupSerializer
#     filter_backends = (DjangoFilterBackend,)
#     filter_fields = ('id', 'name', 'creator')
class CommentaryViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.filter(Q(kind=1) | Q(kind=2)).all()
    serializer_class = CommentSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'kind')

class CommentReplyViewSet(viewsets.ModelViewSet):
    queryset = CommentReply.objects.all()
    serializer_class = CommentReplySerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'user', 'comment', 'replied_reply')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        if(serializer.instance.comment):
            if serializer.instance.comment.user.id != serializer.instance.user.id:
                related_profile_obj = get_user_profile_obj(get_user_obj(serializer.instance.comment.user.id))
                activity_profile_obj = get_user_profile_obj(get_user_obj(serializer.instance.user.id))
                if related_profile_obj and activity_profile_obj:
                    notification = Notification.objects.create(
                        notification_type=Notification.Notification_Type_Reply)
                    if notification:
                        notification.related_profile.add(related_profile_obj)
                        notification.profile_id = activity_profile_obj.id
                        notification.post_id = serializer.instance.comment.id
                        notification.comment_id = serializer.instance.id
                        notification.save()
        if(serializer.instance.replied_reply):
            print(serializer.instance.replied_reply.user.id)
            print(serializer.instance.user.id)
            if serializer.instance.replied_reply.user.id != serializer.instance.user.id:
                # firing notification to parent comment user
                related_profile_obj = get_user_profile_obj(get_user_obj(serializer.instance.replied_reply.user.id))
                activity_profile_obj = get_user_profile_obj(get_user_obj(serializer.instance.user.id))
                
                if related_profile_obj and activity_profile_obj:                    
                    notification = Notification.objects.create(
                        notification_type=Notification.Notification_Type_Reply)
                    if notification:
                        notification.related_profile.add(related_profile_obj)
                        notification.profile_id = activity_profile_obj.id
                        notification.comment_id = serializer.instance.id
                        notification.save()

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        print("reply vote update")
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={"request": request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if(serializer.instance.comment):
            if serializer.instance.comment.user.id != serializer.instance.user.id:
                related_profile_obj = get_user_profile_obj(get_user_obj(serializer.instance.comment.user.id))
                activity_profile_obj = get_user_profile_obj(get_user_obj(serializer.instance.user.id))
                if related_profile_obj and activity_profile_obj:
                    notification = Notification.objects.create(
                        notification_type=Notification.Notification_Type_Reply)
                    if notification:
                        notification.related_profile.add(related_profile_obj)
                        notification.profile_id = activity_profile_obj.id
                        notification.post_id = serializer.instance.comment.id
                        notification.comment_id = serializer.instance.id
                        notification.save()
        if(serializer.instance.replied_reply):
            print(serializer.instance.replied_reply.user.id)
            print(serializer.instance.user.id)
            if serializer.instance.replied_reply.user.id != serializer.instance.user.id:
                # firing notification to parent comment user
                related_profile_obj = get_user_profile_obj(get_user_obj(serializer.instance.replied_reply.user.id))
                activity_profile_obj = get_user_profile_obj(get_user_obj(serializer.instance.user.id))
                
                if related_profile_obj and activity_profile_obj:                    
                    notification = Notification.objects.create(
                        notification_type=Notification.Notification_Type_Reply)
                    if notification:
                        notification.related_profile.add(related_profile_obj)
                        notification.profile_id = activity_profile_obj.id
                        notification.comment_id = serializer.instance.replied_reply.comment.id
                        notification.save()       

        return Response(serializer.data)

class PostReactionViewSet(viewsets.ModelViewSet):
    queryset = PostReaction.objects.all()
    serializer_class = PostReactionSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('post', 'user', 'reaction_type')

    def create(self, request, *args, **kwargs):
        try:
            print("post reaction created")
            print(request.data)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            increment_count_top_people_in_liked_post(serializer.instance, request.data)
        except Exception as es:
            print("Exception in save post create", str(es))
        finally:
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        print("post reaction update", request.data)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        decrease_count_top_people_in_liked_post(instance, request.data)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    @action(detail=False, methods=['POST'])
    def delete_post_reaction(self, request, pk=None):
        try:
            print("delete_post_reaction", request.data)
            pid = self.request.GET.get('pk')
            instance = PostReaction.objects.filter(id=pid).first()
            decrease_count_top_people_in_liked_post(instance, request.data, True)
            instance.delete()
        except Exception as es:
            print("Exception in delete_saved_post", str(es))
        finally:
            return Response(status=status.HTTP_204_NO_CONTENT)


class SavedPostViewSet(viewsets.ModelViewSet):
    queryset = SavedPost.objects.all().order_by('-id')
    serializer_class = SavedPostSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'user')

    def create(self, request, *args, **kwargs):
        try:
            print("save post created")
            print(request.data)
            user_obj = None
            if 'user' in request.data:
                user_obj = get_user_obj(request.data['user'])
            profile_obj = get_user_profile_obj(user_obj)
            request.data['profile'] = profile_obj.id
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            # recording primary people of saved post

            primary_people = get_primary_people_from_post(serializer.instance.post)
            if user_obj and primary_people:
                print("saved by:", user_obj.email, primary_people)
                existing_object = TopPeopleInSavedPost.objects.filter(user=user_obj,
                                                                      people_name__iexact=primary_people).first()
                if existing_object:
                    existing_object.total_count += 1
                else:
                    existing_object = TopPeopleInSavedPost.objects.create(user=user_obj, people_name=primary_people,
                                                                          total_count=1)
                existing_object.save()
                print(existing_object.people_name, existing_object.total_count)

            # setting notification for saved post
            if user_obj:
                # profile_obj = get_user_profile_obj(user_obj)
                if profile_obj:
                    related_profiles = Profile.objects.filter(following__in=[profile_obj])
                    if related_profiles and len(related_profiles) > 0:
                        notification = Notification.objects.create(
                            notification_type=Notification.Notification_Type_Commentary)
                        if notification:
                            notification.related_profile.add(*list(related_profiles))
                            notification.profile_id = profile_obj.id
                            notification.save()

        except Exception as es:
            print("Exception in save post create", str(es))
        finally:
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['POST'])
    def delete_saved_post(self, request, pk=None):
        try:
            pid = self.request.GET.get('pk')
            instance = SavedPost.objects.filter(id=pid).first()
            user_obj = None
            if 'user' in request.data:
                user_obj = get_user_obj(request.data['user'])
            primary_people = get_primary_people_from_post(instance.post)
            if user_obj and primary_people:
                print("deleted by:", user_obj.email, primary_people)
                existing_object = TopPeopleInSavedPost.objects.filter(user=user_obj,
                                                                      people_name__iexact=primary_people).first()
                if existing_object:
                    if existing_object.total_count > 0:
                        existing_object.total_count -= 1
                existing_object.save()
                print(existing_object.people_name, existing_object.total_count)

            instance.delete()
        except Exception as es:
            print("Exception in delete_saved_post", str(es))
        finally:
            return Response(status=status.HTTP_204_NO_CONTENT)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('id', 'username', 'first_name', 'last_name', 'email')


class ReplyVoteViewSet(viewsets.ModelViewSet):
    queryset = ReplyVote.objects.all()
    serializer_class = ReplyVoteSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('user', 'reply', 'vote_type')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        print(serializer.instance.reply.user.id, serializer.instance.vote_type, serializer.instance.user.id)
        notification_type = Notification.Notification_Type_Like
        if (serializer.instance.reply.user.id != serializer.instance.user.id):
            if str(serializer.instance.vote_type) == "DOWN_VOTE":
                notification_type = Notification.Notification_Type_Dislike
            related_profile_obj = get_user_profile_obj(get_user_obj( serializer.instance.reply.user.id))
            activity_profile_obj = get_user_profile_obj(get_user_obj( serializer.instance.user.id))
            if related_profile_obj and activity_profile_obj:
                notification = Notification.objects.create(
                    notification_type=notification_type)
                if notification:
                    notification.related_profile.add(related_profile_obj)
                    notification.profile_id = activity_profile_obj.id
                    notification.post_id = -2
                    notification.comment_id = serializer.instance.reply.id
                    notification.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

def generate_graph(request):
    response = {}
    post_response = {}
    if request.method == 'POST':
        source = ""
        url = str(request.POST.get('url_path')).strip(" ")
        email_user = str(request.POST.get('email')).strip(" ")
        print("url", url)
        print("email_user", email_user)
        source = url
        file_type = ""
        print("FILES", request.FILES)
        if 'file_txt' in request.FILES:
            file = str(request.FILES['file_txt']).lower()
            if file.__contains__(".pdf"):
                file_type = "pdf"
                source = file_type
                uploaded_file_content = request.FILES['file_txt'].read()
            else:
                file_type = "txt"
                source = file_type
                uploaded_file_content = str(request.FILES['file_txt'].read().decode("utf-8")).replace("\n", "").strip(
                    " ")
            url = uploaded_file_content
            print("content selected from file")

        if url.__len__() > 0:
            try:
                import main_script as script
                import SentimentAnalysisModels as sentiment_script
                sentences = script.get_data_list(url, file_type)
                response['sentences'] = sentences
                # response['sentiments'] = sentiment_script.get_sentiment_result(sentences)
                # print(response['sentiments'])
                keywords_dic = script.get_keywords_dic(url, file_type)
                response['people'] = keywords_dic['people']
                response['organization'] = keywords_dic['organization']
                # response['people'] = prepare_wiki_data(response['people'])
                # response['organization'] = prepare_wiki_data(response['organization'])
                # print(response['people'])
                # print(response['organization'])
                # request.user.current_type = file_type
                # if file_type == "":
                #   request.user.current_url = url
                # request.user.current_response_data = json.dumps(response)
                # print("generated json", json.dumps(response))

                my_user = User.objects.filter(email__exact=email_user).first()  # request.user
                current_profile = Profile.objects.filter(user=my_user).first()

                post_response['title'] = "Post of " + source
                post_response['author'] = current_profile.name
                post_response['source'] = source
                post_response['category'] = "Economy"
                post_response['author_description'] = "author_description"

                # new_post = Post.objects.create(title="Post of " + source, user=my_user, source=source, category="Economy",
                #                                author=current_profile.name,
                #                                json_response=json.dumps(response))
                if True:
                    if len(sentences) > 0:
                        post_response['main_sentence'] = sentences[0]
                    if len(sentences) > 1:
                        post_response['sentence2'] = sentences[1]
                    if len(sentences) > 2:
                        post_response['sentence3'] = sentences[2]
                    if len(sentences) > 3:
                        post_response['sentence4'] = sentences[3]
                    if len(sentences) > 4:
                        post_response['sentence5'] = sentences[4]
                    if len(response['people']) > 0:
                        post_response['people1'] = response['people'][0]
                    if len(response['people']) > 1:
                        post_response['people2'] = response['people'][1]
                    if len(response['organization']) > 0:
                        post_response['people3'] = response['organization'][0]
                    if len(response['organization']) > 1:
                        post_response['people4'] = response['organization'][1]
                        # new_post.save()
                        # response = {"post_id": new_post.id}
                        # request.user.save()
            except Exception as e:
                print(str(e))
            finally:
                # print("going to sleep")
                # time.sleep(50)
                print("post response", json.dumps(post_response))
                return HttpResponse(json.dumps(post_response))
                # script.read_pdf(my_uploaded_file_url)  # return redirect(result)
    return HttpResponse(json.dumps(post_response))


# def old_generate_graph(request):
#     response = {}
#     if request.method == 'POST':
#         source = ""
#         url = str(request.POST.get('url_path')).strip(" ")
#         email_user = str(request.POST.get('email')).strip(" ")
#         print("url", url)
#         print("email_user", email_user)
#         source = url
#         file_type = ""
#         if 'file_txt' in request.FILES:
#             file = str(request.FILES['file_txt']).lower()
#             if file.__contains__(".pdf"):
#                 file_type = "pdf"
#                 source = file_type
#                 uploaded_file_content = request.FILES['file_txt'].read()
#             else:
#                 file_type = "txt"
#                 source = file_type
#                 uploaded_file_content = str(request.FILES['file_txt'].read().decode("utf-8")).replace("\n", "").strip(
#                     " ")
#             url = uploaded_file_content
#             print("content selected from file")
#
#         if url.__len__() > 0:
#             try:
#                 import main_script as script
#                 import SentimentAnalysisModels as sentiment_script
#                 sentences = script.get_data_list(url, file_type)
#                 response['sentences'] = sentences
#                 response['sentiments'] = sentiment_script.get_sentiment_result(sentences)
#                 print(response['sentiments'])
#                 keywords_dic = script.get_keywords_dic(url, file_type)
#                 response['people'] = keywords_dic['people']
#                 response['organization'] = keywords_dic['organization']
#                 response['people'] = prepare_wiki_data(response['people'])
#                 response['organization'] = prepare_wiki_data(response['organization'])
#                 # print(response['people'])
#                 # print(response['organization'])
#                 # request.user.current_type = file_type
#                 # if file_type == "":
#                 #   request.user.current_url = url
#                 # request.user.current_response_data = json.dumps(response)
#                 print("generated json", json.dumps(response))
#
#                 my_user = User.objects.all().first()  # request.user
#                 current_profile = Profile.objects.filter(user=my_user).first()
#                 new_post = Post.objects.create(title="Post of " + source, user=my_user, source=source,
#                                                category="Economy",
#                                                author=current_profile.name,
#                                                json_response=json.dumps(response))
#                 if new_post:
#                     if len(sentences) > 0:
#                         new_post.main_sentence = sentences[0]
#                     if len(sentences) > 1:
#                         new_post.sentence2 = sentences[1]
#                     if len(sentences) > 2:
#                         new_post.sentence3 = sentences[2]
#                     if len(sentences) > 3:
#                         new_post.sentence4 = sentences[3]
#                     if len(sentences) > 4:
#                         new_post.sentence5 = sentences[4]
#                     if len(response['people']) > 0:
#                         new_post.people1 = response['people'][0]['keyword']
#                     if len(response['people']) > 1:
#                         new_post.people2 = response['people'][1]['keyword']
#                     if len(response['organization']) > 0:
#                         new_post.people3 = response['organization'][0]['keyword']
#                     if len(response['organization']) > 1:
#                         new_post.people4 = response['organization'][1]['keyword']
#                 new_post.save()
#                 response = {"post_id": new_post.id}
#                 # request.user.save()
#             except Exception as e:
#                 print(str(e))
#             finally:
#                 return HttpResponse(json.dumps(response))
#                 # script.read_pdf(my_uploaded_file_url)  # return redirect(result)
#     return HttpResponse(json.dumps(response))


def get_graph_json_from_object(request, post_obj, user_obj=None):
    response = {}
    try:
        is_same = False
        older_sentences = None
        older_sentiments = None
        if str(post_obj.json_response).__len__() > 0:
            json_response = json.loads(post_obj.json_response)
            # print("already json", json_response)

            older_sentences = sentences = json_response['sentences']
            older_sentiments = json_response['sentiments']
            is_same = True
            if len(sentences) > 0:
                if not post_obj.main_sentence == json_response['sentences'][0]:
                    print("json_response['sentences'][0]")
                    is_same = False
            if len(sentences) > 1:
                if not post_obj.sentence2 == json_response['sentences'][1]:
                    print("json_response['sentences'][1]")
                    is_same = False
            if len(sentences) > 2:
                if not post_obj.sentence3 == json_response['sentences'][2]:
                    print("json_response['sentences'][2]")
                    is_same = False
            if len(sentences) > 3:
                if not post_obj.sentence4 == json_response['sentences'][3]:
                    print("json_response['sentences'][3]")
                    is_same = False
            if len(sentences) > 4:
                if not post_obj.sentence5 == json_response['sentences'][4]:
                    print("json_response['sentences'][4]")
                    is_same = False

        sentences = []
        sentiments = [1, 1, 1, 1, 1]
        keywords_dic = {"people": [], "organization": []}
        if str(post_obj.main_sentence).strip(" ").__len__() > 0:
            sentences.append(str(post_obj.main_sentence).strip(" "))
        if str(post_obj.sentence2).strip(" ").__len__() > 0:
            sentences.append(str(post_obj.sentence2).strip(" "))
        if str(post_obj.sentence3).strip(" ").__len__() > 0:
            sentences.append(str(post_obj.sentence3).strip(" "))
        if str(post_obj.sentence4).strip(" ").__len__() > 0:
            sentences.append(str(post_obj.sentence4).strip(" "))
        if str(post_obj.sentence5).strip(" ").__len__() > 0:
            sentences.append(str(post_obj.sentence5).strip(" "))

        if str(post_obj.people1).strip(" ").__len__() > 0:
            keywords_dic["people"].append(str(post_obj.people1).strip(" "))
        if str(post_obj.people2).strip(" ").__len__() > 0:
            keywords_dic["people"].append(str(post_obj.people2).strip(" "))
        if str(post_obj.people3).strip(" ").__len__() > 0:
            keywords_dic["organization"].append(str(post_obj.people3).strip(" "))
        if str(post_obj.people4).strip(" ").__len__() > 0:
            keywords_dic["organization"].append(str(post_obj.people4).strip(" "))
        
        if not is_same:
            # import main_script as script
            # import SentimentAnalysisModels as sentiment_script
            response['sentences'] = sentences
            response['sentiments'] = sentiments  # sentiment_script.get_sentiment_result(sentences)
            # positive_score = 0.0
            # total_sentences = len(response['sentiments'])
            # score_per_positive = 100.0 / float(total_sentences)
            # for sentiment in response['sentiments']:
            #     if sentiment == "1":
            #         positive_score += score_per_positivess
            # post_obj.positive_score = positive_score
            # print(response['sentiments'], positive_score)
        else:
            response['sentences'] = older_sentences
            response['sentiments'] = older_sentiments
        
        response['people'] = keywords_dic['people']
        response['organization'] = keywords_dic['organization']
        
        response['people'] = prepare_wiki_data(request, response['people'])
        response['organization'] = prepare_wiki_data(request, response['organization'])
        print("==============================")
        print(response['people'])
        if len(response['people']) > 0:
            post_obj.people1 = response['people'][0]['keyword']
            response['people'][0]['follow_status'] = get_follow_status(user_obj, response['people'][0]['keyword'])
        if len(response['people']) > 1:
            post_obj.people2 = response['people'][1]['keyword']
            response['people'][1]['follow_status'] = get_follow_status(user_obj, response['people'][1]['keyword'])
        if len(response['organization']) > 0:
            post_obj.people3 = response['organization'][0]['keyword']
            response['organization'][0]['follow_status'] = get_follow_status(user_obj,
                                                                             response['organization'][0]['keyword'])
        if len(response['organization']) > 1:
            post_obj.people4 = response['organization'][1]['keyword']
            response['organization'][1]['follow_status'] = get_follow_status(user_obj,
                                                                             response['organization'][1]['keyword'])
        post_obj.json_response = json.dumps(response)
        post_obj.save()
        if not is_same:
            print("generated json", json.dumps(response))

    except Exception as e:
        print(str(e))
        # return HttpResponse(json.dumps(response))


def prepare_wiki_data(request, name_list):
    wiki_list_of_dics = []
    for name in name_list:
        query_keyword = ""
        people_name_tokens = str(name).strip(" ").split(" ")
        for keyword in people_name_tokens:
            if not keyword.isnumeric():
                query_keyword += keyword + "_"
        query_keyword = query_keyword.strip("_")
        with_space_query_keyword = query_keyword.replace("_", " ")
        wiki_object = WikiPedia.objects.filter(keyword__iexact=with_space_query_keyword).first()
        if not wiki_object:
            import parse_wiki as wiki
            wiki_dic = wiki.get_wiki_result_dic(query_keyword)
            print(wiki_dic)
            if not wiki_dic == {}:
                wiki_object = WikiPedia.objects.create(keyword=wiki_dic['keyword'])
                if 'description' in wiki_dic:
                    wiki_object.description = wiki_dic['description']
                if 'image_url' in wiki_dic:
                    wiki_object.image_url = wiki_dic['image_url']
                wiki_object.save()
                wiki_list_of_dics.append(wiki_dic)
                # time.sleep(0.5)
        else:
            wiki_dic = wiki_object.wiki_dic(request)
            print("Found from db", wiki_dic['keyword'])
            if not wiki_dic == {}:
                wiki_list_of_dics.append(wiki_dic)

    return wiki_list_of_dics


def Login(request):
    method = request.method
    if (method == 'POST'):
        return JsonResponse({'success': ""})
    else:
        return JsonResponse({'error': "This request only handles post request"})


def Signup(request):
    method = request.method
    if (method == 'POST'):
        # try:
        user = User.objects.create(
            username=request.POST['username'],
            first_name=request.POST['first_name'],
            last_name=request.POST['last_name'],
            email=request.POST['email'],
        )

        user.set_password(user['password'])
        user.save()
        return JsonResponse({'password': user['email']})
        # except:
        # return JsonResponse({'error': 'Something went wrong'})
    else:
        return JsonResponse({'error': "This request only handles post request"})


def sendVerificationEmail(request):
    method = request.method;
    if method == "POST":
        data = json.loads(request.body)
        email = data.get('email', 1)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.connect("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login('randomuser@gmail.com', 'jango/12345')
        server.sendmail('randomuser@gmail.com', email,
                        "Hi {email}, you are registered to news website.".format(email=email))
        server.quit()
        return JsonResponse({'success': True, 'message': "Email sent"});
    else:
        return JsonResponse({'error': 'Must be post method'})


def ForgetPassword(request):
    method = request.method
    if method == 'GET':
        return JsonResponse({'error': 'Must be get method'})
    email = request.GET.get('email', 1)
    if email == 1 or email == '':
        return JsonResponse({'message': 'Email is required'})
    print(email)
    token = ''.join(random.sample(string.ascii_uppercase + string.digits * 4, 4))
    forgetPasswordInstance = ForgetPasswordModel.objects.create()
    forgetPasswordInstance.email = email
    forgetPasswordInstance.token = token
    forgetPasswordInstance.save()
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.connect("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login('randomuser@gmail.com', 'jango/12345')
    server.sendmail('randomuser@gmail.com', email, "Hey, use {token} to reset your password.".format(token=token))
    server.quit()
    return JsonResponse({'success': 'true', 'message': 'Email has been sent to the requested email'})


def ResetPassword(request):
    method = request.method
    if method == 'GET':
        return JsonResponse({'message': 'Must be get method'})
    data = json.loads(request.body)
    token = data.get('token', 1)
    password = data.get('password', 1)
    confirm_password = data.get('confirm_password', 1)

    if token == 1 or password == 1 or confirm_password == 1:
        return JsonResponse({'message': 'Token, password, confirm_password are required'})
    if password != confirm_password:
        return JsonResponse({'message': 'Password does not matches'})
    # try:
    model = get_object_or_404(ForgetPasswordModel, token=token)
    if model.token == token:
        # change the password
        user = get_object_or_404(User, email=model.email)
        user.set_password(password)
        user.save()
        return JsonResponse({'message': 'Password changed'})
    else:
        return JsonResponse({'message': 'Token Expired'})
        # except:

        # if forget_password:
        # email = request.POST['token']
        # password = request.POST['password']
        # confirm_password = request.POST['confirm_password']
        # if password != confirm_password:
        #   return JsonResponse({'error': 'Password doesnot matches confirm password'})


@user_passes_test(lambda u: u.is_superuser)
def export_all_posts(request):
    if request.POST:
        file_rows = [
            ['title', 'username', 'author', 'category', 'source', 'author_description', 'main_sentence', 'sentence2',
             'sentence3', 'sentence4', 'people1', 'people2', 'people3', 'people4', 'json_response', 'embedded_image',
             'thumbnail_image', 'post_reaction_json', 'post_comments_json']]
        all_posts = []
        if 'email' in request.POST:
            email = str(request.POST['email']).strip(" ")
            saved_posts_list = SavedPost.objects.filter(user__username__iexact=email)
            if saved_posts_list:
                for saved_post in saved_posts_list:
                    all_posts.append(saved_post.post)
        else:
            all_posts = Post.objects.all()
        if all_posts:
            from io import StringIO
            f = StringIO()
            # with open("export_csv.csv", 'w') as myfile:
            #   wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
            for post_item in all_posts:
                reaction_json_dic = {"reactions": []}
                reactions_list = PostReaction.objects.filter(post=post_item)
                if reactions_list:
                    for reaction_item in reactions_list:
                        reaction_dic = {"reaction_type": reaction_item.reaction_type,
                                        "username": reaction_item.user.username}
                        reaction_json_dic['reactions'].append(reaction_dic)

                comment_json_dic = {"comments": []}
                comments_list = Comment.objects.filter(post=post_item)
                print("comments list", comments_list)
                if comments_list:
                    for comment_item in comments_list:
                        comment_dic = {"comment_text": comment_item.comment, "username": comment_item.user.username}
                        comment_json_dic['comments'].append(comment_dic)

                list_row = [post_item.title, post_item.user.username, post_item.author,
                            post_item.category, post_item.source, post_item.author_description,
                            post_item.main_sentence, post_item.sentence2, post_item.sentence3,
                            post_item.sentence4, post_item.people1, post_item.people2,
                            post_item.people3, post_item.people4, post_item.json_response,
                            post_item.embedded_image, post_item.thumbnail_image, reaction_json_dic, comment_json_dic]
                print(list_row)
                file_rows.append(list_row)
                # wr.writerow(list_row)
            print(file_rows)
            csv.writer(f).writerows(file_rows)
            # length = f.tell()
            f.flush()
            f.seek(0)
            response = HttpResponse(FileWrapper(f), content_type='text/csv')
            # response['Content-Length'] = length
            response['Content-Disposition'] = 'attachment; filename=all_posts_export.csv'
            # f.close()
            return response
            # wrapper = FileWrapper(open(template_path, 'rb'))
            # file_mimetype = mimetypes.guess_type(template_path)
            # response = HttpResponse(wrapper, content_type=file_mimetype)
            # response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(template_path)
            # response['Content-Length'] = os.path.getsize(template_path)
            # return response
    # return redirect("admin/api/post/") #render(request, 'export.html', {})
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# search block
def search(request):
    response = {'search_result': [], 'search_commentary_result': []}
    if request.method == 'POST':
        if 'query' in request.POST:
            query = str(request.POST['query']).strip(" ")
            print("Search Query", query)
            if query.__len__() > 2:
                trending_obj, created = TrendingSearch.objects.get_or_create(people_name=query.upper())
                trending_obj.total_count += 1
                trending_obj.save()
                # searched_posts_list = PeoplePostRelationship.objects.filter(people_name__icontains=query.lower()).order_by(
                #     '-id')
                query = query.lower()
                searched_posts_list = Post.objects. \
                                          filter(Q(title__icontains=query) | Q(main_sentence__icontains=query)
                                                 | Q(sentence2__icontains=query) | Q(sentence3__icontains=query)
                                                 | Q(sentence4__icontains=query) | Q(sentence5__icontains=query)
                                                 | Q(people1__icontains=query) | Q(people2__icontains=query)
                                                 | Q(people3__icontains=query) | Q(people4__icontains=query)
                                                 ).order_by('-id')[:50]
                if searched_posts_list:
                    for searched_post in searched_posts_list:
                        response['search_result'].append(searched_post.get_post_data_for_search(request))

                searched_commentary_list = Comment.objects. \
                                               filter((Q(comment__icontains=query) | Q(post__title__icontains=query)) & (Q(kind=1) | Q(kind=2))).order_by('-id')
                if searched_commentary_list:
                    for searched_commentary in searched_commentary_list:
                        group_comment = GroupComment.objects.filter(comment=searched_commentary).first()
                        if group_comment is None:
                            response['search_commentary_result'].append(
                                searched_commentary.get_info(request))
                        else:
                            print(group_comment.group.privacy)
                            if group_comment.group.privacy is True:
                                response['search_commentary_result'].append(
                                searched_commentary.get_info(request))
                            
    response['search_commentary_result'] = sorted(response['search_commentary_result'], key=lambda x:x['saved_at'], reverse=True) 
    # print("search", response)
    return HttpResponse(json.dumps(response))

def get_search_keywords(request):    
    query = request.GET.get('query')
    response = []
    trends = TrendingSearch.objects.filter(Q(people_name__icontains=query)).order_by('-id').values('people_name')
    for trend in trends:
        response.append(trend['people_name'])    
    if query:
        posts = Post.objects.filter((Q(title__icontains=query))).values('title')
        for post in posts:
            response.append(post['title'])
        groups = UserGroup.objects.filter(Q(name__icontains=query)).values('name')
        for group in groups:
            response.append(group['name'])        
    return HttpResponse(json.dumps(response[:10]))

def get_trending_search(request):
    response = []
    tending_list = TrendingSearch.objects.order_by('-total_count')[:10]
    if tending_list:
        for trend in tending_list:
            response.append(trend.people_name)
    return HttpResponse(json.dumps(response))


# end search block
def get_profile_owner_of_post(request):
    response = {}
    if request.method == 'POST':
        post_id = int(request.POST['post_id'])
        user_query = Post.objects.filter(id=post_id).select_related('user').first()
        if user_query:
            profile_obj = get_user_profile_obj(get_user_obj(request.POST['user']))
            visitor = Profile.objects.filter(user=user_query.user).first()
            if profile_obj:
                response = visitor.get_obj_dic(request)
                response['total_followers_count'] = Profile.objects.filter(following=visitor).count()
                response['follow_status'] = "Follow"
                if visitor in profile_obj.following.all():
                    response['follow_status'] = "Un-Follow"
    return HttpResponse(json.dumps(response))


# follow block

def follow_people(request):
    response = []
    if request.method == 'POST':
        # follow_status = "Follow"
        user_obj = get_user_obj(int(request.POST['user']))
        keyword = str(request.POST['keyword']).strip(" ")
        post_id = int(request.POST['post_id'])
        followed_obj = FollowedPeople.objects.filter(user=user_obj, people_name__iexact=keyword).first()
        if followed_obj:
            followed_obj.delete()
        else:
            followed_obj = FollowedPeople.objects.create(user=user_obj, people_name=keyword)
            followed_obj.save()
        response = get_follow_status_of_post(post_id, user_obj)
    return HttpResponse(json.dumps(response))


def get_follow_status_of_post(post_id, user_obj):
    response = {"people": [], "organization": []}
    post_instance = Post.objects.filter(id=post_id).first()
    people_list = []
    organization_list = []
    people_1 = str(post_instance.people1).strip(" ")
    if people_1.__len__() > 0:
        people_list.append(people_1)
    people_2 = str(post_instance.people2).strip(" ")
    if people_2.__len__() > 0:
        people_list.append(people_2)
    people_3 = str(post_instance.people3).strip(" ")
    if people_3.__len__() > 0:
        organization_list.append(people_3)
    people_4 = str(post_instance.people4).strip(" ")
    if people_4.__len__() > 0:
        organization_list.append(people_4)

    for keyword in people_list:
        response["people"].append(get_follow_status(user_obj, keyword))
    for keyword in organization_list:
        response["organization"].append(get_follow_status(user_obj, keyword))
    return response


def get_posts_people_follow_status(request):
    response = []
    if request.method == 'POST':
        user_obj = get_user_obj(int(request.POST['user']))
        post_id = int(request.POST['post_id'])
        response = get_follow_status_of_post(post_id, user_obj)
        print("get_posts_people_follow_status", response)
    return HttpResponse(json.dumps(response))


def get_follow_status(user_obj, keyword):
    follow_status = "Follow"
    if user_obj:
        keyword = str(keyword).strip(" ")
        followed_obj = FollowedPeople.objects.filter(user=user_obj, people_name__iexact=keyword).first()
        if followed_obj:
            follow_status = "Un-follow"
        total_followed_list = FollowedPeople.objects.filter(people_name__iexact=keyword)
        if total_followed_list and len(total_followed_list) > 0:
            follow_status += get_follow_number(len(total_followed_list))
    return follow_status


def get_follow_number(count):
    follow_num = " (" + str(count) + ")"
    if count >= 1000:
        follow_num = " (" + str(round(float(count) / 1000.0, 3)) + "K)"
    return follow_num


# end follow block


# user profile block
def follow_user(request):
    response = {"id": -1, "follow_status": ""}
    if request.method == 'POST':
        auth_user = get_user_obj(int(request.POST['user']))
        view_user = get_user_obj(int(request.POST['user_view']))
        response["id"] = int(request.POST['user_view'])
        visitor_profile = get_user_profile_obj(view_user)
        auth_profile = get_user_profile_obj(auth_user)
        print(request.POST['user'], request.POST['user_view'])
        if auth_user != view_user:
            if visitor_profile not in auth_profile.following.all():
                auth_profile.following.add(visitor_profile)
                response["follow_status"] = "Un-follow"
            else:
                if auth_profile.pinned_profile == visitor_profile:
                    auth_profile.pinned_profile = None
                    auth_profile.save()
                auth_profile.following.remove(visitor_profile)
                response["follow_status"] = "Follow"
            response['total_followers_count'] = Profile.objects.filter(following=visitor_profile).count()
    return HttpResponse(json.dumps(response))

def exists_profile_uid(request):
    profile = Profile.objects.filter(id=request.GET.get('id')).first()
    response = {'uID':request.GET.get('uID')}
    if Profile.objects.filter(uID=request.GET.get('uID')).count() > 0:
        response['uID'] = profile.uID
    return HttpResponse(json.dumps(response))

def get_profile_content(request):
    response = {"following_profiles": [], "following_keywords": [],"visitor_profile_info":{},
                "saved_posts": [], "my_posts": [], "total_followers_count": 0,
                "total_view_count": 0}
    print("profile content")
    if request.method == 'POST':
        is_own_profile = False
        auth_user = get_user_obj(int(request.POST['user']))
        view_user = get_user_obj(int(request.POST['user_view']))
        visitor_profile = get_user_profile_obj(view_user)
        auth_profile = get_user_profile_obj(auth_user)
        print(visitor_profile.name, auth_profile.name)
        if auth_user == view_user:
            is_own_profile = True

        # getting current profile following status
        if not is_own_profile:
            follow_status = "Follow"
            if visitor_profile in auth_profile.following.all():
                follow_status = "Un-follow"
            response['follow_status'] = follow_status        
            response['visitor_profile_info'] = visitor_profile.get_obj_dic(request)

        # getting total followers count
        response['total_followers_count'] = Profile.objects.filter(following=visitor_profile).count()
        response['total_view_count'] = visitor_profile.total_views

        # incrementing total views on profile
        if not is_own_profile:
            visitor_profile.total_views += 1
            visitor_profile.save()

        if is_own_profile or visitor_profile.show_profile_keywords:
            # getting following_profiles content
            all_following_profiles = visitor_profile.following.all()
            if all_following_profiles:
                for profile in all_following_profiles:
                    profile_dic = profile.get_obj_dic(request)
                    if is_own_profile:
                        if visitor_profile.pinned_profile == profile:
                            profile_dic['pinned'] = True
                        else:
                            profile_dic['pinned'] = False
                        profile_dic["follow_status"] = "Un-follow"
                    if visitor_profile.pinned_profile == profile:
                        response['following_profiles'].insert(0, profile_dic)
                    else:
                        response['following_profiles'].append(profile_dic)

        # getting saved post content
        if is_own_profile or visitor_profile.show_commentary_articles:
            all_saved_posts = SavedPost.objects.filter(user=view_user).order_by('-id')
            if all_saved_posts:
                for saved_post in all_saved_posts:
                    new_save_post_dic = saved_post.get_saved_post_data_for_profile(request)
                    if is_own_profile:
                        if visitor_profile.pinned_commentary == saved_post:
                            new_save_post_dic['pinned'] = True
                        else:
                            new_save_post_dic['pinned'] = False
                    vote_save_obj = VoteSavedPost.objects.filter(saved_post=saved_post, user=auth_user).first()
                    if vote_save_obj:
                        new_save_post_dic["like_status"] = "like"
                    else:
                        new_save_post_dic["like_status"] = "unlike"
                    if visitor_profile.pinned_commentary == saved_post:
                        response['saved_posts'].insert(0, new_save_post_dic)
                    else:
                        response['saved_posts'].append(new_save_post_dic)


        if is_own_profile or visitor_profile.show_commentary_articles:
            # getting my posts content
            all_my_posts = Post.objects.filter(user=view_user).order_by('-id')
            if all_my_posts:
                for my_post in all_my_posts:
                    new_my_post_post_dic = my_post.get_post_data_for_profile(request)
                    if is_own_profile:
                        if visitor_profile.pinned_article == my_post:
                            new_my_post_post_dic['pinned'] = True
                        else:
                            new_my_post_post_dic['pinned'] = False
                    if visitor_profile.pinned_article == my_post:
                        response['my_posts'].insert(0, new_my_post_post_dic)
                    else:
                        response['my_posts'].append(new_my_post_post_dic)

        if is_own_profile or visitor_profile.show_profile_keywords:
            # getting followed keywords
            all_followed_keywords = FollowedPeople.objects.filter(user=view_user)
            if all_followed_keywords:
                for followed_keyword in all_followed_keywords:
                    should_alert = False
                    followed_keyword_dic = {'keyword': followed_keyword.people_name, 'alert': should_alert}
                    if is_own_profile:
                        people_post_item = PeoplePostRelationship.objects.filter(
                            people_name__icontains=followed_keyword.people_name).order_by('-id').first()
                        if people_post_item:
                            already_viewed = UserPostViewed.objects.filter(user=view_user,
                                                                           post_id=people_post_item.post_id).first()
                            if not already_viewed:
                                followed_keyword_dic['alert'] = True
                    response['following_keywords'].append(followed_keyword_dic)
    # print(json.dumps(response))
    
    return HttpResponse(json.dumps(response))


# end user profile

# start home page
def get_top_stories(request):
    response = {'top_stories': {"1": None,
                                "2": None, "3": None,
                                "4": None, "5": None,
                                "6": None, "7": None,
                                "8": None,
                                }
                }
    if request.method == 'POST':
        fixed_stories = TopStories.objects.all()
        fixed_posts_list = []
        for fix_story in fixed_stories:
            response["top_stories"][fix_story.position_number] = fix_story.post_id.get_post_data_for_search(request)
            fixed_posts_list.append(fix_story.post_id)

        user_id = int(request.POST['user'])
        if user_id != -1:
            user_obj = get_user_obj(user_id)
            if user_obj:
                top_stories_list = calculate_top_stories(user_obj, fixed_posts_list, 4)
                print("top_stories_list", top_stories_list)
                for top_story in top_stories_list:
                    for key, value in response["top_stories"].items():
                        if value is None:
                            response["top_stories"][key] = top_story.get_post_data_for_search(request)
                            break
    print("top_stories", response)
    return HttpResponse(json.dumps(response))


def get_home_posts(request):
    response = []
    category = request.GET.get('category')
    if category:        
        date_from = timezone.now() - timezone.timedelta(days=30)
        posts_list = Post.objects.filter(category__icontains=category).order_by('-total_views')
        for post_item in posts_list:
            if get_user_profile_obj(post_item.user).verified:
                response.append(post_item.get_post_data_for_search(request))
    response = response[:10]
    return HttpResponse(json.dumps(response))


# end home page

# notification
def get_notifications(request):
    response = {"new_notification": False, "notifications": []}
    if request.method == 'POST':
        user_obj = get_user_obj(int(request.POST['user']))
        profile_obj = get_user_profile_obj(user_obj)
        all_notifications = Notification.objects.filter(related_profile__in=[profile_obj]).order_by('-id')[:15]
        if all_notifications and len(all_notifications) > 0:
            for notification in all_notifications:
                data = {}
                main_url=''
                sub_url=''
                if notification.notification_type == "comment":
                    comment = Comment.objects.filter(id=notification.comment_id).first()
                    if comment:
                        data['user_name'] = comment.user.username
                        data['img_url'] = get_user_profile_obj(get_user_obj(comment.user.id)).image                  
                        if comment.kind == 3:                        
                            main_url = '/news-page/'
                            sub_url = '#articlecomment_{}_{}'.format(comment.post.id, notification.comment_id)
                            data['text'] = 'Commented your profile article'  
                            data['url'] = '{}{}{}'.format(main_url, user_obj.id, sub_url)
                        if comment.kind == 2:
                            main_url = '/news-page/'
                            sub_url = '#commentary_{}'.format(notification.comment_id)
                            data['text'] = 'Commented your article'  
                            data['url'] = '{}{}{}'.format(main_url, comment.user.id, sub_url)
                        if comment.kind == 1:
                            main_url = '/group/'
                            sub_url = '#commentary_{}'.format(notification.comment_id)  
                            data['text'] = 'Commented your article in his group'
                            data['url'] = '{}{}{}'.format(main_url, GroupComment.objects.filter(comment__id=notification.comment_id).first().group.id, sub_url)
                        if comment.kind == 0:
                            main_url = '/view/'
                            sub_url = '#comments_{}'.format(notification.comment_id) 
                            data['text'] = 'Commented your article'
                            data['url'] = '{}{}{}'.format(main_url, comment.post.id, sub_url)
                        data['saved_at'] = notification.saved_at.__str__()
                        response['notifications'].append(data)
                if notification.notification_type == "reply":
                    reply = CommentReply.objects.filter(id=notification.comment_id).first()
                    if reply:
                        data['user_name'] = reply.user.username
                        data['img_url'] = get_user_profile_obj(get_user_obj(reply.user.id)).image 
                        if reply.comment:     
                            if reply.comment.kind == 3:                        
                                main_url = '/news-page/'
                                sub_url = '#articlereply_{}_{}'.format(reply.comment.id, notification.comment_id)
                                data['text'] = 'Replied your profile article comment'  
                                data['url'] = '{}{}{}'.format(main_url, user_obj.id, sub_url)
                            if reply.comment.kind == 2:
                                main_url = '/news-page/'
                                sub_url = '#commentarycomment_{}_{}'.format(reply.comment.id, notification.comment_id)
                                data['url'] = '{}{}{}'.format(main_url, user_obj.id, sub_url)
                                data['text'] = 'Commented your profile commentary'  
                            if reply.comment.kind == 1:
                                main_url = '/group/'
                                sub_url = '#comment_{}_{}'.format(reply.comment.id, notification.comment_id)  
                                data['text'] = 'Commented your group commentary'
                                data['url'] = '{}{}{}'.format(main_url, GroupComment.objects.filter(comment__id=reply.comment.id).first().group.id, sub_url)
                            if reply.comment.kind == 0:
                                main_url = '/view/'
                                sub_url = '#reply_{}'.format(notification.comment_id)
                                data['url'] = '{}{}{}'.format(main_url, reply.comment.post.id, sub_url)
                                data['text'] = 'Replied your article comment'  
                        else:
                            if reply.replied_reply.comment.kind == 2:
                                main_url = '/news-page/'
                                sub_url = '#commentaryreply_{}_{}'.format(reply.replied_reply.comment.id, notification.comment_id)
                                data['url'] = '{}{}{}'.format(main_url, user_obj.id, sub_url)
                                data['text'] = 'Replied your profile comment'  
                            if reply.replied_reply.comment.kind == 1:
                                main_url = '/group/'
                                sub_url = '#reply_{}_{}'.format(reply.replied_reply.comment.id, notification.comment_id)  
                                data['text'] = 'Replied your group comment'
                                data['url'] = '{}{}{}'.format(main_url, GroupComment.objects.filter(comment=reply.replied_reply.comment).first().group.id, sub_url)
                        data['saved_at'] = notification.saved_at.__str__()
                        response['notifications'].append(data)
                if notification.notification_type == "upvote" or notification.notification_type == "downvote":
                    profile = Profile.objects.filter(id=notification.profile_id).first()
                    data['user_name'] = profile.user.username
                    data['img_url'] = profile.image  
                    if notification.comment_id == -1:
                        post = Post.objects.filter(id=notification.post_id)          
                        if post:               
                            main_url = '/news-page/'
                            sub_url = '#article_{}'.format(notification.post_id)
                            data['text'] = 'Downvoted your profile article'
                            if notification.notification_type == "upvote":
                                data['text'] = 'Upvoted your profile article'
                            data['url'] = '{}{}{}'.format(main_url, user_obj.id, sub_url)
                            data['saved_at'] = notification.saved_at.__str__()
                            response['notifications'].append(data)
                    else:
                        comment = Comment.objects.filter(id=notification.comment_id).first()
                        if comment:
                            if comment.kind == 1:
                                main_url = '/group/'
                                sub_url = '#commentary_{}'.format(notification.comment_id)  
                                data['text'] = 'Downvoted your group commentary'
                                if notification.notification_type == "upvote":
                                    data['text'] = 'Upvoted your group commentary'
                                data['url'] = '{}{}{}'.format(main_url, GroupComment.objects.filter(comment__id=notification.comment_id).first().group.id, sub_url)
                            if comment.kind == 2:
                                main_url = '/news-page/'
                                sub_url = '#commentary_{}'.format(notification.comment_id)   
                                data['text'] = 'Downvoted your profile commentary'
                                if notification.notification_type == "upvote":
                                    data['text'] = 'Upvoted your profile commentary'
                                data['url'] = '{}{}{}'.format(main_url, user_obj.id, sub_url)
                            data['saved_at'] = notification.saved_at.__str__()
                            response['notifications'].append(data)
                if notification.notification_type == "like" or notification.notification_type == "dislike":
                    profile = Profile.objects.filter(id=notification.profile_id).first()
                    data['user_name'] = profile.user.username
                    data['img_url'] = profile.image  
                    if notification.post_id == -1:
                        comment = Comment.objects.filter(id=notification.comment_id).first()     
                        if comment:                              
                            if comment.kind == 3:                        
                                main_url = '/news-page/'
                                sub_url = '#articlecomment_{}_{}'.format(comment.post.id, notification.comment_id)                            
                                data['text'] = 'Liked your profile article comment'  
                                if notification.notification_type == "dislike":
                                    data['text'] = 'Disliked your profile article comment' 
                                data['url'] = '{}{}{}'.format(main_url, user_obj.id, sub_url)
                            if comment.kind == 0:
                                main_url = '/view/'
                                sub_url = '#comments_{}'.format(notification.comment_id)
                                data['url'] = '{}{}{}'.format(main_url, comment.post.id, sub_url)
                                data['text'] = 'Liked your article comment'  
                                if notification.notification_type == "dislike":
                                    data['text'] = 'Disliked your article comment'  
                            data['saved_at'] = notification.saved_at.__str__()
                            response['notifications'].append(data)
                    elif notification.post_id == -2:
                        reply = CommentReply.objects.filter(id=notification.comment_id).first() 
                        if reply:                   
                            if reply.comment:   
                                if reply.comment.kind == 3:
                                    main_url = '/news-page/'
                                    sub_url = '#articlereply_{}_{}'.format(reply.comment.id, notification.comment_id)
                                    data['text'] = 'Liked your profile article comment reply'  
                                    if notification.notification_type == "dislike":
                                        data['text'] = 'Disliked your profile article comment reply'
                                    data['url'] = '{}{}{}'.format(main_url, user_obj.id, sub_url)
                                if reply.comment.kind == 2:                        
                                    main_url = '/news-page/'
                                    sub_url = '#commentarycomment_{}_{}'.format(reply.comment.id, notification.comment_id)
                                    data['text'] = 'Liked your profile commentary comment'  
                                    if notification.notification_type == "dislike":
                                        data['text'] = 'Disliked your profile commentary comment'
                                    data['url'] = '{}{}{}'.format(main_url, user_obj.id, sub_url)
                                elif reply.comment.kind == 1:
                                    main_url = '/group/'
                                    sub_url = '#comment_{}_{}'.format(reply.comment.id, notification.comment_id)  
                                    data['text'] = 'Liked your Group comment'  
                                    if notification.notification_type == "dislike":
                                        data['text'] = 'Disliked your Group comment'
                                    data['url'] = '{}{}{}'.format(main_url, GroupComment.objects.filter(comment__id=reply.comment.id).first().group.id, sub_url)
                                elif reply.comment.kind == 0:
                                    main_url = '/view/'
                                    sub_url = '#reply_{}'.format(notification.comment_id)
                                    data['text'] = 'Liked your article comment reply'  
                                    if notification.notification_type == "dislike":
                                        data['text'] = 'Disliked your article comment reply'
                                    data['url'] = '{}{}{}'.format(main_url, reply.comment.post.id, sub_url)
                            else:
                                if reply.replied_reply.comment.kind == 2:                        
                                    main_url = '/news-page/'
                                    sub_url = '#commentaryreply_{}_{}'.format(reply.comment.id, notification.comment_id)
                                    data['text'] = 'Liked your profile comment reply'  
                                    if notification.notification_type == "dislike":
                                        data['text'] = 'Disliked your profile comment reply'
                                    data['url'] = '{}{}{}'.format(main_url, user_obj.id, sub_url)
                                elif reply.replied_reply.comment.kind == 1:
                                    main_url = '/group/'
                                    sub_url = '#reply_{}_{}'.format(reply.replied_reply.comment.id, notification.comment_id)  
                                    data['text'] = 'Liked your Group comment reply'  
                                    if notification.notification_type == "dislike":
                                        data['text'] = 'Disliked your Group comment reply'
                                    data['url'] = '{}{}{}'.format(main_url, GroupComment.objects.filter(comment__id=reply.replied_reply.comment.id).first().group.id, sub_url)
                            data['saved_at'] = notification.saved_at.__str__()
                            response['notifications'].append(data)
                if notification.notification_type == "invite":
                    group = UserGroup.objects.filter(id=notification.comment_id).first()
                    data['user_name'] = '{} Group'.format(group.name)
                    data['img_url'] = '' 
                    data['text'] = 'You are invited!'
                    data['url'] = '/group/{}'.format(group.id)
                    data['saved_at'] = notification.saved_at.__str__()                    
                    data['img_url'] = group.thumbnail_image
                    response['notifications'].append(data)
            if profile_obj.last_notification_id != all_notifications[0].id:                
                response['new_notification'] = True

    return HttpResponse(json.dumps(response))

def check_notification(request):
    profile_obj = get_user_profile_obj(get_user_obj(request.GET.get('user')))
    all_notifications = Notification.objects.filter(related_profile__in=[profile_obj]).order_by('-id')[:15]
    profile_obj.last_notification_id = all_notifications[0].id
    profile_obj.save()
    return HttpResponse(json.dumps({'response':'ok'}))
# end notifiaction


# user profile
def update_profile_settings(request):
    response = {"show_profile_keywords": False, "show_commentary_articles": False}
    if request.method == 'POST':
        user_obj = get_user_obj(int(request.POST['user']))
        profile_obj = get_user_profile_obj(user_obj)
        show_profile_keywords = False
        if int(request.POST['show_profile_keywords']) == 1:
            show_profile_keywords = True
        show_commentary_articles = False
        if int(request.POST['show_commentary_articles']) == 1:
            show_commentary_articles = True
        show_articles_first = False
        if int(request.POST['show_articles_first']) == 1:
            show_articles_first = True
        profile_obj.show_profile_keywords = show_profile_keywords
        profile_obj.show_commentary_articles = show_commentary_articles
        profile_obj.show_articles_first = show_articles_first
        profile_obj.save()
        response = {"show_profile_keywords": show_profile_keywords,
                    "show_commentary_articles": show_commentary_articles,
                    "show_articles_first": show_articles_first}
    return HttpResponse(json.dumps(response))

def pin_commentary(request):
    response = {}
    if request.method == 'POST':
        user_obj = get_user_obj(int(request.POST['user']))
        profile_obj = get_user_profile_obj(user_obj)
        saved_post_id = int(request.POST['saved_post_id'])
        saved_post_obj = Comment.objects.filter(id=saved_post_id).first()
        if saved_post_obj:
            if profile_obj.pinned_commentary != saved_post_obj:
                profile_obj.pinned_commentary = saved_post_obj
            else:
                profile_obj.pinned_commentary = None
            profile_obj.save()
    return HttpResponse(json.dumps(response))

def pin_post(request):
    response = {}
    if request.method == 'POST':
        user_obj = get_user_obj(int(request.POST['user']))
        profile_obj = get_user_profile_obj(user_obj)
        post_id = int(request.POST['id'])
        post_obj = Post.objects.filter(id=post_id).first()
        if post_obj:
            if profile_obj.pinned_article != post_obj:
                profile_obj.pinned_article = post_obj
            else:
                profile_obj.pinned_article = None
            profile_obj.save()
    return HttpResponse(json.dumps(response))


def pin_group(request):
    response = {'groups':[]}
    if request.method == 'POST':
        user_obj = get_user_obj(int(request.POST['user']))
        profile_obj = get_user_profile_obj(user_obj)
        pinned_groups = profile_obj.pinned_groups.split(',')
        if request.POST['group']:
            if request.POST['group'] in pinned_groups:
                pinned_groups.remove(request.POST['group'])   
            else:
                if(len(pinned_groups) >= 3):
                    pinned_groups.pop(0)
                pinned_groups.append(request.POST['group'])    
        profile_obj.pinned_groups = ",".join(pinned_groups)            
        profile_obj.save()
        response['groups'] = pinned_groups
    return HttpResponse(json.dumps(response))



def pin_my_post(request):
    response = {}
    if request.method == 'POST':
        user_obj = get_user_obj(int(request.POST['user']))
        profile_obj = get_user_profile_obj(user_obj)
        post_id = int(request.POST['post_id'])
        post_obj = Post.objects.filter(id=post_id).first()
        if post_obj:
            if profile_obj.pinned_article != post_obj:
                profile_obj.pinned_article = post_obj
            else:
                profile_obj.pinned_article = None
            profile_obj.save()
    return HttpResponse(json.dumps(response))


def pin_following_profile(request):
    response = {}
    if request.method == 'POST':
        auth_user = get_user_obj(int(request.POST['user']))
        view_user = get_user_obj(int(request.POST['user_view']))
        visitor_profile = get_user_profile_obj(view_user)
        auth_profile = get_user_profile_obj(auth_user)
        if visitor_profile in auth_profile.following.all():
            if auth_profile.pinned_profile != visitor_profile:
                auth_profile.pinned_profile = visitor_profile
            else:
                auth_profile.pinned_profile = None
            auth_profile.save()
    return HttpResponse(json.dumps(response))
    # end user profile


def like_commentary(request):
    response = {"like_status": "unlike", "like_count": 0}
    if request.method == 'POST':
        user_obj = get_user_obj(int(request.POST['user']))
        profile_obj = get_user_profile_obj(user_obj)
        saved_post_id = int(request.POST['saved_post_id'])
        saved_post_obj = SavedPost.objects.filter(id=saved_post_id).first()
        if saved_post_obj:
            vote_save_obj = VoteSavedPost.objects.filter(saved_post=saved_post_obj, user=user_obj).first()
            if vote_save_obj:
                vote_save_obj.delete()
                response["like_status"] = "unlike"
            else:
                vote_save_obj = VoteSavedPost.objects.create(saved_post=saved_post_obj, profile=profile_obj,
                                                             user=user_obj)
                if vote_save_obj:
                    response["like_status"] = "like"
            response['like_count'] = VoteSavedPost.objects.filter(saved_post=saved_post_obj).count()
    return HttpResponse(json.dumps(response))

def get_group_count_by_user(request):
    response = {"count": 0}
    if request.method == "GET":
        response['count'] = UserGroup.objects.filter(users__id=request.GET.get('user')).count()
    return HttpResponse(json.dumps(response))

def search_invite_users(request):
    response = []
    group = UserGroup.objects.filter(id=request.GET.get('group')).first()
    for profile in Profile.objects.filter(uID__contains=request.GET.get('query')).all():
        if not profile.user in group.users.all():         
            if(profile.uID): 
                data = {'id': profile.user.id, 'uID': profile.uID}
                response.append(data)
    return HttpResponse(json.dumps(response))

def add_users_to_group(request):
    group = UserGroup.objects.filter(id=request.POST['group']).first()
    for user in request.POST['users'].split(","):
        group.users.add(get_user_obj(int(user)))
        related_profiles = get_user_profile_obj(get_user_obj(int(user)))
        if related_profiles: 
            notification = Notification.objects.create(
                notification_type=Notification.Notification_Type_Invite)
            if notification:
                notification.related_profile.add(related_profiles)
                notification.comment_id = int(request.POST['group'])
                notification.save()
    return HttpResponse(json.dumps({'success':True}))

def get_groups_by_user(request):
    response = []
    if request.method == "GET":
        groups = UserGroup.objects.filter(users__id=request.GET.get('user')).all()
        for group in groups:
            data = {}
            data['id'] = group.id
            data['name'] = group.name
            data['description'] = group.description
            data['visible'] = group.visible
            data['privacy'] = group.privacy
            data['image'] = ''
            data['alert'] = 'none'
            if group.last_comment_id != GroupComment.objects.filter(group=group).count():
                data['alert'] = 'new' 
            data['image'] = group.thumbnail_image
            response.append(data)
    return JsonResponse({'groups': list(response)})

def check_group_alert(request):
    group = UserGroup.objects.filter(id=request.GET.get('group')).first()
    if group:
        group.last_comment_id = GroupComment.objects.filter(group=group).count()
        group.save()
    return JsonResponse({'success': 'ok'})

def get_all_groups(request):
    groups = []
    if request.method == "GET":
        for group in UserGroup.objects.all() :
            g = UserGroup.objects.filter(id=int(group.id)).values('id', 'name', 'description', 'privacy', 'visible')
            data = g[0]
            data['image'] = group.thumbnail_image
            data['members'] = UserGroup.objects.filter(id=int(group.id)).first().users.count()
            data['creator'] = UserGroup.objects.filter(id=int(group.id)).first().creator.id
            posts = 0
            data['joined'] = False
            for user in UserGroup.objects.filter(id=int(group.id)).first().users.all():
                if(user.id == int(request.GET.get('user'))):
                    data['joined'] = True
                posts += SavedPost.objects.filter(user=user).order_by('-id').count()
            data['posts'] = posts
            groups.append(data)
    return JsonResponse({'groups': list(groups)})

def search_group_by_name(request):
    groups = []
    if request.method == "GET":        
        for group in UserGroup.objects.filter(name='pp').all():
            g = UserGroup.objects.filter(id=int(group.id)).values('id', 'name', 'description', 'privacy', 'visible')
            data = g[0]
            data['members'] = UserGroup.objects.filter(id=int(group.id)).first().users.count()
            data['creator'] = UserGroup.objects.filter(id=int(group.id)).first().creator.id
            posts = 0
            data['joined'] = False
            for user in UserGroup.objects.filter(id=int(group.id)).first().users.all():
                if(user.id == int(request.GET.get('user'))):
                    data['joined'] = True
                posts += SavedPost.objects.filter(user=user).order_by('-id').count()
            data['posts'] = posts
            groups.append(data)
    return JsonResponse({'groups': list(groups)})

def get_group_feeds_by_user(request):
    response = {'feeds': []}
    if request.method == "GET":
        for group in UserGroup.objects.filter(users__id=request.GET.get('user')).all():            
            for element in GroupComment.objects.filter(group__id=int(group.id)).all():
                data = {}
                data['id'] = element.id
                data['user_name'] = Profile.objects.filter(user=element.comment.user).first().name
                data['user_avatar'] = Profile.objects.filter(user=element.comment.user).first().image
                data['comment'] = element.comment.comment
                data['comment_id'] = element.comment.id
                data['comment_time'] = element.comment.created_at.__str__()
                data['post_author'] = element.comment.post.author
                data['post_user'] = get_user_profile_obj(user=element.comment.post.user).name
                data['post_id'] = element.comment.post.id
                data['creator_id'] = element.comment.user.id
                data['post_title'] = element.comment.post.title
                if element.comment.post.thumbnail_image:
                    data['post_avatar'] = 'http://'+request.get_host()+element.comment.post.thumbnail_image.url
                else :
                    data['post_avatar'] = ''
                data['post_views'] = element.comment.post.total_views
                data['post_time'] = element.comment.post.created_at.__str__()
                data['votes'] = VoteComment.objects.filter(comment=element.comment).count()
                data['like'] = 'like'
                if VoteComment.objects.filter(user=User.objects.filter(id=request.GET.get('user')).first(), comment=element.comment).count() > 0:
                    data['like'] = 'dislike'
                data['group_id'] = group.id    
                data['group_name'] = group.name   
                data['group_creator'] = group.creator.id   
                data['group_image'] = group.thumbnail_image
                data['pinned'] = 'unpinned'
                if (int(element.group.pinned_commentaries) if element.group.pinned_commentaries else -1) == int(element.comment.id):
                  data['pinned'] = 'pinned'
                response['feeds'].append(data)
    response['feeds'] = sorted(response['feeds'], key=lambda x:x['comment_time'], reverse=True)           
    return HttpResponse(json.dumps(response))

def get_group_feeds_by_group(request):
    response = {'feeds': []}
    if request.method == "GET":          
        group = UserGroup.objects.filter(id=request.GET.get('group')).first()
        for element in GroupComment.objects.filter(group__id=request.GET.get('group')).all():
            data = {}
            data['id'] = element.comment.post.id
            data['user_name'] = Profile.objects.filter(user=element.comment.user).first().name
            data['user_avatar'] = Profile.objects.filter(user=element.comment.user).first().image
            data['comment'] = element.comment.comment
            data['comment_id'] = element.comment.id
            data['creator_id'] = element.comment.user.id
            data['total_comments'] = Comment.objects.filter(post=element.comment.post).count()
            data['comment_time'] = element.comment.created_at.__str__()
            data['post_id'] = element.comment.post.id
            data['post_author'] = element.comment.post.author
            data['post_user'] = get_user_profile_obj(user=element.comment.post.user).name
            data['post_title'] = element.comment.post.title
            if element.comment.post.thumbnail_image:
                data['post_avatar'] = 'http://'+request.get_host()+element.comment.post.thumbnail_image.url
            else :
                data['post_avatar'] = ''
            data['post_views'] = element.comment.post.total_views
            data['post_time'] = element.comment.post.created_at.__str__()
            data['votes'] = VoteComment.objects.filter(comment=element.comment).count()
            data['like'] = 'like'
            if VoteComment.objects.filter(user=User.objects.filter(id=request.GET.get('user')).first(), comment=element.comment).count() > 0:
                data['like'] = 'dislike'
            data['post_time'] = element.comment.post.created_at.__str__()
            data['group_id'] = group.id    
            data['group_name'] = group.name   
            data['group_creator'] = group.creator.id
            data['group_image'] = group.thumbnail_image
            data['pinned'] = 'unpinned'
            if (int(element.group.pinned_commentaries) if element.group.pinned_commentaries else -1) == int(element.comment.id):
                data['pinned'] = 'pinned'
                    
            response['feeds'].append(data)
    response['feeds'] = sorted(response['feeds'], key=lambda x:x['comment_time'], reverse=True)           
    return HttpResponse(json.dumps(response))

def get_saved_comments_by_user(request):
    response = {'comments': []}
     
    if request.method == "GET":          
        pinned_data = {}
        for comment in Comment.objects.filter(user__id=request.GET.get('user'), kind=2).all():
            data = {}
            data['id'] = comment.post.id
            data['user_name'] = Profile.objects.filter(user=comment.user).first().name
            data['user_avatar'] = Profile.objects.filter(user=comment.user).first().image
            data['comment'] = comment.comment
            data['comment_id'] = comment.id
            data['creator_id'] = comment.user.id
            data['total_comments'] = Comment.objects.filter(post=comment.post).count()
            data['comment_time'] = comment.created_at.__str__()
            data['post_id'] = comment.post.id
            data['post_author'] = comment.post.author
            data['post_user'] = get_user_profile_obj(user=comment.post.user).name
            data['post_title'] = comment.post.title
            if comment.post.thumbnail_image:
                data['post_avatar'] = 'http://'+request.get_host()+comment.post.thumbnail_image.url
            else :
                data['post_avatar'] = ''
            data['post_views'] = comment.post.total_views
            data['post_time'] = comment.post.created_at.__str__()
            data['votes'] = VoteComment.objects.filter(comment=comment).count()
            data['like'] = 'like'
            if VoteComment.objects.filter(user=User.objects.filter(id=request.GET.get('user')).first(), comment=comment).count() > 0:
                data['like'] = 'dislike'
            data['group_id'] = -1    
            data['group_name'] = ""   
            data['group_creator'] = -1  
            if get_user_profile_obj(get_user_obj(request.GET.get('user'))).pinned_commentary == comment:
                data['pinned'] = 'pinned'
                pinned_data = data
            else:        
                data['pinned'] = 'unpinned'
                response['comments'].append(data)
    response['comments'] = sorted(response['comments'], key=lambda x:x['comment_time'], reverse=True)    
    if pinned_data:
        response['comments'].insert(0, pinned_data)       
    return HttpResponse(json.dumps(response))

def get_posts_by_user(request):
    response = {'posts': []}
    if request.method == "GET":  
        pinned_data = {}
        for post in Post.objects.filter(user__id=request.GET.get('user')).all():
            data = {}
            data['id'] = post.id
            data['comment_id'] = -1
            data['post_id'] = post.id
            data['user_name'] = Profile.objects.filter(user__id=request.GET.get('user')).first().name
            data['user_avatar'] = Profile.objects.filter(user__id=request.GET.get('user')).first().image
            data['post_author'] = post.author
            data['post_title'] = post.title
            if post.thumbnail_image:
                data['post_avatar'] = 'http://'+request.get_host()+post.thumbnail_image.url
            else :
                data['post_avatar'] = ''
            data['post_views'] = post.total_views
            data['post_time'] = post.created_at.__str__()
            data['votes'] = PostVote.objects.filter(post=post).count()
            data['like'] = 'like'
            if PostVote.objects.filter(user=User.objects.filter(id=request.GET.get('user')).first(), post=post).count() > 0:
                data['like'] = 'dislike'
            if get_user_profile_obj(get_user_obj(request.GET.get('user'))).pinned_article == post:
                data['pinned'] = 'pinned'
                pinned_data = data
            else:        
                data['pinned'] = 'unpinned'
                response['posts'].append(data)
        response['posts'] = sorted(response['posts'], key=lambda x:x['post_time'], reverse=True)    
        if pinned_data:
            response['posts'].insert(0, pinned_data)       
    return HttpResponse(json.dumps(response))

def remove_group_feed_by_id(request):
    response = {'success': False}
    if request.method == "GET":
        comment = Comment.objects.filter(id=request.GET.get('comment')).first()
        GroupCommentary.objects.filter(post=comment.post, user=comment.user, comment=comment.comment).delete()
        GroupComment.objects.filter(comment=comment).delete()
        comment.delete() 

    return HttpResponse(json.dumps(response))
def get_all_posts(request):
    response = {'posts': []}        
    for post in Post.objects.all():
        if get_user_profile_obj(post.user).verified:
            post = post.get_post_data_for_profile(request) 
            response['posts'].append(post)
    response['posts'] = sorted(response['posts'], key=lambda x:x['created_at'], reverse=False) 
    return HttpResponse(json.dumps(response))

def get_group_posts_by_group(request):
    response = {'posts': []}
    if request.method == "GET":
        for user in UserGroup.objects.filter(id=request.GET.get('group')).first().users.all():
            all_posts = Post.objects.filter(user=user).order_by('-id')
            if all_posts:
                for post in all_posts:
                    post = post.get_post_data_for_profile(request)  
                    response['posts'].append(post)
    response['posts'] = sorted(response['posts'], key=lambda x:x['created_at'], reverse=False)           
    return HttpResponse(json.dumps(response))

def add_pin_to_group(request):
    response = {'success': False}
    if request.method == "POST":
        group = UserGroup.objects.filter(id=request.POST['group']).first()
        if (int(group.pinned_commentaries) if group.pinned_commentaries else -1) == int(request.POST['comment']):
            group.pinned_commentaries = ""
        else:
            print(request.POST['comment'])
            group.pinned_commentaries = request.POST['comment']        
        group.save()
    return HttpResponse(json.dumps(response))

def create_new_group(request):
    response = {'success': False}
    if request.method == "POST":
        user_obj = get_user_obj(int(request.POST['user']))
        print(request.POST['privacy'])
        group = UserGroup(name=request.POST['name'], description=request.POST['description'], privacy=request.POST['privacy']=='true', visible=request.POST['visible']=='true', creator=user_obj)
        group.save()
        group.users.add(user_obj)
        response['success'] = True
    return HttpResponse(json.dumps(response))

def get_groupinfo_by_id(request):
    response = {'group':{}}
    if request.method == "GET":
        group = UserGroup.objects.filter(id=request.GET.get('group')).first()
        response['group']['id'] = group.id
        response['group']['name'] = group.name
        response['group']['description'] = group.description
        response['group']['privacy'] = group.privacy
        response['group']['visible'] = group.visible
        response['group']['members'] = group.users.count()
        response['group']['creator'] = group.creator.id        
        posts = 0
        for user in group.users.all():
             posts += Post.objects.filter(user=user).order_by('-id').count()
        response['group']['posts'] = posts
        response['group']['image'] = group.thumbnail_image
    return HttpResponse(json.dumps(response))

def get_all_groupinfo(request):
    response = {'groups':[]}
    if request.method == "GET":
        for group in UserGroup.objects.all():
            data = {}
            data['id'] = group.id
            data['name'] = group.name
            data['description'] = group.description
            data['members'] = group.users.count()
            posts = 0
            for user in group.users.all():
                posts += SavedPost.objects.filter(user=user).order_by('-id').count()
            data['posts'] = posts
            response['groups'].append(data)
    response['groups'] = sorted(response['groups'], key=lambda x:x['posts'], reverse=True)
    response['groups'] = response['groups'][0:30]
    return HttpResponse(json.dumps(response))

def add_comment(request):  
    post = Post.objects.filter(id=int(request.POST['post'])).first()
    user_id = int(request.POST['user'])
    comment = Comment(post=post, user=User.objects.filter(id=user_id).first(), comment=request.POST['comment'], kind=request.POST['kind'])
    comment.save()
    print(comment.kind)
    if int(comment.kind) == 2:
        pro = ProfileCommentary(post=comment.post, user=comment.user, comment=comment.comment)
        pro.save(recursive=False)
    if(post.user.id != user_id):
        notification = Notification.objects.create(
            notification_type=Notification.Notification_Type_Comment)
        if notification:
            related_profile_obj = get_user_profile_obj(get_user_obj(post.user.id))
            activity_profile_obj = get_user_profile_obj(get_user_obj(user_id))
            notification.related_profile.add(related_profile_obj)
            notification.profile_id = activity_profile_obj.id
            notification.comment_id = comment.id
            notification.post_id = request.POST['post']
            notification.save()    

    response={'comment': comment.id}
    return HttpResponse(json.dumps(response))
def add_reply(request):
    reply = CommentReply(comment=Comment.objects.filter(id=int(request.POST['comment'])).first(), reply=request.POST['reply'], user=User.objects.filter(id=int(request.POST['user'])).first())
    reply.save()
    response={'reply': reply.id}
    return HttpResponse(json.dumps(response))

def vote_comment(request):
    response = {"like_status": "unlike", "like_count": 0}
    if request.method == 'POST':
        user_obj = get_user_obj(int(request.POST['user']))
        comment_obj = Comment.objects.filter(id=int(request.POST['comment'])).first()
        if comment_obj:
            vote_save_obj = VoteComment.objects.filter(comment=comment_obj, user=user_obj).first()
            notification_type = Notification.Notification_Type_Upvote
            if vote_save_obj:
                notification_type = Notification.Notification_Type_Downvote
                vote_save_obj.delete()
                response["like_status"] = "like"
            else:
                vote_save_obj = VoteComment.objects.create(comment=comment_obj, user=user_obj)
                if vote_save_obj:
                    response["like_status"] = "unlike"
            response['id'] = comment_obj.id
            response['like_count'] = VoteComment.objects.filter(comment=comment_obj).count()
            if(comment_obj.user.id != user_obj.id):
                notification = Notification.objects.create(
                notification_type=notification_type)
                if notification:
                    related_profile_obj = get_user_profile_obj(comment_obj.user)
                    activity_profile_obj = get_user_profile_obj(user_obj)
                    notification.related_profile.add(related_profile_obj)
                    notification.profile_id = activity_profile_obj.id
                    notification.comment_id = comment_obj.id
                    notification.post_id = comment_obj.post.id
                    notification.save()    
    return HttpResponse(json.dumps(response))

def vote_post(request):
    response = {"like_status": "unlike", "like_count": 0}
    if request.method == 'POST':
        user_id = int(request.POST['user'])
        user_obj = get_user_obj(user_id)
        post_obj = Post.objects.filter(id=int(request.POST['post'])).first()
        if post_obj:
            vote_save_obj = PostVote.objects.filter(post=post_obj, user=user_obj).first()
            
            if vote_save_obj:
                vote_save_obj.delete()
                response["like_status"] = "like"                
            else:
                vote_save_obj = PostVote.objects.create(post=post_obj, user=user_obj)
                if vote_save_obj:
                    response["like_status"] = "unlike"            
            response['id'] = post_obj.id
            response['like_count'] = PostVote.objects.filter(post=post_obj).count()
            if user_id != post_obj.user.id:
                related_profile_obj = get_user_profile_obj( post_obj.user)
                notification_type=Notification.Notification_Type_Downvote
                if response["like_status"] == "unlike":
                    notification_type=Notification.Notification_Type_Upvote            
                notification = Notification.objects.create(
                        notification_type=notification_type)
                if notification:
                    activity_profile_obj = get_user_profile_obj(get_user_obj(user_id))
                    notification.related_profile.add(related_profile_obj)
                    notification.profile_id = activity_profile_obj.id
                    notification.post_id = int(request.POST['post'])
                    notification.save()
    return HttpResponse(json.dumps(response))    

def get_saved_comments_by_post(request):
    response = []
    comments = Comment.objects.filter(post__id=int(request.GET.get('post')),kind=3).all()
    for comment in comments:
        data = {}
        data['id'] = comment.id
        data['comment'] = comment.comment
        data['user'] = comment.user.id
        data['created_at'] = comment.created_at.__str__()
        response.append(data)
    return HttpResponse(json.dumps(response))
def get_total_commments_count(request):
    response = {'total': 0}
    kind = 0
    if request.GET.get('kind'):
        kind = request.GET.get('kind')
    comments = Comment.objects.filter(post__id=int(request.GET.get('post')), kind=kind).all()
    for comment in comments:
        response['total'] += (CommentReply.objects.filter(comment=comment).count() + 1)
    return HttpResponse(json.dumps(response))

def get_comment_replies_by_comment(request):
    response = []
    replies = CommentReply.objects.filter(comment__id=int(request.GET.get('comment'))).all()
    for reply in replies:
        data = {}
        data['reply'] = reply.reply
        data['created_at'] = reply.created_at.__str__()
        data['user'] = reply.user.id
        data['id'] = reply.id
        response.append(data)
    return HttpResponse(json.dumps(response))

def get_total_replies_count(request):
    response = {'total':0}
    replies = CommentReply.objects.filter(comment__id=int(request.GET.get('comment'))).all()
    for reply in replies:
        response['total'] += (CommentReply.objects.filter(replied_reply=reply).count() + 1)
    return HttpResponse(json.dumps(response))

def add_group_comment(request):
    response = {'success': False}
    if request.method == "POST":
        print(request.path)
        post = Post.objects.filter(id=int(request.POST['post'])).first()
        user = User.objects.filter(id=int(request.POST['user'])).first()
        for group in request.POST['groups'].split(','):            
            group=UserGroup.objects.filter(id=int(group)).first()
            comment = Comment(post=post, user=user, comment=request.POST['comment'],kind=1)
            comment.save()
            row = GroupComment(comment=comment, group=group)
            row.save()
            commentary = GroupCommentary(post=post, user=user, comment=request.POST['comment'], group=group)
            commentary.save(recursive=False)
            if comment.user.id != comment.post.user.id:
                related_profiles = get_user_profile_obj(comment.post.user)
                if related_profiles: 
                    notification = Notification.objects.create(
                        notification_type=Notification.Notification_Type_Comment)
                    if notification:
                        notification.related_profile.add(related_profiles)
                        notification.profile_id = get_user_profile_obj(comment.user).id
                        notification.comment_id = comment.id
                        notification.save()
        response['success'] = True  
    return HttpResponse(json.dumps(response))
def add_group_photo(request):
    print(request.POST['file'])    
    group = UserGroup.objects.filter(id=request.POST['group']).first()
    group.thumbnail_image = request.POST['file']
    group.save()
    return HttpResponse(json.dumps({'response':'ok'}))

def join_group(request):
    response = {'success': False}
    if request.method == "GET":        
        group = UserGroup.objects.filter(id=request.GET.get('group')).first()   
        # if group.users.filter(id=request.GET.get('user')).count() == 0:  
    
        user = get_user_obj(request.GET.get('user'))   
        group.users.add(user)
        response['success'] = True
    return HttpResponse(json.dumps(response))

def unjoin_group_by_user(request): 
    response = {'success': False}
    if request.method == "GET":   
        response['success'] = True            
        group = UserGroup.objects.filter(id=request.GET.get('group')).first()   
        user = get_user_obj(request.GET.get('user'))   
        group.users.remove(user)
    return HttpResponse(json.dumps(response))