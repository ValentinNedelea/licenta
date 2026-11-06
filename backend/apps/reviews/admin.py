from django.contrib import admin

from .models import (
    BookActivityDaily, BookList, BookListItem, BookListLike, BookReview, Quote,
    QuoteLike, ReviewAspectRating, ReviewComment, ReviewLike,
)


class AspectInline(admin.TabularInline):
    model = ReviewAspectRating
    extra = 0


@admin.register(BookReview)
class BookReviewAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "rating", "has_spoilers", "is_hidden", "created_at")
    list_filter = ("has_spoilers", "is_hidden")
    inlines = [AspectInline]


class BookListItemInline(admin.TabularInline):
    model = BookListItem
    extra = 0


@admin.register(BookList)
class BookListAdmin(admin.ModelAdmin):
    list_display = ("title", "owner_user", "is_curated", "is_public", "likes_count")
    inlines = [BookListItemInline]


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("text", "book", "created_by_user", "is_public", "likes_count")


admin.site.register([ReviewLike, ReviewComment, QuoteLike, BookListLike, BookActivityDaily])