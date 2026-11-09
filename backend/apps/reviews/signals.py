from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.catalog.models import Book

from .models import (BookList, BookListLike, BookReview, Quote, QuoteLike,
                     ReviewComment, ReviewLike)


def recalc_book_rating(book_id):
    agg = BookReview.objects.filter(
        book_id=book_id, rating__isnull=False, is_hidden=False
    ).aggregate(avg=Avg("rating"), n=Count("id"))
    Book.objects.filter(pk=book_id).update(
        avg_rating=round(agg["avg"] or 0, 2), rating_count=agg["n"])


@receiver([post_save, post_delete], sender=BookReview)
def on_review_change(sender, instance, **kwargs):
    recalc_book_rating(instance.book_id)


@receiver([post_save, post_delete], sender=ReviewLike)
def on_review_like_change(sender, instance, **kwargs):
    BookReview.objects.filter(pk=instance.review_id).update(
        helpful_count=ReviewLike.objects.filter(review_id=instance.review_id).count())


@receiver([post_save, post_delete], sender=ReviewComment)
def on_comment_change(sender, instance, **kwargs):
    BookReview.objects.filter(pk=instance.review_id).update(
        comments_count=ReviewComment.objects.filter(
            review_id=instance.review_id, deleted_at__isnull=True).count())


@receiver([post_save, post_delete], sender=QuoteLike)
def on_quote_like_change(sender, instance, **kwargs):
    Quote.objects.filter(pk=instance.quote_id).update(
        likes_count=QuoteLike.objects.filter(quote_id=instance.quote_id).count())


@receiver([post_save, post_delete], sender=BookListLike)
def on_list_like_change(sender, instance, **kwargs):
    BookList.objects.filter(pk=instance.list_id).update(
        likes_count=BookListLike.objects.filter(list_id=instance.list_id).count())