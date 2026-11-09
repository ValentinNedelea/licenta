from django.db.models import Count
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import ReadingProgress, Shelf, ShelfBook
from .serializers import (AddBookSerializer, ReadingProgressSerializer,
                          SetStatusSerializer, ShelfBookSerializer, ShelfSerializer)


class ShelfViewSet(viewsets.ModelViewSet):
    serializer_class = ShelfSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return (Shelf.objects.filter(user=self.request.user)
                .annotate(books_count=Count("shelfbook")))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        shelf = self.get_object()
        if shelf.kind != Shelf.Kind.CUSTOM:
            return Response({"detail": "Rafturile implicite nu pot fi șterse."},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get"])
    def books(self, request, pk=None):
        shelf = self.get_object()
        entries = (ShelfBook.objects.filter(shelf=shelf)
                   .select_related("book")
                   .prefetch_related("book__bookauthor_set__author")
                   .order_by("position", "-added_at"))
        page = self.paginate_queryset(entries)
        serializer = ShelfBookSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"], url_path="add-book",
            serializer_class=AddBookSerializer)
    def add_book(self, request, pk=None):
        shelf = self.get_object()
        data = AddBookSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        book = data.validated_data["book"]

        # rafturile de stare se gestionează prin progresul de citire
        if shelf.kind in services.KIND_TO_STATUS:
            progress = services.set_status(request.user, book, services.KIND_TO_STATUS[shelf.kind])
            return Response(ReadingProgressSerializer(progress).data)

        _, created = ShelfBook.objects.get_or_create(shelf=shelf, book=book)
        return Response({"detail": "Carte adăugată."},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["delete"], url_path=r"books/(?P<book_id>\d+)")
    def remove_book(self, request, pk=None, book_id=None):
        shelf = self.get_object()
        if shelf.kind in services.KIND_TO_STATUS:
            progress = services.latest_progress(request.user, book_id)
            if progress and progress.status == services.KIND_TO_STATUS[shelf.kind]:
                services.delete_progress(progress)
                return Response(status=status.HTTP_204_NO_CONTENT)
        ShelfBook.objects.filter(shelf=shelf, book_id=book_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReadingProgressViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                             mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                             viewsets.GenericViewSet):
    serializer_class = ReadingProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = (ReadingProgress.objects.filter(user=self.request.user)
              .select_related("book")
              .prefetch_related("book__bookauthor_set__author")
              .order_by("-updated_at"))
        st = self.request.query_params.get("status")
        book = self.request.query_params.get("book")
        if st:
            qs = qs.filter(status=st)
        if book:
            qs = qs.filter(book_id=book)
        return qs

    def perform_destroy(self, instance):
        services.delete_progress(instance)

    @action(detail=False, methods=["post"], url_path="set-status",
            serializer_class=SetStatusSerializer)
    def set_status(self, request):
        data = SetStatusSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        progress = services.set_status(
            request.user, data.validated_data["book"], data.validated_data["status"])
        return Response(ReadingProgressSerializer(progress).data)