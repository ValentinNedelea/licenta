from django.urls import path

from .views import SimilarBooksView

urlpatterns = [
    path("books/<int:book_id>/similar/", SimilarBooksView.as_view()),
]