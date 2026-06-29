# accounts/sso.py
import os
from decouple import config
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from contacts.models import Contact

User = get_user_model()

GB_SSO_SECRET = config('GB_SSO_SECRET', default='')


def _find_or_create_user(email, username='', full_name=''):
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': _unique_username(username or email.split('@')[0]),
            'first_name': full_name.split(' ')[0] if full_name else '',
            'last_name': ' '.join(full_name.split(' ')[1:]) if full_name else '',
            'is_email_verified': True,
        }
    )
    return user, created


def _auto_add_contact(user_a, user_b):
    """Create mutual accepted contact between two users if not already exists."""
    exists = Contact.objects.filter(
        sender=user_a, receiver=user_b
    ).exists() or Contact.objects.filter(
        sender=user_b, receiver=user_a
    ).exists()

    if not exists:
        Contact.objects.create(
            sender=user_a,
            receiver=user_b,
            status='accepted'
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def gazabridge_sso_login(request):
    """
    Called by GazaBridge backend to auto-login/register a GB user in LinguaDuo.
    Payload: { email, username, full_name, shared_secret, target_email (optional), preferred_language (optional) }
    Returns: { access, refresh, user, target_ld_id (optional) }
    """
    data = request.data

    # Validate shared secret
    if not GB_SSO_SECRET or data.get('shared_secret') != GB_SSO_SECRET:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    email = (data.get('email') or '').strip().lower()
    username = (data.get('username') or '').strip()
    full_name = (data.get('full_name') or '').strip()
    target_email = (data.get('target_email') or '').strip().lower()
    preferred_language = (data.get('preferred_language') or 'en').strip()[:10]

    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Find or create the requesting user
    user, created = _find_or_create_user(email, username, full_name)

    # Set preferred_language only if new user OR still on default 'en' (never explicitly chosen)
    if created or user.preferred_language == 'en':
        user.preferred_language = preferred_language
        user.save(update_fields=['preferred_language'])

    # Issue JWT
    refresh = RefreshToken.for_user(user)

    result = {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'preferred_language': user.preferred_language,
            'is_online': user.is_online,
        },
    }

    # If target email provided, find/create target and auto-add as contacts
    if target_email:
        target_user, _ = _find_or_create_user(target_email)
        _auto_add_contact(user, target_user)
        result['target_ld_id'] = target_user.id

    return Response(result)


def _unique_username(base: str) -> str:
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{counter}"
        counter += 1
    return username
