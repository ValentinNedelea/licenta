from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.serializers import BookListSerializer

from .models import BookSimilarity
from .recommend import active_model, recommend_for_user


class SimilarBooksView(APIView):
    """Cărți similare (model collaborative activ)."""

    permission_classes = [AllowAny]

    def get(self, request, book_id):
        model = active_model()
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


class RecommendationsView(APIView):
    """„Recomandate pentru tine”: din recenziile și rafturile utilizatorului."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            limit = min(int(request.query_params.get("limit", 12)), 30)
        except ValueError:
            limit = 12
        items = recommend_for_user(request.user, limit)
        data = BookListSerializer([i["book"] for i in items], many=True, context={"request": request}).data
        return Response(
            [
                {**d, "score": None if i["score"] is None else round(i["score"], 4), "reason": i["reason"]}
                for d, i in zip(data, items)
            ]
        )