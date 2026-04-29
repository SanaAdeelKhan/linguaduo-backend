from django.contrib import admin
from .models import Group, Membership, Message, Translation


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'is_study_group', 'created_at')


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'role', 'joined_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'message_type', 'group', 'recipient', 'created_at')


@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    list_display = ('message', 'language')
