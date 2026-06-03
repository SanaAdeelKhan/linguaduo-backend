from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .models import Contact
from .serializers import ContactSerializer
import threading

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
    action = request.data.get('action')
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
        contact = Contact.objects.get(id=contact_id, status='accepted')
        if contact.sender != request.user and contact.receiver != request.user:
            return Response({'error': 'Not your contact'}, status=403)
        contact.delete()
        return Response({'message': 'Contact removed'})
    except Contact.DoesNotExist:
        return Response({'error': 'Contact not found'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return Response({'error': 'Query too short'}, status=400)
    users = User.objects.filter(
        username__icontains=query
    ).exclude(id=request.user.id)[:10]
    results = []
    for u in users:
        contact_status = None
        contact = Contact.objects.filter(
            sender=request.user, receiver=u
        ).first() or Contact.objects.filter(
            sender=u, receiver=request.user
        ).first()
        if contact:
            if contact.status == 'accepted':
                contact_status = 'accepted'
            elif contact.sender == request.user:
                contact_status = 'sent'
            else:
                contact_status = 'received'
        results.append({
            'id': u.id,
            'username': u.username,
            'preferred_language': u.preferred_language,
            'is_online': u.is_online,
            'contact_status': contact_status,
        })
    return Response(results)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_invite_link(request):
    token = str(request.user.invite_token)
    return Response({'invite_token': token})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_invite(request):
    token = request.data.get('token')
    try:
        inviter = User.objects.get(invite_token=token)
    except User.DoesNotExist:
        return Response({'error': 'Invalid invite link'}, status=404)
    if inviter == request.user:
        return Response({'error': 'Cannot add yourself'}, status=400)
    contact, created = Contact.objects.get_or_create(
        sender=inviter,
        receiver=request.user,
        defaults={'status': 'accepted'}
    )
    if not created:
        return Response({'error': 'Already connected'}, status=400)
    return Response({'message': f'You are now connected with {inviter.username}!'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_by_email(request):
    email = request.data.get('email', '').strip()
    if not email:
        return Response({'error': 'Email required'}, status=400)

    existing = User.objects.filter(email=email).first()
    if existing:
        if existing == request.user:
            return Response({'error': 'That is your own email'}, status=400)
        contact, created = Contact.objects.get_or_create(
            sender=request.user,
            receiver=existing
        )
        if not created:
            return Response({'error': 'Already connected or request sent'}, status=400)
        return Response({'message': f'{existing.username} is already on LinguaDuo! Contact request sent.'})

    invite_token = str(request.user.invite_token)
    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://thelinguaduo.netlify.app')
    invite_url = f"{frontend_url}/invite/{invite_token}"
    from_email = settings.DEFAULT_FROM_EMAIL
    sender_name = request.user.username
    subject = f"{sender_name} invited you to LinguaDuo!"
    message = f"{sender_name} wants to connect with you on LinguaDuo — a language learning chat app.\n\nClick the link below to join and connect:\n{invite_url}\n\nSee you there!"

    def send_async():
        try:
            send_mail(subject, message, from_email, [email], fail_silently=False)
            print(f"EMAIL SENT OK to {email}")
        except Exception as e:
            print(f"EMAIL ERROR: {e}")

    threading.Thread(target=send_async, daemon=True).start()
    return Response({'message': f'Invite sent to {email}!'})
