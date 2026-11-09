from rest_framework import serializers

from apps.accounts.serializers import UserMiniSerializer
from apps.catalog.models import Book

from .models import BookReview


class ReviewSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = BookReview
        fields = ("id", "user", "book", "rating", "review_text", "has_spoilers",
                  "helpful_count", "comments_count", "liked_by_me",
                  "created_at", "updated_at")
        read_only_fields = ("helpful_count", "comments_count")

    def get_liked_by_me(self, review):
        return getattr(review, "liked_by_me", False)

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
        validated_data.pop("book", None)   # cartea nu se schimbă după creare
        return super().update(instance, validated_data)