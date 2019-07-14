"""jango URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls import url, include
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, RedirectView
from django.conf.urls.static import static
from rest_framework_swagger.views import get_swagger_view

from django.contrib.auth import views
from django.conf import settings

schema_view = get_swagger_view(title='Pastebin API')

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('api/', include('api.urls')),
                  path('api-docs/', schema_view),
                  # url(r'^custom/signup/$', TemplateView.as_view(),name='signup'),
                  # url(r'^custom/email-verification/$',TemplateView.as_view(),name='email-verification'),
                  # url(r'^custom/login/$', TemplateView.as_view(),name='login'),
                  # url(r'^custom/logout/$', TemplateView.as_view(),name='logout'),url(r'^password-reset/$',TemplateView.as_view(),name='password-reset'),
                  # url(r'^custom/password-reset/confirm/$',TemplateView.as_view(),name='password-reset-confirm'),
                  # url(r'^custom/user-details/$',TemplateView.as_view(),name='user-details'),
                  # url(r'^custom/password-change/$',TemplateView.as_view(),name='password-change'),
                  # url(r'^custom/password-reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',TemplateView.as_view(),name='password_reset_confirm'),
                  path(r'accounts/', include('allauth.urls')),
                  path(r'rest-auth/', include('rest_auth.urls')),
                  path(r'rest-auth/signup', include('rest_auth.registration.urls')),
                  # url('fe/p-r/done/', views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from rest_auth import urls