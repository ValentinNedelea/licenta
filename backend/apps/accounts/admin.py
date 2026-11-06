from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Profil", {"fields": ("avatar_url", "bio", "date_of_birth", "country", "role", "email_verified_at")}),
    )
    list_display = ("username", "email", "role", "is_staff")