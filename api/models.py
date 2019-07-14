from django.db import models
from django.contrib.auth.models import User
import json
from django.utils import timezone
from django.db.models import DateField
from helper import get_in_ks
from django.db.models.signals import post_save, pre_save, pre_delete
import copy

VOTE_TYPE_CHOICES = (
    ('DOWN_VOTE', 'Down vote'),
    ('UP_VOTE', 'Up vote'),
)

# Create your models here.
class Post(models.Model):
    title = models.CharField(max_length=250)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    author = models.CharField(max_length=250)
    category = models.CharField(max_length=250)
    source = models.CharField(max_length=250)
    author_description = models.TextField(blank=True)
    main_sentence_number = models.IntegerField(default=1)
    main_sentence = models.TextField(blank=True)
    sentence2 = models.TextField(blank=True)
    sentence3 = models.TextField(blank=True)
    sentence4 = models.TextField(blank=True)
    sentence5 = models.TextField(blank=True)
    people1 = models.TextField(blank=True)
    people2 = models.TextField(blank=True)
    people3 = models.TextField(blank=True)
    people4 = models.TextField(blank=True)
    json_response = models.TextField(blank=True)
    embedded_image = models.ImageField(blank=True, null=True)
    thumbnail_image = models.ImageField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # created_at.editable = True
    positive_score = models.FloatField(default=0.0)
    is_private_post = models.BooleanField(blank=False, default=False)
    relevant_post_list = models.ManyToManyField("Post", related_name="custom_user_following", blank=True)
    recommended_post_list = models.ManyToManyField("Post", related_name="second_recommended_list", blank=True)
    total_views = models.IntegerField(default=0)
    
    def __str__(self):
        return self.title

    def get_main_sentence(self):
        if self.main_sentence_number == 1:
            return self.main_sentence
        elif self.main_sentence_number == 2:
            return self.sentence2
        elif self.main_sentence_number == 3:
            return self.sentence3
        elif self.main_sentence_number == 4:
            return self.sentence4
        elif self.main_sentence_number == 5:
            return self.sentence5
        else:
            return ""

    @property
    def get_object_dic(self):
        return {'id': self.id, 'title': self.title, 'author': self.author, 'main_sentence': self.get_main_sentence(),
                'created_at': str(self.created_at)}

    def get_publisher_dic(self, request):
        profile_obj = Profile.objects.filter(user=self.user).only('name').first()
        if profile_obj:
            return profile_obj.get_obj_dic(request)
        return None

    def get_post_data_for_profile(self, request):
        try:
            img_url = request.build_absolute_uri(self.thumbnail_image.url)
        except:
            img_url = ""
            pass
        total_comments = Comment.objects.filter(post=self).count()
        return {'id': self.id, 'title': self.title, 'author': self.author,
                'img_url': img_url, 'created_at': str(self.created_at), 'total_comments': total_comments,
                'total_views': get_in_ks(self.total_views), 'publisher': self.get_publisher_dic(request)}

    def get_post_data_for_search(self, request):
        try:
            img_url = request.build_absolute_uri(self.thumbnail_image.url)
        except:
            img_url = ""
            pass
        total_comments = Comment.objects.filter(post=self).count()
        return {'id': self.id, 'title': self.title, 'author': self.author, 'main_sentence': self.get_main_sentence(),
                'img_url': img_url, 'created_at': str(self.created_at), 'total_comments': total_comments, 'post_user': Profile.objects.filter(user=self.user).first().name,
                'total_views': get_in_ks(self.total_views), 'publisher': self.get_publisher_dic(request)}

    @property
    def get_created_at_str(self):
        return self.created_at.strftime('%B %-d, %Y')

    @property
    def get_json(self):
        title_list = []
        id_list = []
        created_at_list = []
        for post in self.relevant_post_list.order_by('-created_at').all():            
            title_list.append(post.title)
            id_list.append(post.id)
            created_at_list.append(str(post.created_at))
        return json.dumps({'title': title_list, 'id': id_list, 'created_at_list': created_at_list})

    def get_recommended(self, request):
        title_list = []
        id_list = []
        img_list = []
        for post in self.recommended_post_list.all():            
            title_list.append(post.title)
            id_list.append(post.id)
            try:
                img_list.append(request.build_absolute_uri(post.thumbnail_image.url))
            except:
                img_list.append('')
                pass
        print(img_list)
        return json.dumps({'title': title_list, 'id': id_list, 'img_list': img_list})


