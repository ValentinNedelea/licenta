from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Shelf

DEFAULT_SHELVES = [
    ("Want to Read", Shelf.Kind.WANT_TO_READ),
    ("Currently Reading", Shelf.Kind.CURRENTLY_READING),
    ("Read", Shelf.Kind.READ),
    ("Favorites", Shelf.Kind.FAVORITES),
]


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_shelves(sender, instance, created, **kwargs):
    if created:
        Shelf.objects.bulk_create([
            Shelf(user=instance, name=name, kind=kind, position=i)
            for i, (name, kind) in enumerate(DEFAULT_SHELVES)
        ])