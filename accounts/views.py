from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    data = request.data
    email = data.get('email', '').lower().strip()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    preferred_language = data.get('preferred_language', 'en')

    if not email or not username or not password:
        return Response({'error': 'Email, username and password are required.'}, status=400)

    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email already registered.'}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already taken.'}, status=400)

    user = User.objects.create_user(
        email=email,
        username=username,
        password=password,
        preferred_language=preferred_language,
    )
    tokens = get_tokens_for_user(user)
    return Response({
        'message': 'Account created successfully.',
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'preferred_language': user.preferred_language,
        },
        **tokens
    }, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    from django.contrib.auth import authenticate
    email = request.data.get('email', '').lower().strip()
    password = request.data.get('password', '')

    user = authenticate(request, username=email, password=password)
    if not user:
        return Response({'error': 'Invalid email or password.'}, status=401)

    user.is_online = True
    user.save(update_fields=['is_online'])

    tokens = get_tokens_for_user(user)
    return Response({
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'preferred_language': user.preferred_language,
        },
        **tokens
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data.get('refresh')
        token = RefreshToken(refresh_token)
        token.blacklist()
    except Exception:
        pass
    request.user.is_online = False
    request.user.save(update_fields=['is_online'])
    return Response({'message': 'Logged out successfully.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    return Response({
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'preferred_language': user.preferred_language,
        'is_online': user.is_online,
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    user.preferred_language = request.data.get('preferred_language', user.preferred_language)
    if 'username' in request.data:
        user.username = request.data['username']
    user.save()
    return Response({'message': 'Profile updated.', 'preferred_language': user.preferred_language})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        return Response({
            'id': user.id,
            'username': user.username,
            'preferred_language': user.preferred_language,
            'is_online': user.is_online,
        })
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)
