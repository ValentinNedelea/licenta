from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.catalog.models import Author, Book

User = settings.AUTH_USER_MODEL


def validate_rating_step(value):
    """Rating-ul trebuie să fie multiplu de 0,25 (0, 0.25, 0.5, ... 5)."""
    if value is not None and (Decimal(value) * 4) % 1 != 0:
        raise ValidationError("Rating-ul trebuie să fie multiplu de 0,25.")


class BookReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reviews")
    # 0-5, pas 0,25; poate lipsi dacă utilizatorul a scris doar text
    rating = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5), validate_rating_step],
    )
    review_text = models.TextField(blank=True)
    has_spoilers = models.BooleanField(default=False)
    spoiler_score = models.FloatField(null=True, blank=True)      # completat de un model AI
    sentiment_score = models.FloatField(null=True, blank=True)    # completat de un model AI
    helpful_count = models.PositiveIntegerField(default=0)        # denormalizat
    comments_count = models.PositiveIntegerField(default=0)       # denormalizat
    is_hidden = models.BooleanField(default=False)                # ascunsă de moderare
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "book_reviews"
        constraints = [
            models.UniqueConstraint(fields=["user", "book"], name="uniq_review_user_book"),
            models.CheckConstraint(
                condition=Q(rating__isnull=True) | Q(rating__gte=0, rating__lte=5),
                name="review_rating_0_5",
            ),
        ]
        indexes = [models.Index(fields=["book", "created_at"], name="idx_reviews_book_created")]

    def __str__(self):
        return f"{self.user} -> {self.book} ({self.rating})"


class ReviewLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    review = models.ForeignKey(BookReview, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "review_likes"
        constraints = [
            models.UniqueConstraint(fields=["user", "review"], name="uniq_review_like"),
        ]


class ReviewComment(models.Model):
    review = models.ForeignKey(BookReview, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent_comment = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)  # ștergere "soft"

    class Meta:
        db_table = "review_comments"


class ReviewAspectRating(models.Model):
    class Aspect(models.TextChoices):
        PACING = "pacing", "Pacing"
        CHARACTERS = "characters", "Characters"
        ENDING = "ending", "Ending"
        STYLE = "style", "Style"
        WORLDBUILDING = "worldbuilding", "Worldbuilding"

    review = models.ForeignKey(BookReview, on_delete=models.CASCADE, related_name="aspect_ratings")
    aspect = models.CharField(max_length=20, choices=Aspect.choices)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        db_table = "review_aspect_ratings"
        constraints = [
            models.UniqueConstraint(fields=["review", "aspect"], name="uniq_review_aspect"),
        ]


class Quote(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="quotes")
    author = models.ForeignKey(Author, null=True, blank=True, on_delete=models.SET_NULL)
    text = models.TextField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_by_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quotes")
    is_public = models.BooleanField(default=True)
    likes_count = models.PositiveIntegerField(default=0)          # denormalizat
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quotes"

    def __str__(self):
        return self.text[:60]


class QuoteLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quote_likes"
        constraints = [
            models.UniqueConstraint(fields=["user", "quote"], name="uniq_quote_like"),
        ]


class BookList(models.Model):
    # gol = listă curatoriată de aplicație
    owner_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE, related_name="book_lists"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cover_img_url = models.URLField(max_length=500, blank=True)
    is_public = models.BooleanField(default=True)
    is_curated = models.BooleanField(default=False)
    likes_count = models.PositiveIntegerField(default=0)          # denormalizat
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    books = models.ManyToManyField(Book, through="BookListItem", related_name="lists")

    class Meta:
        db_table = "book_lists"

    def __str__(self):
        return self.title


class BookListItem(models.Model):
    list = models.ForeignKey(BookList, on_delete=models.CASCADE, related_name="items")
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0)
    note = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "book_list_items"
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["list", "book"], name="uniq_list_book"),
        ]


class BookListLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    list = models.ForeignKey(BookList, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "book_list_likes"
        constraints = [
            models.UniqueConstraint(fields=["user", "list"], name="uniq_list_like"),
        ]


class BookActivityDaily(models.Model):
    """Contoare zilnice per carte; alimentează 'cărți în trend'."""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="daily_activity")
    day = models.DateField()
    shelf_adds = models.PositiveIntegerField(default=0)
    ratings_count = models.PositiveIntegerField(default=0)
    reviews_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "book_activity_daily"
        verbose_name_plural = "book activity daily"
        constraints = [
            models.UniqueConstraint(fields=["book", "day"], name="uniq_activity_book_day"),
        ]