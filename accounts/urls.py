from django.urls import path
from . import views

urlpatterns = [
    path('github', views.github_login, name='github-login'),
    path('github/callback', views.github_callback, name='github-callback'),
    path('refresh', views.refresh_token, name='refresh-token'),
    path('logout', views.logout, name='logout'),
    path('whoami', views.whoami, name='whoami'),
]