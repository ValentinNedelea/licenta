from rest_framework.routers import SimpleRouter

from .views import BookListViewSet, CommentViewSet, QuoteViewSet, ReviewViewSet

router = SimpleRouter()
router.register("reviews", ReviewViewSet, basename="review")
router.register("comments", CommentViewSet, basename="comment")
router.register("quotes", QuoteViewSet, basename="quote")
router.register("lists", BookListViewSet, basename="booklist")

urlpatterns = router.urls