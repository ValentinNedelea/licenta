from django.contrib import admin

from .models import (
    ReadingGoal, ReadingProgress, ReadingSession, Shelf, ShelfBook, UserStatsMonthly, UserStreak,
)


class ShelfBookInline(admin.TabularInline):
    model = ShelfBook
    extra = 0


@admin.register(Shelf)
class ShelfAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "kind", "is_public")
    inlines = [ShelfBookInline]


@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "status", "current_page", "read_number")


admin.site.register([ReadingSession, ReadingGoal, UserStreak, UserStatsMonthly])