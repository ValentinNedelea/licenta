from decimal import Decimal

from rest_framework import serializers

from apps.catalog.models import Book
from apps.catalog.serializers import BookListSerializer

from .models import ReadingProgress, Shelf, ShelfBook


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