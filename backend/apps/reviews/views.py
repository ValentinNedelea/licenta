from django.db.models import Exists, OuterRef
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import BookReview, ReviewLike
from .permissions import IsOwnerOrReadOnly
from .serializers import ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    ordering_fields = ["created_at", "helpful_count", "rating"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = BookReview.objects.filter(is_hidden=False).select_related("user")
        user = self.request.user
        if user.is_authenticated:
            qs = qs.annotate(liked_by_me=Exists(
                ReviewLike.objects.filter(review=OuterRef("pk"), user=user)))
        params = self.request.query_params
        if params.get("book"):
            qs = qs.filter(book_id=params["book"])
        if params.get("user"):
            qs = qs.filter(user_id=params["user"])
        if params.get("mine") and user.is_authenticated:
            qs = qs.filter(user=user)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post", "delete"],
            permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        review = self.get_object()
        if request.method == "POST":
            _, created = ReviewLike.objects.get_or_create(user=request.user, review=review)
            code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        else:
            ReviewLike.objects.filter(user=request.user, review=review).delete()
            code = status.HTTP_200_OK
        review.refresh_from_db()
        return Response({"helpful_count": review.helpful_count}, status=code)