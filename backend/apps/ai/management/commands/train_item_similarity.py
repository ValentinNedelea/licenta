import time

import numpy as np
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from scipy import sparse

from apps.ai.models import BookSimilarity, DatasetRating, RecommendationModel

DATASET = "goodbooks10k"
MODEL_NAME = "item-knn-adjusted-cosine"


class Command(BaseCommand):
    help = "Calculează cărțile similare (item-item, cosinus ajustat) din dataset_ratings."

    def add_arguments(self, parser):
        parser.add_argument("--k", type=int, default=30, help="Vecini păstrați pentru fiecare carte")
        parser.add_argument("--chunk", type=int, default=500, help="Câte cărți se procesează deodată")

    def handle(self, *args, **opts):
        k, chunk = opts["k"], opts["chunk"]
        t0 = time.time()

        self.stdout.write("Citesc rating-urile...")
        users, ui, bi, rt = {}, [], [], []
        qs = DatasetRating.objects.filter(dataset=DATASET).values_list("external_user_id", "book_id", "rating")
        for u, b, r in qs.iterator(chunk_size=200_000):
            ui.append(users.setdefault(u, len(users)))
            bi.append(b)
            rt.append(r)
        if not rt:
            raise CommandError("Nu există rating-uri. Rulează întâi import_ratings.")

        ui = np.array(ui, dtype=np.int32)
        bi = np.array(bi, dtype=np.int64)
        rt = np.array(rt, dtype=np.float32)
        book_ids, bidx = np.unique(bi, return_inverse=True)
        n_users, n_books = len(users), len(book_ids)
        self.stdout.write(f"  {len(rt):,} rating-uri, {n_users:,} utilizatori, {n_books:,} cărți ({time.time() - t0:.0f}s)")

        # cosinus ajustat: scădem media fiecărui utilizator
        sums = np.bincount(ui, weights=rt, minlength=n_users)
        counts = np.bincount(ui, minlength=n_users)
        mean = (sums / np.maximum(counts, 1)).astype(np.float32)
        centered = rt - mean[ui]

        X = sparse.csr_matrix((centered, (bidx, ui)), shape=(n_books, n_users), dtype=np.float32)
        norms = np.sqrt(np.asarray(X.multiply(X).sum(axis=1)).ravel())
        norms[norms == 0] = 1.0
        X = (sparse.diags((1.0 / norms).astype(np.float32)) @ X).tocsr()
        XT = X.T.tocsr()

        self.stdout.write("Calculez similaritățile...")
        rows = []
        for start in range(0, n_books, chunk):
            end = min(start + chunk, n_books)
            S = (X[start:end] @ XT).toarray()
            for i in range(end - start):
                S[i, start + i] = -1.0  # o carte nu e vecină cu ea însăși
            kk = min(k, n_books - 1)
            top = np.argpartition(-S, kk, axis=1)[:, :kk]
            for i in range(end - start):
                order = top[i][np.argsort(-S[i, top[i]])]
                for rank, j in enumerate(order, start=1):
                    score = float(S[i, j])
                    if score > 0:
                        rows.append((int(book_ids[start + i]), int(book_ids[j]), score, rank))
            self.stdout.write(f"  {end:,}/{n_books:,} cărți ({time.time() - t0:.0f}s)")

        with transaction.atomic():
            model, _ = RecommendationModel.objects.get_or_create(
                name=MODEL_NAME, type="collaborative", defaults={"version": "1"}
            )
            BookSimilarity.objects.filter(model=model)._raw_delete(using="default")
            BookSimilarity.objects.bulk_create(
                [BookSimilarity(model=model, book_id=b, similar_book_id=s, score=sc, rank=r) for b, s, sc, r in rows],
                batch_size=10_000,
            )
            model.params = {"k": k, "dataset": DATASET, "similarity": "adjusted_cosine"}
            model.trained_at = timezone.now()
            model.is_active = True
            model.save()
            RecommendationModel.objects.filter(type="collaborative").exclude(pk=model.pk).update(is_active=False)

        self.stdout.write(self.style.SUCCESS(f"Gata: {len(rows):,} perechi salvate în {time.time() - t0:.0f}s."))