from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.catalog.models import Book

User = settings.AUTH_USER_MODEL


class Shelf(models.Model):
    class Kind(models.TextChoices):
        WANT_TO_READ = "want_to_read", "Want to read"
        CURRENTLY_READING = "currently_reading", "Currently reading"
        READ = "read", "Read"
        FAVORITES = "favorites", "Favorites"
        CUSTOM = "custom", "Custom"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shelves")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.CUSTOM)
    is_public = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    books = models.ManyToManyField(Book, through="ShelfBook", related_name="shelves")

    class Meta:
        db_table = "shelves"
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="uniq_shelf_user_name"),
        ]

    def __str__(self):
        return f"{self.name} ({self.user})"


class ShelfBook(models.Model):
    shelf = models.ForeignKey(Shelf, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "shelf_books"
        constraints = [
            models.UniqueConstraint(fields=["shelf", "book"], name="uniq_shelf_book"),
        ]


class ReadingProgress(models.Model):
    class Status(models.TextChoices):
        WANT_TO_READ = "want_to_read", "Want to read"
        READING = "reading", "Reading"
        READ = "read", "Read"
        DNF = "dnf", "Did not finish"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reading_progress")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reading_progress")
    status = models.CharField(max_length=20, choices=Status.choices)
    current_page = models.PositiveIntegerField(default=0)
    percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    started_at = models.DateField(null=True, blank=True)
    finished_at = models.DateField(null=True, blank=True)
    # 1 = prima citire, 2 = prima recitire etc.
    read_number = models.PositiveSmallIntegerField(default=1)
    private_notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reading_progress"
        verbose_name_plural = "reading progress"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book", "read_number"], name="uniq_progress_user_book_read"
            ),
            models.CheckConstraint(condition=Q(percent__gte=0, percent__lte=100), name="progress_percent_0_100"),
        ]

    def __str__(self):
        return f"{self.user} - {self.book} ({self.status})"


class ReadingSession(models.Model):
    class Source(models.TextChoices):
        TIMER = "timer", "Timer (focus mode)"
        MANUAL = "manual", "Manual"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reading_sessions")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reading_sessions")
    reading_progress = models.ForeignKey(
        ReadingProgress, null=True, blank=True, on_delete=models.SET_NULL, related_name="sessions"
    )
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    start_page = models.PositiveIntegerField(null=True, blank=True)
    end_page = models.PositiveIntegerField(null=True, blank=True)
    pages_read = models.PositiveIntegerField(default=0)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.TIMER)

    class Meta:
        db_table = "reading_sessions"
        indexes = [models.Index(fields=["user", "started_at"], name="idx_sessions_user_started")]


class ReadingGoal(models.Model):
    class GoalType(models.TextChoices):
        BOOKS = "books", "Books"
        PAGES = "pages", "Pages"
        MINUTES = "minutes", "Minutes"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reading_goals")
    year = models.PositiveSmallIntegerField()
    goal_type = models.CharField(max_length=10, choices=GoalType.choices, default=GoalType.BOOKS)
    target = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reading_goals"
        constraints = [
            models.UniqueConstraint(fields=["user", "year", "goal_type"], name="uniq_goal_user_year_type"),
        ]


class UserStreak(models.Model):
    user = models.OneToOneField(User, primary_key=True, on_delete=models.CASCADE, related_name="streak")
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_read_date = models.DateField(null=True, blank=True)
    freezes_available = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_streaks"


class UserStatsMonthly(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="monthly_stats")
    month = models.DateField(help_text="Prima zi a lunii")
    books_finished = models.PositiveIntegerField(default=0)
    pages_read = models.PositiveIntegerField(default=0)
    minutes_read = models.PositiveIntegerField(default=0)
    avg_rating_given = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "user_stats_monthly"
        verbose_name_plural = "user stats monthly"
        constraints = [
            models.UniqueConstraint(fields=["user", "month"], name="uniq_stats_user_month"),
        ]