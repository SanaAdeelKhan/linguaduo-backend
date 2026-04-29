from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'preferred_language', 'is_online', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('LinguaDuo', {'fields': ('preferred_language', 'avatar', 'is_online', 'last_seen')}),
    )
