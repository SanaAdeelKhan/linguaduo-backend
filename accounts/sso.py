# accounts/sso.py
import os
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

GB_SSO_SECRET = os.environ.get('GB_SSO_SECRET', '')


@api_view(['POST'])
@permission_classes([AllowAny])
def gazabridge_sso_login(request):
    """
    Called by GazaBridge backend to auto-login/register a GB user in LinguaDuo.
    Payload: { email, username, full_name, shared_secret }
    Returns: { access, refresh, user: { id, email, username, preferred_language, is_online } }
    """
    data = request.data

    # Validate shared secret
    if not GB_SSO_SECRET or data.get('shared_secret') != GB_SSO_SECRET:
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    email = data.get('email', '').strip().lower()
    username = data.get('username', '').strip()
    full_name = data.get('full_name', '').strip()

    if not email:
        return Response(
            {'error': 'Email is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Find or create user by email
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': _unique_username(username or email.split('@')[0]),
            'first_name': full_name.split(' ')[0] if full_name else '',
            'last_name': ' '.join(full_name.split(' ')[1:]) if full_name else '',
            'is_email_verified': True,  # trusted — came from GB OAuth
        }
    )

    # Issue JWT
    refresh = RefreshToken.for_user(user)

    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        # Full user object matching LD's AuthState interface exactly
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'preferred_language': user.preferred_language,
            'is_online': user.is_online,
        },
    })


def _unique_username(base: str) -> str:
    """Ensure username is unique in LD by appending a number if needed."""
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{counter}"
        counter += 1
    return username
