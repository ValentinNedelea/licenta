from rest_framework import viewsets

from .models import Author, Book, Genre
from .serializers import (AuthorSerializer, BookDetailSerializer,
                          BookListSerializer, GenreSerializer)


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    search_fields = ["title", "subtitle", "isbn13", "authors__name"]
    ordering_fields = ["title", "avg_rating", "rating_count", "publication_date"]
    ordering = ["title"]

    def get_queryset(self):
        qs = (Book.objects
              .select_related("series")
              .prefetch_related("bookauthor_set__author", "genres", "tags"))
        genre = self.request.query_params.get("genre")      # ?genre=science-fiction
        author = self.request.query_params.get("author")    # ?author=3
        if genre:
            qs = qs.filter(genres__slug=genre)
        if author:
            qs = qs.filter(authors__id=author)
        return qs.distinct()

    def get_serializer_class(self):
        return BookDetailSerializer if self.action == "retrieve" else BookListSerializer


class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Author.objects.all().order_by("name")
    serializer_class = AuthorSerializer
    search_fields = ["name"]


class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Genre.objects.all().order_by("name")
    serializer_class = GenreSerializer
    search_fields = ["name"]