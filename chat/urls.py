from django.urls import path
from . import views

urlpatterns = [
    path('conversations/', views.conversations, name='conversations'),
    path('users/', views.users_list, name='users_list'),
    path('history/<str:room_name>/', views.message_history, name='message_history'),
    path('groups/', views.group_list, name='group_list'),
    path('groups/create/', views.create_group, name='create_group'),
    path('groups/<int:group_id>/join/', views.join_group, name='join_group'),
    path('groups/<int:group_id>/members/', views.group_members, name='group_members'),
    path('groups/<int:group_id>/add-member/', views.add_member, name='add_member'),
    path('groups/<int:group_id>/remove-member/<int:user_id>/', views.remove_member, name='remove_member'),
    path('groups/<int:group_id>/rename/', views.rename_group, name='rename_group'),
]
