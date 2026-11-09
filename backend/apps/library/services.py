from django.db import transaction
from django.utils import timezone

from .models import ReadingProgress, Shelf, ShelfBook

STATUS_TO_KIND = {
    "want_to_read": Shelf.Kind.WANT_TO_READ,
    "reading": Shelf.Kind.CURRENTLY_READING,
    "read": Shelf.Kind.READ,
}
KIND_TO_STATUS = {kind: status for status, kind in STATUS_TO_KIND.items()}
STATUS_KINDS = list(STATUS_TO_KIND.values())


def latest_progress(user, book):
    return (ReadingProgress.objects.filter(user=user, book=book)
            .order_by("-read_number").first())


def _sync_shelves(user, book, status):
    """Scoate cartea de pe rafturile de stare și o pune pe cel potrivit."""
    ShelfBook.objects.filter(
        shelf__user=user, shelf__kind__in=STATUS_KINDS, book=book
    ).delete()
    kind = STATUS_TO_KIND.get(status)
    if kind:
        shelf = Shelf.objects.filter(user=user, kind=kind).first()
        if shelf:
            ShelfBook.objects.get_or_create(shelf=shelf, book=book)


@transaction.atomic
def set_status(user, book, status):
    today = timezone.localdate()
    progress = latest_progress(user, book)

    if progress is None:
        progress = ReadingProgress(user=user, book=book, read_number=1)
    elif progress.status == "read" and status in ("want_to_read", "reading"):
        # carte terminată, pornită din nou: recitire (rând nou, read_number + 1)
        progress = ReadingProgress(user=user, book=book, read_number=progress.read_number + 1)

    progress.status = status
    if status == "reading" and not progress.started_at:
        progress.started_at = today
    if status == "read":
        progress.started_at = progress.started_at or today
        progress.finished_at = progress.finished_at or today
        progress.percent = 100
        if book.page_count:
            progress.current_page = book.page_count
    progress.save()

    _sync_shelves(user, book, status)
    return progress


@transaction.atomic
def delete_progress(progress):
    user, book = progress.user, progress.book
    was_latest = latest_progress(user, book).pk == progress.pk
    progress.delete()
    if was_latest:
        previous = latest_progress(user, book)
        _sync_shelves(user, book, previous.status if previous else None)