import uuid
from django.contrib.auth import get_user_model, authenticate
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def send_verification_email(user):
    token = user.email_verify_token
    verify_url = f"https://linguaduo-backend.onrender.com/api/accounts/verify-email/{token}/"
    send_mail(
        subject="Verify your LinguaDuo email",
        message=f"Hi {user.username}!\n\nClick to verify your email:\n{verify_url}\n\nWelcome to LinguaDuo!",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


# ── Register ───────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    user = serializer.save()
    user.is_active = False
    user.is_email_verified = False
    user.save()

    try:
        send_verification_email(user)
    except Exception as e:
        user.delete()
        return Response(
            {"error": "Could not send verification email. Please check your email address."},
            status=500
        )

    return Response(
        {"message": "Account created! Please check your email to verify before logging in."},
        status=201
    )


# ── Verify Email ───────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request, token):
    try:
        user = User.objects.get(email_verify_token=token)
    except User.DoesNotExist:
        return Response({"error": "Invalid or expired link."}, status=400)

    if user.is_email_verified:
        return HttpResponseRedirect("https://thelinguaduo.netlify.app/login?verified=already")

    user.is_email_verified = True
    user.is_active = True
    user.email_verify_token = uuid.uuid4()  # rotate so link can't be reused
    user.save()

    return HttpResponseRedirect("https://thelinguaduo.netlify.app/login?verified=1")


# ── Resend Verification ────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification(request):
    email = request.data.get('email', '').strip().lower()
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"message": "If that email is registered, we've sent a verification link."})

    if user.is_email_verified:
        return Response({"message": "That email is already verified. You can log in."})

    try:
        send_verification_email(user)
    except Exception:
        return Response({"error": "Could not send email. Try again later."}, status=500)

    return Response({"message": "Verification email resent! Check your inbox."})


# ── Login ──────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email', '').lower().strip()
    password = request.data.get('password', '')

    user = authenticate(request, username=email, password=password)
    if not user:
        return Response({'error': 'Invalid email or password.'}, status=401)

    if not user.is_email_verified:
        return Response(
            {'error': 'Please verify your email first. Check your inbox.',
             'resend': True},
            status=403
        )

    user.is_online = True
    user.save(update_fields=['is_online'])

    tokens = get_tokens_for_user(user)
    return Response({
        'user': UserSerializer(user).data,
        **tokens
    })


# ── Google Login ───────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    import os
    token = request.data.get('id_token')
    if not token:
        return Response({"error": "id_token required."}, status=400)

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            os.environ.get('GOOGLE_CLIENT_ID')
        )
    except ValueError as e:
        return Response({"error": f"Invalid Google token: {str(e)}"}, status=401)

    google_email = idinfo['email']
    google_name = idinfo.get('name', '')
    is_verified = idinfo.get('email_verified', False)

    if not is_verified:
        return Response({"error": "Google email is not verified."}, status=403)

    user, created = User.objects.get_or_create(
        email=google_email,
        defaults={
            'username': google_name or google_email.split('@')[0],
            'is_email_verified': True,
            'is_active': True,
        }
    )

    if not created and not user.is_email_verified:
        user.is_email_verified = True
        user.is_active = True
        user.save()

    user.is_online = True
    user.save(update_fields=['is_online'])

    tokens = get_tokens_for_user(user)
    return Response({
        'user': UserSerializer(user).data,
        'is_new_user': created,
        **tokens
    })


# ── Logout ─────────────────────────────────────────────────────
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


# ── Me ─────────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


# ── Update Profile ─────────────────────────────────────────────
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    user.preferred_language = request.data.get('preferred_language', user.preferred_language)
    if 'username' in request.data:
        user.username = request.data['username']
    if 'native_language' in request.data:
        user.native_language = request.data['native_language']
    user.save()
    return Response({'message': 'Profile updated.', 'user': UserSerializer(user).data})


# ── User Detail ────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        return Response(UserSerializer(user).data)
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)
