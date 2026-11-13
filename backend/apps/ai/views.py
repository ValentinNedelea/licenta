from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.serializers import BookListSerializer

from .models import BookSimilarity, RecommendationModel


class SimilarBooksView(APIView):
    """Cărți similare (model collaborative activ)."""

    permission_classes = [AllowAny]

    def get(self, request, book_id):
        model = (
            RecommendationModel.objects.filter(is_active=True, type="collaborative")
            .order_by("-trained_at")
            .first()
        )
        if model is None:
            return Response([])
        try:
            limit = min(int(request.query_params.get("limit", 10)), 30)
        except ValueError:
            limit = 10
        sims = list(
            BookSimilarity.objects.filter(model=model, book_id=book_id)
            .select_related("similar_book")
            .prefetch_related("similar_book__bookauthor_set__author")
            .order_by("rank")[:limit]
        )
        data = BookListSerializer([s.similar_book for s in sims], many=True, context={"request": request}).data
        return Response([{**d, "similarity": round(s.score, 4)} for d, s in zip(data, sims)])