from django.contrib import admin

from .models import (
    Author, AuthorClaimRequest, Book, BookAuthor, BookEdition, Genre, Series, Tag,
)


class BookAuthorInline(admin.TabularInline):
    model = BookAuthor
    extra = 1


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "isbn13", "publication_date", "avg_rating", "rating_count")
    search_fields = ("title", "isbn13")
    inlines = [BookAuthorInline]


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    search_fields = ("name",)


admin.site.register([Series, Genre, Tag, BookEdition, AuthorClaimRequest])