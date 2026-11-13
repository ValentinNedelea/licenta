from django.conf import settings
from django.db import models


class DatasetRating(models.Model):
    """Rating-uri din dataset-uri publice (Goodbooks-10k), folosite la antrenarea recomandărilor.
    Nu sunt rating-urile utilizatorilor aplicației."""

    dataset = models.CharField(max_length=20)  # goodbooks10k | bookcrossing
    external_user_id = models.CharField(max_length=32)
    book = models.ForeignKey("catalog.Book", on_delete=models.CASCADE, related_name="dataset_ratings")
    rating = models.SmallIntegerField()

    class Meta:
        db_table = "dataset_ratings"
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "external_user_id", "book"], name="uniq_dataset_user_book"
            ),
        ]
        indexes = [
            models.Index(fields=["book"], name="dsr_book_idx"),
        ]

    def __str__(self):
        return f"{self.dataset}:{self.external_user_id} -> {self.book_id} = {self.rating}"


class RecommendationModel(models.Model):
    TYPES = [
        ("content_based", "Content-based"),
        ("collaborative", "Collaborative"),
        ("hybrid", "Hybrid"),
        ("popularity", "Popularity"),
    ]

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPES)
    version = models.CharField(max_length=30, blank=True)
    params = models.JSONField(default=dict, blank=True)
    metrics = models.JSONField(default=dict, blank=True)  # Precision@K, Recall@K, NDCG
    trained_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "recommendation_models"

    def __str__(self):
        return f"{self.name} ({self.type}) v{self.version}"


class Recommendation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendations")
    book = models.ForeignKey("catalog.Book", on_delete=models.CASCADE, related_name="+")
    model = models.ForeignKey(RecommendationModel, on_delete=models.CASCADE, related_name="recommendations")
    score = models.FloatField()
    rank = models.SmallIntegerField()
    explanation = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recommendations"
        constraints = [
            models.UniqueConstraint(fields=["user", "book", "model"], name="uniq_reco_user_book_model"),
        ]
        ordering = ["rank"]

class BookSimilarity(models.Model):
    """Cei mai apropiați vecini ai unei cărți, calculați de un model de recomandare."""

    model = models.ForeignKey(RecommendationModel, on_delete=models.CASCADE, related_name="similarities")
    book = models.ForeignKey("catalog.Book", on_delete=models.CASCADE, related_name="+")
    similar_book = models.ForeignKey("catalog.Book", on_delete=models.CASCADE, related_name="+")
    score = models.FloatField()
    rank = models.SmallIntegerField()

    class Meta:
        db_table = "book_similarities"
        constraints = [
            models.UniqueConstraint(fields=["model", "book", "similar_book"], name="uniq_book_similarity"),
        ]
        indexes = [
            models.Index(fields=["model", "book", "rank"], name="bsim_lookup_idx"),
        ]