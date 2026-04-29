from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    preferred_language = models.CharField(
        max_length=10,
        default='en',
        help_text='Language code e.g. en, ar, fr, de'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True
    )
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
