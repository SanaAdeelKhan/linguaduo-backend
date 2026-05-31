from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
import dns.resolver

User = get_user_model()

BLOCKED_DOMAINS = [
    'mailinator.com', 'guerrillamail.com', 'tempmail.com',
    'throwaway.email', 'fakeinbox.com', 'yopmail.com',
    '10minutemail.com', 'trashmail.com', 'sharklasers.com',
]

def validate_email_domain(email):
    domain = email.split('@')[1]
    if domain in BLOCKED_DOMAINS:
        raise serializers.ValidationError(
            "Disposable/temporary email addresses are not allowed."
        )
    try:
        dns.resolver.resolve(domain, 'MX')
    except Exception:
        raise serializers.ValidationError(
            f"'{domain}' doesn't appear to be a valid email domain."
        )


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2',
                  'native_language', 'preferred_language']

    def validate_email(self, value):
        value = value.strip().lower()
        validate_email_domain(value)
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'native_language',
                  'preferred_language', 'is_email_verified', 'avatar', 'is_online']
