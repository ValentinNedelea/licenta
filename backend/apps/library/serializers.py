import calendar
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.catalog.models import Book
from apps.catalog.serializers import BookListSerializer

from . import services
from .models import ReadingGoal, ReadingProgress, ReadingSession, Shelf, ShelfBook


class ShelfSerializer(serializers.ModelSerializer):
    books_count = serializers.SerializerMethodField()

    class Meta:
        model = Shelf
        fields = ("id", "name", "description", "kind", "is_public", "position", "books_count")
        read_only_fields = ("kind",)

    def get_books_count(self, shelf):
        if hasattr(shelf, "books_count"):          # adnotat în queryset
            return shelf.books_count
        return shelf.shelfbook_set.count()

    def validate_name(self, value):
        user = self.context["request"].user
        same = Shelf.objects.filter(user=user, name=value)
        if self.instance:
            same = same.exclude(pk=self.instance.pk)
            if self.instance.kind != Shelf.Kind.CUSTOM and value != self.instance.name:
                raise serializers.ValidationError("Rafturile implicite nu pot fi redenumite.")
        if same.exists():
            raise serializers.ValidationError("Ai deja un raft cu acest nume.")
        return value


class ShelfBookSerializer(serializers.ModelSerializer):
    book = BookListSerializer(read_only=True)

    class Meta:
        model = ShelfBook
        fields = ("book", "added_at", "position")


class AddBookSerializer(serializers.Serializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())


class ReadingProgressSerializer(serializers.ModelSerializer):
    book = BookListSerializer(read_only=True)

    class Meta:
        model = ReadingProgress
        fields = ("id", "book", "status", "current_page", "percent", "started_at",
                  "finished_at", "read_number", "private_notes", "updated_at")
        read_only_fields = ("status", "read_number", "updated_at")
        extra_kwargs = {
            "current_page": {"min_value": 0},
            "percent": {"min_value": 0, "max_value": 100},
        }

    def validate(self, attrs):
        page_count = self.instance.book.page_count if self.instance else None
        page = attrs.get("current_page")
        if page_count and page is not None and page > page_count:
            raise serializers.ValidationError(
                {"current_page": f"Cartea are doar {page_count} de pagini."})
        return attrs

    def update(self, instance, validated_data):
        # păstrăm pagina și procentul în concordanță
        page_count = instance.book.page_count
        if page_count:
            if "current_page" in validated_data and "percent" not in validated_data:
                validated_data["percent"] = min(
                    Decimal(100),
                    round(Decimal(validated_data["current_page"]) / page_count * 100, 2))
            elif "percent" in validated_data and "current_page" not in validated_data:
                validated_data["current_page"] = round(validated_data["percent"] * page_count / 100)
        return super().update(instance, validated_data)


class SetStatusSerializer(serializers.Serializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    status = serializers.ChoiceField(choices=ReadingProgress.Status.choices)

class ReadingSessionSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = ReadingSession
        fields = ("id", "book", "book_title", "reading_progress", "started_at", "ended_at",
                  "duration_seconds", "start_page", "end_page", "pages_read", "source")
        read_only_fields = ("reading_progress", "pages_read")

    def validate(self, attrs):
        started = attrs["started_at"]
        ended = attrs.get("ended_at")
        duration = attrs.get("duration_seconds")

        if started > timezone.now() + timedelta(minutes=5):
            raise serializers.ValidationError({"started_at": "Sesiunea nu poate începe în viitor."})
        if ended:
            if ended < started:
                raise serializers.ValidationError({"ended_at": "Sfârșitul e înaintea începutului."})
            attrs["duration_seconds"] = int((ended - started).total_seconds())
        elif duration:
            attrs["ended_at"] = started + timedelta(seconds=duration)
        else:
            raise serializers.ValidationError("Trimite ended_at sau duration_seconds.")
        if attrs["duration_seconds"] > 24 * 3600:
            raise serializers.ValidationError("O sesiune nu poate depăși 24 de ore.")

        start_page, end_page = attrs.get("start_page"), attrs.get("end_page")
        if start_page is not None and end_page is not None and end_page < start_page:
            raise serializers.ValidationError({"end_page": "Pagina de final e înaintea celei de început."})
        page_count = attrs["book"].page_count
        if page_count and end_page is not None and end_page > page_count:
            raise serializers.ValidationError({"end_page": f"Cartea are doar {page_count} de pagini."})
        return attrs

    def create(self, validated_data):
        return services.log_session(
            user=self.context["request"].user,
            book=validated_data["book"],
            started_at=validated_data["started_at"],
            ended_at=validated_data.get("ended_at"),
            duration_seconds=validated_data["duration_seconds"],
            start_page=validated_data.get("start_page"),
            end_page=validated_data.get("end_page"),
            source=validated_data.get("source", "manual"),
        )


class ReadingGoalSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    percent = serializers.SerializerMethodField()
    on_track = serializers.SerializerMethodField()

    class Meta:
        model = ReadingGoal
        fields = ("id", "year", "goal_type", "target", "progress", "percent", "on_track")
        extra_kwargs = {
            "target": {"min_value": 1},
            "year": {"min_value": 2000, "max_value": 2100},
        }

    def _progress(self, goal):
        if not hasattr(goal, "_progress_cache"):
            goal._progress_cache = services.goal_progress(goal.user, goal.year, goal.goal_type)
        return goal._progress_cache

    def get_progress(self, goal):
        return self._progress(goal)

    def get_percent(self, goal):
        return min(100, round(self._progress(goal) / goal.target * 100, 1))

    def get_on_track(self, goal):
        """True dacă ești la zi cu ritmul necesar pentru țintă (doar pentru anul curent)."""
        today = timezone.localdate()
        if goal.year != today.year:
            return None
        days = 366 if calendar.isleap(goal.year) else 365
        expected = goal.target * today.timetuple().tm_yday / days
        return self._progress(goal) >= expected

    def validate(self, attrs):
        if self.instance is None:
            user = self.context["request"].user
            if ReadingGoal.objects.filter(user=user, year=attrs["year"],
                                          goal_type=attrs.get("goal_type", "books")).exists():
                raise serializers.ValidationError(
                    "Ai deja un obiectiv de acest tip pentru anul respectiv.")
        else:
            attrs.pop("year", None)          # anul și tipul nu se schimbă după creare
            attrs.pop("goal_type", None)
        return attrs