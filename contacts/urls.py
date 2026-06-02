from django.urls import path
from . import views

urlpatterns = [
    path('send/', views.send_request, name='send-request'),
    path('pending/', views.pending_requests, name='pending-requests'),
    path('list/', views.list_contacts, name='list-contacts'),
    path('respond/<int:contact_id>/', views.respond_request, name='respond-request'),
    path('remove/<int:contact_id>/', views.remove_contact, name='remove-contact'),
    path('search/', views.search_users, name='search-users'),
    path('invite-link/', views.my_invite_link, name='invite-link'),
    path('accept-invite/', views.accept_invite, name='accept-invite'),
    path('invite-by-email/', views.invite_by_email, name='invite-by-email'),
]
