from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    avatar_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    country = models.CharField(max_length=2, blank=True)
    role = models.CharField(max_length=20, default="user")
    email_verified_at = models.DateTimeField(null=True, blank=True)