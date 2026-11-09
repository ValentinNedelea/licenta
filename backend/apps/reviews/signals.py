from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.catalog.models import Book

from .models import BookReview, ReviewLike


def recalc_book_rating(book_id):
    agg = BookReview.objects.filter(
        book_id=book_id, rating__isnull=False, is_hidden=False
    ).aggregate(avg=Avg("rating"), n=Count("id"))
    Book.objects.filter(pk=book_id).update(
        avg_rating=round(agg["avg"] or 0, 2),
        rating_count=agg["n"],
    )


@receiver([post_save, post_delete], sender=BookReview)
def on_review_change(sender, instance, **kwargs):
    recalc_book_rating(instance.book_id)


@receiver([post_save, post_delete], sender=ReviewLike)
def on_like_change(sender, instance, **kwargs):
    BookReview.objects.filter(pk=instance.review_id).update(
        helpful_count=ReviewLike.objects.filter(review_id=instance.review_id).count()
    )