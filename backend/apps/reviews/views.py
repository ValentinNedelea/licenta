from django.db.models import Count, Exists, Max, OuterRef, Prefetch, Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (BookList, BookListItem, BookListLike, BookReview, Quote,
                     QuoteLike, ReviewComment, ReviewLike)
from .permissions import IsOwnerOrReadOnly
from .serializers import (AddListItemSerializer, CommentSerializer,
                          ListDetailSerializer, ListSerializer, QuoteSerializer,
                          ReviewSerializer)

OWNER_OR_READ = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]


def with_liked(qs, user, like_model, like_field):
    """Adaugă liked_by_me (True/False) la fiecare rând, dintr-un singur query."""
    if user.is_authenticated:
        return qs.annotate(liked_by_me=Exists(
            like_model.objects.filter(**{like_field: OuterRef("pk"), "user": user})))
    return qs


def visible_to(qs, user, owner_field):
    """Public, plus ce a creat utilizatorul curent."""
    if user.is_authenticated:
        return qs.filter(Q(is_public=True) | Q(**{owner_field: user}))
    return qs.filter(is_public=True)


class LikeMixin:
    """POST /{id}/like/ apreciază, DELETE /{id}/like/ retrage aprecierea."""
    like_model = None
    like_field = None
    count_field = "likes_count"

    @action(detail=True, methods=["post", "delete"],
            permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        obj = self.get_object()
        lookup = {"user": request.user, self.like_field: obj}
        if request.method == "POST":
            _, created = self.like_model.objects.get_or_create(**lookup)
            code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        else:
            self.like_model.objects.filter(**lookup).delete()
            code = status.HTTP_200_OK
        obj.refresh_from_db()
        return Response({self.count_field: getattr(obj, self.count_field)}, status=code)


# ------------------------------------------------------------ recenzii
class ReviewViewSet(LikeMixin, viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = OWNER_OR_READ
    like_model, like_field, count_field = ReviewLike, "review", "helpful_count"
    ordering_fields = ["created_at", "helpful_count", "rating"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = with_liked(BookReview.objects.filter(is_hidden=False).select_related("user"),
                        user, ReviewLike, "review")
        p = self.request.query_params
        if p.get("book"):
            qs = qs.filter(book_id=p["book"])
        if p.get("user"):
            qs = qs.filter(user_id=p["user"])
        if p.get("mine") and user.is_authenticated:
            qs = qs.filter(user=user)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ------------------------------------------------------------ comentarii
class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = OWNER_OR_READ
    ordering = ["created_at"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = ReviewComment.objects.select_related("user")
        if self.request.query_params.get("review"):
            qs = qs.filter(review_id=self.request.query_params["review"])
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        # ștergere "soft": rândul rămâne, ca firul de răspunsuri să nu se rupă
        if instance.deleted_at is None:
            instance.deleted_at = timezone.now()
            instance.save(update_fields=["deleted_at"])


# ------------------------------------------------------------ citate
class QuoteViewSet(LikeMixin, viewsets.ModelViewSet):
    serializer_class = QuoteSerializer
    permission_classes = OWNER_OR_READ
    like_model, like_field, count_field = QuoteLike, "quote", "likes_count"
    search_fields = ["text"]
    ordering_fields = ["created_at", "likes_count"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = visible_to(Quote.objects.select_related("created_by_user"), user, "created_by_user")
        qs = with_liked(qs, user, QuoteLike, "quote")
        p = self.request.query_params
        if p.get("book"):
            qs = qs.filter(book_id=p["book"])
        if p.get("user"):
            qs = qs.filter(created_by_user_id=p["user"])
        if p.get("mine") and user.is_authenticated:
            qs = qs.filter(created_by_user=user)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by_user=self.request.user)


# ------------------------------------------------------------ liste
class BookListViewSet(LikeMixin, viewsets.ModelViewSet):
    permission_classes = OWNER_OR_READ
    like_model, like_field, count_field = BookListLike, "list", "likes_count"
    search_fields = ["title"]
    ordering_fields = ["created_at", "likes_count"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        return ListDetailSerializer if self.action == "retrieve" else ListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = visible_to(BookList.objects.select_related("owner_user"), user, "owner_user")
        qs = with_liked(qs, user, BookListLike, "list")
        qs = qs.annotate(items_count=Count("items", distinct=True))
        if self.action == "retrieve":
            qs = qs.prefetch_related(Prefetch(
                "items",
                queryset=(BookListItem.objects.select_related("book")
                          .prefetch_related("book__bookauthor_set__author")
                          .order_by("position"))))
        p = self.request.query_params
        if p.get("curated"):
            qs = qs.filter(is_curated=True)
        if p.get("owner"):
            qs = qs.filter(owner_user_id=p["owner"])
        if p.get("mine") and user.is_authenticated:
            qs = qs.filter(owner_user=user)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner_user=self.request.user, is_curated=False)

    @action(detail=True, methods=["post"], url_path="add-book",
            serializer_class=AddListItemSerializer)
    def add_book(self, request, pk=None):
        book_list = self.get_object()          # doar proprietarul trece de permisiuni
        data = AddListItemSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        position = data.validated_data.get("position")
        if position is None:
            last = book_list.items.aggregate(m=Max("position"))["m"]
            position = 0 if last is None else last + 1
        _, created = BookListItem.objects.get_or_create(
            list=book_list, book=data.validated_data["book"],
            defaults={"note": data.validated_data["note"], "position": position})
        return Response({"detail": "Carte adăugată." if created else "Cartea e deja în listă."},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["delete"], url_path=r"books/(?P<book_id>\d+)")
    def remove_book(self, request, pk=None, book_id=None):
        book_list = self.get_object()
        BookListItem.objects.filter(list=book_list, book_id=book_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)