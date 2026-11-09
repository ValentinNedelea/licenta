from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import ReadingGoal, ReadingProgress, ReadingSession, Shelf, ShelfBook, UserStreak
from .serializers import (AddBookSerializer, ReadingGoalSerializer,
                          ReadingProgressSerializer, ReadingSessionSerializer,
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
    
class SessionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                     mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    serializer_class = ReadingSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ["started_at", "duration_seconds"]
    ordering = ["-started_at"]

    def get_queryset(self):
        qs = ReadingSession.objects.filter(user=self.request.user).select_related("book")
        p = self.request.query_params
        if p.get("book"):
            qs = qs.filter(book_id=p["book"])
        if p.get("from") and parse_date(p["from"]):
            qs = qs.filter(started_at__date__gte=parse_date(p["from"]))
        if p.get("to") and parse_date(p["to"]):
            qs = qs.filter(started_at__date__lte=parse_date(p["to"]))
        return qs

    def perform_destroy(self, instance):
        user = instance.user
        instance.delete()
        services.rebuild_streak(user)


class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = ReadingGoalSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = ReadingGoal.objects.filter(user=self.request.user).order_by("-year", "goal_type")
        if self.request.query_params.get("year"):
            qs = qs.filter(year=self.request.query_params["year"])
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class StreakView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        streak = UserStreak.objects.filter(user=request.user).first()
        return Response(services.streak_summary(streak))


class StatsOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            year = int(request.query_params.get("year", timezone.localdate().year))
        except ValueError:
            return Response({"detail": "year trebuie să fie un număr."},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(services.stats_overview(request.user, year))