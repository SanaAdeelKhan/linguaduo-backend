from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import Contact
from .serializers import ContactSerializer

User = get_user_model()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_request(request):
    username = request.data.get('username')
    if not username:
        return Response({'error': 'Username required'}, status=400)
    try:
        receiver = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    if receiver == request.user:
        return Response({'error': 'Cannot add yourself'}, status=400)
    contact, created = Contact.objects.get_or_create(
        sender=request.user,
        receiver=receiver
    )
    if not created:
        return Response({'error': 'Request already sent'}, status=400)
    return Response(ContactSerializer(contact).data, status=201)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def respond_request(request, contact_id):
    action = request.data.get('action')  # 'accept' or 'reject'
    try:
        contact = Contact.objects.get(id=contact_id, receiver=request.user, status='pending')
    except Contact.DoesNotExist:
        return Response({'error': 'Request not found'}, status=404)
    if action == 'accept':
        contact.status = 'accepted'
        contact.save()
        return Response(ContactSerializer(contact).data)
    elif action == 'reject':
        contact.delete()
        return Response({'message': 'Request rejected'})
    return Response({'error': 'Invalid action'}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_contacts(request):
    accepted = Contact.objects.filter(
        status='accepted'
    ).filter(
        sender=request.user
    ) | Contact.objects.filter(
        status='accepted'
    ).filter(
        receiver=request.user
    )
    return Response(ContactSerializer(accepted, many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_requests(request):
    pending = Contact.objects.filter(receiver=request.user, status='pending')
    return Response(ContactSerializer(pending, many=True).data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_contact(request, contact_id):
    try:
        contact = Contact.objects.get(
            id=contact_id,
            status='accepted'
        )
        if contact.sender != request.user and contact.receiver != request.user:
            return Response({'error': 'Not your contact'}, status=403)
        contact.delete()
        return Response({'message': 'Contact removed'})
    except Contact.DoesNotExist:
        return Response({'error': 'Contact not found'}, status=404)
