from rest_framework import serializers

from apps.accounts.serializers import UserMiniSerializer
from apps.catalog.models import Book
from apps.catalog.serializers import BookListSerializer as BookSummarySerializer

from .models import BookList, BookListItem, BookReview, Quote, ReviewComment


class LikedByMeMixin(serializers.Serializer):
    liked_by_me = serializers.SerializerMethodField()

    def get_liked_by_me(self, obj):
        return getattr(obj, "liked_by_me", False)


# ------------------------------------------------------------ recenzii
class ReviewSerializer(LikedByMeMixin, serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())

    class Meta:
        model = BookReview
        fields = ("id", "user", "book", "rating", "review_text", "has_spoilers",
                  "helpful_count", "comments_count", "liked_by_me",
                  "created_at", "updated_at")
        read_only_fields = ("helpful_count", "comments_count")

    def validate(self, attrs):
        request = self.context["request"]
        if self.instance is None:
            if BookReview.objects.filter(user=request.user, book=attrs["book"]).exists():
                raise serializers.ValidationError("Ai scris deja o recenzie pentru această carte.")
            rating, text = attrs.get("rating"), attrs.get("review_text")
        else:
            rating = attrs.get("rating", self.instance.rating)
            text = attrs.get("review_text", self.instance.review_text)
        if rating is None and not text:
            raise serializers.ValidationError("Adaugă un rating sau un text.")
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop("book", None)
        return super().update(instance, validated_data)


# ------------------------------------------------------------ comentarii
class CommentSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    review = serializers.PrimaryKeyRelatedField(queryset=BookReview.objects.filter(is_hidden=False))
    is_deleted = serializers.SerializerMethodField()

    class Meta:
        model = ReviewComment
        fields = ("id", "review", "user", "parent_comment", "body", "is_deleted",
                  "created_at", "updated_at")

    def get_is_deleted(self, comment):
        return comment.deleted_at is not None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.deleted_at:
            data["body"] = ""          # firul de răspunsuri rămâne, textul dispare
        return data

    def validate(self, attrs):
        if self.instance and self.instance.deleted_at:
            raise serializers.ValidationError("Comentariul a fost șters.")
        review = attrs.get("review") or (self.instance.review if self.instance else None)
        parent = attrs.get("parent_comment")
        if parent and review and parent.review_id != review.id:
            raise serializers.ValidationError(
                {"parent_comment": "Răspunsul trebuie să fie la un comentariu din aceeași recenzie."})
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop("review", None)
        validated_data.pop("parent_comment", None)
        return super().update(instance, validated_data)


# ------------------------------------------------------------ citate
class QuoteSerializer(LikedByMeMixin, serializers.ModelSerializer):
    created_by_user = UserMiniSerializer(read_only=True)

    class Meta:
        model = Quote
        fields = ("id", "book", "author", "text", "page_number", "note",
                  "created_by_user", "is_public", "likes_count", "liked_by_me", "created_at")
        read_only_fields = ("likes_count",)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if not request or request.user.id != instance.created_by_user_id:
            data.pop("note", None)       # nota personală e vizibilă doar autorului
        return data

    def update(self, instance, validated_data):
        validated_data.pop("book", None)
        return super().update(instance, validated_data)


# ------------------------------------------------------------ liste
class BookListItemSerializer(serializers.ModelSerializer):
    book = BookSummarySerializer(read_only=True)

    class Meta:
        model = BookListItem
        fields = ("book", "position", "note", "added_at")


class ListSerializer(LikedByMeMixin, serializers.ModelSerializer):
    owner = UserMiniSerializer(source="owner_user", read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = BookList
        fields = ("id", "title", "description", "cover_img_url", "owner", "is_public",
                  "is_curated", "likes_count", "items_count", "liked_by_me",
                  "created_at", "updated_at")
        read_only_fields = ("is_curated", "likes_count")

    def get_items_count(self, obj):
        return obj.items_count if hasattr(obj, "items_count") else obj.items.count()


class ListDetailSerializer(ListSerializer):
    items = BookListItemSerializer(many=True, read_only=True)

    class Meta(ListSerializer.Meta):
        fields = ListSerializer.Meta.fields + ("items",)


class AddListItemSerializer(serializers.Serializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    note = serializers.CharField(required=False, allow_blank=True, default="")
    position = serializers.IntegerField(required=False, min_value=0)