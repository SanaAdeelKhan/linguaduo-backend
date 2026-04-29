from django.urls import path
from . import views

urlpatterns = [
    path('conversations/', views.conversations, name='conversations'),
    path('users/', views.users_list, name='users_list'),
    path('history/<str:room_name>/', views.message_history, name='message_history'),
    path('groups/', views.group_list, name='group_list'),
    path('groups/create/', views.create_group, name='create_group'),
    path('groups/<int:group_id>/join/', views.join_group, name='join_group'),
]
