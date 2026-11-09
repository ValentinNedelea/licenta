from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (GoalViewSet, ReadingProgressViewSet, SessionViewSet, ShelfViewSet,
                    StatsOverviewView, StreakView)

router = SimpleRouter()
router.register("shelves", ShelfViewSet, basename="shelf")
router.register("progress", ReadingProgressViewSet, basename="progress")
router.register("sessions", SessionViewSet, basename="session")
router.register("goals", GoalViewSet, basename="goal")

urlpatterns = router.urls + [
    path("streak/", StreakView.as_view()),
    path("stats/overview/", StatsOverviewView.as_view()),
]