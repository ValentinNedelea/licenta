from rest_framework import serializers

from .models import Author, Book, Genre, Series, Tag


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ("id", "name", "bio", "avatar_url", "country", "birth_date", "death_date")


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name", "slug", "parent_genre", "book_count")


class SeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = ("id", "name", "description")


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


def authors_of(book):
    return [
        {"id": ba.author_id, "name": ba.author.name, "role": ba.role}
        for ba in book.bookauthor_set.all()
    ]


class BookListSerializer(serializers.ModelSerializer):
    """Varianta scurtă, pentru liste și rezultate de căutare."""
    authors = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ("id", "title", "subtitle", "cover_img_url", "authors",
                  "avg_rating", "rating_count", "external_avg_rating", "external_rating_count", "publication_date")

    def get_authors(self, book):
        return authors_of(book)


class BookDetailSerializer(serializers.ModelSerializer):
    """Varianta completă, pentru pagina cărții."""
    authors = serializers.SerializerMethodField()
    genres = GenreSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    series = SeriesSerializer(read_only=True)

    class Meta:
        model = Book
        fields = ("id", "title", "subtitle", "description", "isbn10", "isbn13",
                  "cover_img_url", "publication_date", "language", "page_count",
                  "publisher", "series", "series_position", "avg_rating",
                  "rating_count", "external_avg_rating", "external_rating_count", "authors", "genres", "tags")

    def get_authors(self, book):
        return authors_of(book)