from django.urls import path
from . import views

urlpatterns = [
    path('send/', views.send_request, name='send-request'),
    path('pending/', views.pending_requests, name='pending-requests'),
    path('list/', views.list_contacts, name='list-contacts'),
    path('respond/<int:contact_id>/', views.respond_request, name='respond-request'),
    path('remove/<int:contact_id>/', views.remove_contact, name='remove-contact'),
]
