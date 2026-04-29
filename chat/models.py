from django.db import models
from django.conf import settings


class Group(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='group_avatars/', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_groups'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_study_group = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Membership(models.Model):
    ROLE_CHOICES = [('admin', 'Admin'), ('member', 'Member')]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group')

    def __str__(self):
        return f'{self.user} in {self.group}'


class Message(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('voice', 'Voice'),
        ('image', 'Image'),
        ('file', 'File'),
        ('video', 'Video'),
    ]

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messages'
    )
    # For direct messages — null if it's a group message
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_messages'
    )
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    original_text = models.TextField(blank=True)
    original_language = models.CharField(max_length=10, default='en')
    file_url = models.URLField(blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender} — {self.message_type} at {self.created_at}'


class Translation(models.Model):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='translations'
    )
    language = models.CharField(max_length=10)
    translated_text = models.TextField()

    class Meta:
        unique_together = ('message', 'language')

    def __str__(self):
        return f'{self.message_id} → {self.language}'