class TopStories(models.Model):
    post_id = models.ForeignKey('Post', on_delete=models.CASCADE)
    position_number = models.TextField(blank=False)

    def __str__(self):
        return self.position_number

class UserGroup(models.Model):
    name = models.TextField(blank=False)
    description = models.TextField(blank=False)
    privacy = models.BooleanField(default=True)
    visible = models.BooleanField(default=False)
    pinned_commentaries = models.TextField(blank=True)
    last_comment_id = models.IntegerField(default=0)
    thumbnail_image = models.TextField(blank=True, null=True)
    users = models.ManyToManyField(User)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='usergroup_creator')
    def __str__(self):
        return self.name
        
class Notification(models.Model):
    Notification_Type_Like = "like"
    Notification_Type_Dislike = "dislike"
    Notification_Type_Upvote = "upvote"
    Notification_Type_Downvote = "downvote"
    Notification_Type_Comment = "comment"
    Notification_Type_Reply = "reply"
    Notification_Type_Post = "new_article_keyword"
    Notification_Type_Commentary = "new_commentary_subscribed"
    Notification_Type_Invite = "invite"

    related_profile = models.ManyToManyField('Profile', related_name="related_profile_profiles", blank=True)
    notification_type = models.TextField(blank=False)
    post_id = models.IntegerField(default=-1)
    comment_id = models.IntegerField(default=-1)
    people_keyword = models.TextField(blank=True, null=True)
    profile_id = models.IntegerField(default=-1)
    saved_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.notification_type

    def get_post(self):
        post_obj = Post.objects.filter(id=self.post_id).first()
        return post_obj

    def get_profile(self):
        profile_obj = Profile.objects.filter(id=self.profile_id).first()
        return profile_obj

    def get_json(self):
        response = {"notification_type": self.notification_type}
        if self.notification_type == Notification.Notification_Type_Post:
            if self.people_keyword:
                response["keyword"] = str(self.people_keyword)
                response["img_url"] = ""
                wiki_object = WikiPedia.objects.filter(keyword__iexact=str(self.people_keyword)). \
                    only('image_url').first()
                if wiki_object:
                    response["img_url"] = wiki_object.image_url
        else:
            profile_obj = self.get_profile()
            if profile_obj:
                response['user_id'] = profile_obj.user.id
                response['user_name'] = profile_obj.name
                response['img_url'] = profile_obj.image
            if self.notification_type == Notification.Notification_Type_Like or \
                            self.notification_type == Notification.Notification_Type_Comment:
                post_obj = self.get_post()
                if post_obj:
                    response['post_id'] = post_obj.id
                response['comment_id'] = self.comment_id
        return response


class WikiPedia(models.Model):
    keyword = models.TextField(blank=False)
    description = models.TextField(blank=True)
    image_url = models.TextField(blank=True)
    uploaded_image = models.ImageField(blank=True, null=True)
    reference_title = models.TextField(blank=True)
    reference_url = models.TextField(blank=True)

    def wiki_dic(self, request):
        dic_wiki = {'keyword': self.keyword}
        description = str(self.description).strip(" ")
        if description.__len__() > 0:
            dic_wiki['description'] = description
        image_url = str(self.image_url).strip(" ")
        if image_url.__len__() > 0:
            dic_wiki['image_url'] = image_url
        elif self.uploaded_image and len(self.uploaded_image.url) > 0:
            image_url = request.build_absolute_uri(self.uploaded_image.url)
            dic_wiki['image_url'] = image_url

        reference_title = str(self.reference_title).strip(" ")
        reference_url = str(self.reference_url).strip(" ")
        if reference_title.__len__() > 0 and reference_url.__len__() > 0:
            dic_wiki['reference_title'] = reference_title
            dic_wiki['reference_url'] = reference_url

        return dic_wiki

    def __str__(self):
        return self.keyword


class PeoplePostRelationship(models.Model):
    post_id = models.ForeignKey('Post', on_delete=models.CASCADE)
    people_name = models.TextField(blank=True)


