from rest_framework.routers import SimpleRouter

from .views import ReadingProgressViewSet, ShelfViewSet

router = SimpleRouter()
router.register("shelves", ShelfViewSet, basename="shelf")
router.register("progress", ReadingProgressViewSet, basename="progress")

urlpatterns = router.urls