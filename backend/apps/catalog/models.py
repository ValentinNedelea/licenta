from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Series(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "series"
        verbose_name_plural = "series"

    def __str__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    country = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    death_date = models.DateField(null=True, blank=True)
    # setat când un utilizator își revendică profilul de autor
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="author_profile",
    )
    claimed_at = models.DateTimeField(null=True, blank=True)
    external_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "authors"

    def __str__(self):
        return self.name


class AuthorClaimRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="claim_requests")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="author_claim_requests"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    message = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reviewed_author_claims",
    )

    class Meta:
        db_table = "author_claim_requests"


class Genre(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    parent_genre = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    book_count = models.PositiveIntegerField(default=0)  # denormalizat

    class Meta:
        db_table = "genres"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        db_table = "tags"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=500)
    subtitle = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    isbn10 = models.CharField(max_length=10, blank=True)
    isbn13 = models.CharField(max_length=13, unique=True, null=True, blank=True)
    cover_img_url = models.URLField(max_length=500, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    language = models.CharField(max_length=10, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    series = models.ForeignKey(
        Series, null=True, blank=True, on_delete=models.SET_NULL, related_name="books"
    )
    series_position = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    # contoare denormalizate, actualizate când se adaugă/șterg rating-uri
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)
    # media și numărul de rating-uri din dataset-ul extern (Goodbooks-10k);
    # nu se recalculează, spre deosebire de avg_rating / rating_count
    external_avg_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    external_rating_count = models.PositiveIntegerField(default=0)
    # sursa importului (de ex. openlibrary, goodbooks10k) și id-ul din acea sursă
    external_source = models.CharField(max_length=20, blank=True)
    external_id = models.CharField(max_length=100, blank=True)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="created_books",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    authors = models.ManyToManyField(Author, through="BookAuthor", related_name="books")
    genres = models.ManyToManyField(Genre, through="BookGenre", related_name="books")
    tags = models.ManyToManyField(Tag, through="BookTag", related_name="books")

    class Meta:
        db_table = "books"
        constraints = [
            models.UniqueConstraint(
                fields=["external_source", "external_id"],
                condition=~models.Q(external_source=""),
                name="uniq_books_external_source_id",
            ),
        ]

    def __str__(self):
        return self.title


class BookAuthor(models.Model):
    class Role(models.TextChoices):
        AUTHOR = "author", "Author"
        TRANSLATOR = "translator", "Translator"
        ILLUSTRATOR = "illustrator", "Illustrator"
        EDITOR = "editor", "Editor"

    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.AUTHOR)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "book_authors"
        constraints = [
            models.UniqueConstraint(fields=["book", "author", "role"], name="uniq_book_author_role"),
        ]
        ordering = ["position"]


class BookGenre(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)

    class Meta:
        db_table = "book_genres"
        constraints = [
            models.UniqueConstraint(fields=["book", "genre"], name="uniq_book_genre"),
        ]


class BookTag(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    added_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "book_tags"
        constraints = [
            models.UniqueConstraint(fields=["book", "tag"], name="uniq_book_tag"),
        ]


class BookEdition(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="editions")
    isbn13 = models.CharField(max_length=13, blank=True)
    format = models.CharField(max_length=20, blank=True)  # hardcover, paperback, ebook, audiobook
    publisher = models.CharField(max_length=255, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    cover_img_url = models.URLField(max_length=500, blank=True)

    class Meta:
        db_table = "book_editions"