from rest_framework.routers import DefaultRouter

from .views import AuthorViewSet, BookViewSet, GenreViewSet

router = DefaultRouter()
router.register("books", BookViewSet, basename="book")
router.register("authors", AuthorViewSet, basename="author")
router.register("genres", GenreViewSet, basename="genre")

urlpatterns = router.urls