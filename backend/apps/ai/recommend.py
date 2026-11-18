from collections import defaultdict

from apps.catalog.models import Book
from apps.library.models import ReadingProgress, ShelfBook
from apps.reviews.models import BookReview

from .models import BookSimilarity, RecommendationModel

# cât de mult contează o carte de pe raft, când utilizatorul n-a notat-o
SHELF_WEIGHTS = {"read": 0.5, "currently_reading": 0.5}
FAVORITE_BONUS = 1.0


def active_model():
    return (
        RecommendationModel.objects.filter(is_active=True, type="collaborative")
        .order_by("-trained_at")
        .first()
    )


def user_evidence(user):
    """Întoarce (evidență, văzute).
    evidență: {book_id: pondere}, cât i-a plăcut utilizatorului cartea (pozitiv = a plăcut, negativ = nu)
    văzute: cărțile pe care nu mai are rost să i le recomandăm."""
    reviews = {b: float(r) for b, r in BookReview.objects.filter(user=user).values_list("book_id", "rating")}

    # nota se centrează pe media utilizatorului (dacă are destule note diferite), altfel pe 3
    values = list(reviews.values())
    mean = sum(values) / len(values) if len(values) >= 3 and len(set(values)) > 1 else 3.0
    evidence = {b: r - mean for b, r in reviews.items()}

    seen = set(reviews)
    for book_id, kind in ShelfBook.objects.filter(shelf__user=user).values_list("book_id", "shelf__kind"):
        seen.add(book_id)
        if book_id not in reviews:
            evidence[book_id] = evidence.get(book_id, 0.0) + SHELF_WEIGHTS.get(kind, 0.0)
        if kind == "favorites":
            evidence[book_id] = evidence.get(book_id, 0.0) + FAVORITE_BONUS
    seen |= set(ReadingProgress.objects.filter(user=user).values_list("book_id", flat=True))

    return {b: w for b, w in evidence.items() if w != 0}, seen


def recommend_for_user(user, limit=12):
    """Lista de recomandări: [{"book", "score", "reason"}]."""
    model = active_model()
    evidence, seen = user_evidence(user)
    results = []

    if model and evidence:
        scores = defaultdict(float)
        contrib = defaultdict(list)
        rows = BookSimilarity.objects.filter(model=model, book_id__in=list(evidence)).values_list(
            "book_id", "similar_book_id", "score"
        )
        for src, dst, sim in rows:
            if dst in seen:
                continue
            c = sim * evidence[src]
            scores[dst] += c
            contrib[dst].append((c, src))

        ranked = sorted(((sc, b) for b, sc in scores.items() if sc > 0), reverse=True)[:limit]
        books = {
            b.id: b
            for b in Book.objects.filter(id__in=[b for _, b in ranked]).prefetch_related("bookauthor_set__author")
        }
        src_ids = {max(contrib[b], key=lambda t: t[0])[1] for _, b in ranked}
        titles = dict(Book.objects.filter(id__in=src_ids).values_list("id", "title"))
        for sc, b in ranked:
            best = max(contrib[b], key=lambda t: t[0])[1]
            results.append(
                {
                    "book": books[b],
                    "score": sc,
                    "reason": {"type": "similar_to", "book_id": best, "title": titles.get(best, "")},
                }
            )

    # completăm cu cele mai populare cărți, dacă nu avem destule recomandări
    if len(results) < limit:
        exclude = set(seen) | {r["book"].id for r in results}
        popular = (
            Book.objects.exclude(id__in=exclude)
            .order_by("-external_rating_count", "-external_avg_rating")
            .prefetch_related("bookauthor_set__author")[: limit - len(results)]
        )
        for b in popular:
            results.append({"book": b, "score": None, "reason": {"type": "popular"}})

    return results