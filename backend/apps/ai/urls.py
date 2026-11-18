from django.urls import path

from .views import RecommendationsView, SimilarBooksView

urlpatterns = [
    path("books/<int:book_id>/similar/", SimilarBooksView.as_view()),
    path("recommendations/", RecommendationsView.as_view()),
]