class UserPostViewed(models.Model):
    post_id = models.ForeignKey('Post', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class FollowedPeople(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    people_name = models.TextField(blank=False)


class TrendingSearch(models.Model):
    people_name = models.TextField(blank=False)
    total_count = models.IntegerField(default=0)


class TopPeopleInSavedPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    people_name = models.TextField(blank=True)
    total_count = models.IntegerField(default=0)


class TopPeopleInLikedPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    people_name = models.TextField(blank=True)
    total_count = models.IntegerField(default=0)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True)
    bio = models.TextField(blank=True)
    image = models.TextField(blank=True)
    name = models.CharField(blank=True, max_length=150)
    verified = models.BooleanField(default=False)
    show_profile_keywords = models.BooleanField(default=True)
    show_commentary_articles = models.BooleanField(default=True)
    show_articles_first = models.BooleanField(default=True)
    total_views = models.IntegerField(default=0)
    last_notification_id = models.IntegerField(default=0)
    following = models.ManyToManyField("Profile", related_name="profile_following", blank=True)
    pinned_commentary = models.OneToOneField("Comment", related_name="commentary_pinned", blank=True, null=True,
                                             on_delete=models.CASCADE)
    pinned_article = models.OneToOneField(Post, related_name="article_pinned", blank=True, null=True,
                                          on_delete=models.CASCADE)
    pinned_profile = models.OneToOneField("Profile", related_name="profile_pinned", blank=True, null=True,
                                          on_delete=models.CASCADE)
    pinned_groups = models.TextField(blank=True)
    uID = models.TextField(blank=True)

    def get_obj_dic(self, request):
        try:
            img_url = self.image  # request.build_absolute_uri(self.image.url)
        except:
            img_url = ""
            pass
        return {'id': self.user.id, 'name': self.name, 'img_url': img_url, 'bio': self.bio,
                'is_verified': self.verified, 'show_profile_keywords': self.show_profile_keywords,
                'show_commentary_articles': self.show_commentary_articles,'uID':self.uID,
                'show_articles_first': self.show_articles_first
                }

    def get_total_followers(self):
        return Profile.objects.filter(following__in=[self]).count()

    def __str__(self):
        return "Profile for {name}".format(name=self.name)


class PostReaction(models.Model):
    post = models.ForeignKey('api.Post', on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=20)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return "Post reaction"

    class Meta:
        unique_together = ('post', 'user')


class VoteSavedPost(models.Model):
    saved_post = models.ForeignKey('api.SavedPost', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)

    def __str__(self):
        return "VoteSavedPost"

    class Meta:
        unique_together = ('saved_post', 'user')


class SavedPost(models.Model):
    post = models.ForeignKey('api.Post', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    commentary = models.TextField(blank=True)
    saved_at = models.DateTimeField(auto_now_add=True)

    # class Meta:
    #     unique_together = ('post', 'user')

    def __str__(self):
        return "Saved post"

    def get_saved_post_data_for_profile(self, request):
        json_dic = self.post.get_post_data_for_profile(request)
        json_dic['commentary'] = self.commentary
        json_dic['saved_at'] = str(self.saved_at)
        json_dic['saved_post_id'] = str(self.id)
        json_dic['current_profile'] = self.profile.get_obj_dic(request)
        json_dic['like_count'] = VoteSavedPost.objects.filter(saved_post=self).count()

        return json_dic

class VoteComment(models.Model):
    comment = models.ForeignKey('api.Comment', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class Comment(models.Model):
    post = models.ForeignKey('api.Post', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    kind = models.IntegerField(default=0)   #0:article page, 1: group commentary, 2: commentary comment, 3: my articles
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Comment: {comment}".format(comment=self.comment)

    def get_info(self, request):
        json_dic = self.post.get_post_data_for_profile(request)
        json_dic['id'] = self.id
        json_dic['commentary'] = self.comment
        json_dic['saved_at'] = str(self.created_at)
        json_dic['post_id'] = str(self.post.id)
        json_dic['current_profile'] = Profile.objects.filter(user=self.user).first().get_obj_dic(request)
        json_dic['like_count'] = VoteComment.objects.filter(comment=self).count()
        json_dic['kind'] = self.kind
        if self.kind == 1:
            json_dic['url'] = '/group/{}#commentary_{}'.format(GroupComment.objects.filter(comment=self).first().group.id, self.id)
        elif self.kind == 2:
            json_dic['url'] = '/news-page/{}#commentary_{}'.format(self.user.id, self.id)
        return json_dic


class GroupComment(models.Model):
    comment = models.ForeignKey('api.Comment', on_delete=models.CASCADE)
    group = models.ForeignKey('api.UserGroup', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class GroupCommentary(models.Model):    
    group = models.ForeignKey('api.UserGroup', on_delete=models.CASCADE)  
    post = models.ForeignKey('api.Post', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cached_vars=['group', 'post', 'user', 'comment', 'updated_at']

    def __init__(self, *args, **kwargs):
        super(GroupCommentary, self).__init__(*args, **kwargs)
        self.var_cache = {}
        if getattr(self,'comment'):
            for var in self.cached_vars:
                self.var_cache[var] = copy.copy(getattr(self, var))
    def __str__(self):
        return "{} : {} : {}".format(self.group.name, self.user.username, self.comment)
    def save(self,recursive=True,**kwargs):
        result = super(GroupCommentary,self).save(**kwargs)
        if recursive:             
            if self.var_cache:        
                [(self.var_cache[var], getattr(self, var)) for var in self.cached_vars]
                pre_instance = self.var_cache
                print(pre_instance)
                print(self)
                if pre_instance['post'] != self.post or pre_instance['comment'] != self.comment or pre_instance['user'] != self.user or pre_instance['group'] != self.group:
                    comment = Comment.objects.filter(post=pre_instance['post'], comment=pre_instance['comment'], user=pre_instance['user'], kind=1).first()
                    gc = GroupComment.objects.filter(group=pre_instance['group'], comment=comment).first()
                    print(gc.group)
                    gc.group = self.group
                    gc.comment = comment
                    gc.save()  
                    comment.post = self.post
                    comment.comment = self.comment
                    comment.user = self.user
                    comment.updated_at = self.updated_at
                    comment.save()   
            else:
                comment = Comment(post=self.post, comment=self.comment, user=self.user, kind=1)
                comment.save()
                group_comment = GroupComment(group=self.group, comment=comment)
                group_comment.save()      
        return result

def delete_group_commentary(sender, **kwargs):
    instance = kwargs["instance"]   
    comment = Comment.objects.filter(post=instance.post, user=instance.user, comment=instance.comment).first()
    GroupComment.objects.filter(comment=comment).delete()
    comment.delete()

# pre_save.connect(create_group_commentary, sender=GroupCommentary)
pre_delete.connect(delete_group_commentary, sender=GroupCommentary)

class ProfileCommentary(models.Model):    
    post = models.ForeignKey('api.Post', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cached_vars=['post', 'user', 'comment', 'updated_at']

    def __init__(self, *args, **kwargs):
        super(ProfileCommentary, self).__init__(*args, **kwargs)
        self.var_cache = {}
        if getattr(self,'comment'):
            for var in self.cached_vars:
                self.var_cache[var] = copy.copy(getattr(self, var))
    def __str__(self):
        return "{} : {}".format(self.user.username, self.comment)
    def save(self,recursive=True,**kwargs):
        result = super(ProfileCommentary,self).save(**kwargs)
        if recursive:             
            if self.var_cache:
                [(self.var_cache[var], getattr(self, var)) for var in self.cached_vars]
                pre_instance = self.var_cache
                print(pre_instance)
                comment = Comment.objects.filter(post=pre_instance['post'], comment=pre_instance['comment'], user=pre_instance['user'], kind=2).first()
                comment.post = self.post
                comment.comment = self.comment
                comment.user = self.user
                comment.updated_at = self.updated_at
                comment.save()       
            else:
                comment = Comment(post=self.post, comment=self.comment, user=self.user, kind=2)
                comment.save()      
        return result

   
def delete_profile_commentary(sender, **kwargs):
    instance = kwargs["instance"]   
    Comment.objects.filter(post=instance.post, user=instance.user, comment=instance.comment, kind=2).delete()

pre_delete.connect(delete_profile_commentary, sender=ProfileCommentary)

class CommentReply(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE,null=True)
    reply = models.TextField()
    replied_reply = models.ForeignKey('self', on_delete=models.CASCADE,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Comment reply: {reply}".format(reply=self.reply)


class ForgetPassword(models.Model):
    email = models.CharField(max_length=150)
    token = models.CharField(max_length=150)

    def __str__(self):
        return self.email;


class ReplyVote(models.Model):
    reply = models.ForeignKey(CommentReply, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=100, choices=VOTE_TYPE_CHOICES)

    def __str__(self):
        return "A vote by {user} on reply {reply} type {type}".format(user=self.user, reply=self.reply,
                                                                      type=self.vote_type)

    class Meta:
        unique_together = ('reply', 'user')


class CommentVote(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=100, choices=VOTE_TYPE_CHOICES)

    class Meta:
        unique_together = ('comment', 'user')

    def __str__(self):
        return "Comment {comment} {vote_type}vote ".format(vote_type=self.vote_type, comment=self.comment)

class PostVote(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=100, choices=VOTE_TYPE_CHOICES)

    class Meta:
        unique_together = ('post', 'user')

    def __str__(self):
        return "Post {post} {vote_type}vote ".format(vote_type=self.vote_type, post=self.post)
