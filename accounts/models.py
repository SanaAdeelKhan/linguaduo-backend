# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    email = models.EmailField(unique=True)
    preferred_language = models.CharField(
        max_length=10,
        default='en',
        help_text='Language code e.g. en, ar, fr, de'
    )
    native_language = models.CharField(
        max_length=10,
        default='en',
        help_text='User native language code'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True
    )
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    # Email verification
    is_email_verified = models.BooleanField(default=False)
    email_verify_token = models.UUIDField(default=uuid.uuid4, editable=False)
    invite_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
