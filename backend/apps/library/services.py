from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, Max, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from apps.catalog.models import Genre
from apps.reviews.models import BookReview

from .models import ReadingProgress, ReadingSession, Shelf, ShelfBook, UserStreak

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

# ------------------------------------------------------------ sesiuni și streak
@transaction.atomic
def log_session(user, book, started_at, ended_at, duration_seconds,
                start_page=None, end_page=None, source="manual"):
    progress = latest_progress(user, book)
    if progress is None or progress.status == "want_to_read":
        progress = set_status(user, book, "reading")

    pages_read = 0
    if start_page is not None and end_page is not None:
        pages_read = max(0, end_page - start_page)

    session = ReadingSession.objects.create(
        user=user, book=book, reading_progress=progress, started_at=started_at,
        ended_at=ended_at, duration_seconds=duration_seconds, start_page=start_page,
        end_page=end_page, pages_read=pages_read, source=source)

    # avansăm pagina curentă a cărții (dar niciodată înapoi)
    if progress.status == "reading" and end_page is not None and end_page > progress.current_page:
        page = min(end_page, book.page_count) if book.page_count else end_page
        progress.current_page = page
        if book.page_count:
            progress.percent = min(Decimal(100), round(Decimal(page) / book.page_count * 100, 2))
        progress.save(update_fields=["current_page", "percent", "updated_at"])

    rebuild_streak(user)
    return session


def rebuild_streak(user):
    """Recalculează streak-ul din sesiuni. Este mereu corect, inclusiv după ștergeri."""
    dates = sorted(set(
        ReadingSession.objects.filter(user=user)
        .annotate(d=TruncDate("started_at")).values_list("d", flat=True)))
    longest = run = 0
    previous = None
    for day in dates:
        run = run + 1 if previous and (day - previous).days == 1 else 1
        longest = max(longest, run)
        previous = day

    streak, _ = UserStreak.objects.get_or_create(user=user)
    streak.current_streak = run if dates else 0     # seria care se termină la ultima zi citită
    streak.longest_streak = longest
    streak.last_read_date = dates[-1] if dates else None
    streak.save()
    return streak


def streak_summary(streak):
    today = timezone.localdate()
    if streak is None or streak.last_read_date is None:
        return {"current_streak": 0, "longest_streak": 0, "last_read_date": None, "read_today": False}
    # seria e "vie" doar dacă ai citit azi sau ieri
    alive = (today - streak.last_read_date).days <= 1
    return {
        "current_streak": streak.current_streak if alive else 0,
        "longest_streak": streak.longest_streak,
        "last_read_date": streak.last_read_date,
        "read_today": streak.last_read_date == today,
    }


# ------------------------------------------------------------ obiective și statistici
def goal_progress(user, year, goal_type):
    if goal_type == "books":
        return ReadingProgress.objects.filter(
            user=user, status="read", finished_at__year=year).count()
    agg = ReadingSession.objects.filter(user=user, started_at__year=year).aggregate(
        pages=Sum("pages_read"), secs=Sum("duration_seconds"))
    if goal_type == "pages":
        return agg["pages"] or 0
    return (agg["secs"] or 0) // 60          # minutes


def stats_overview(user, year):
    finished = ReadingProgress.objects.filter(
        user=user, status="read", finished_at__year=year).select_related("book")
    sessions = ReadingSession.objects.filter(user=user, started_at__year=year)

    s_agg = sessions.aggregate(pages=Sum("pages_read"), secs=Sum("duration_seconds"))
    f_agg = finished.aggregate(avg_pages=Avg("book__page_count"), max_pages=Max("book__page_count"))
    longest = (finished.exclude(book__page_count__isnull=True)
               .order_by("-book__page_count").first())

    months = {m: {"month": m, "books_finished": 0, "pages_read": 0, "minutes_read": 0}
              for m in range(1, 13)}
    for row in (finished.annotate(m=TruncMonth("finished_at")).values("m")
                .annotate(n=Count("id"))):
        months[row["m"].month]["books_finished"] = row["n"]
    for row in (sessions.annotate(m=TruncMonth("started_at")).values("m")
                .annotate(p=Sum("pages_read"), s=Sum("duration_seconds"))):
        months[row["m"].month]["pages_read"] = row["p"] or 0
        months[row["m"].month]["minutes_read"] = (row["s"] or 0) // 60

    book_ids = list(finished.values_list("book_id", flat=True))
    top_genres = [
        {"name": g.name, "slug": g.slug, "books": g.n}
        for g in (Genre.objects.filter(books__in=book_ids)
                  .annotate(n=Count("books", distinct=True)).order_by("-n", "name")[:5])
    ]

    rating = BookReview.objects.filter(
        user=user, created_at__year=year, rating__isnull=False).aggregate(a=Avg("rating"))["a"]
    days_read = (sessions.annotate(d=TruncDate("started_at"))
                 .values("d").distinct().count())

    return {
        "year": year,
        "books_finished": finished.count(),
        "pages_read": s_agg["pages"] or 0,
        "minutes_read": (s_agg["secs"] or 0) // 60,
        "days_read": days_read,
        "avg_rating_given": round(float(rating), 2) if rating is not None else None,
        "avg_book_pages": round(f_agg["avg_pages"]) if f_agg["avg_pages"] else None,
        "longest_book": ({"id": longest.book_id, "title": longest.book.title,
                          "pages": longest.book.page_count} if longest else None),
        "top_genres": top_genres,
        "months": list(months.values()),
    }