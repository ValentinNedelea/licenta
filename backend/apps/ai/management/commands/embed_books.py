import time

import numpy as np
from django.core.management.base import BaseCommand
from fastembed import TextEmbedding

from apps.ai.models import BookEmbedding
from apps.catalog.models import Book

MODEL = "BAAI/bge-small-en-v1.5"  # 384 dimensiuni


def book_text(b):
    authors = ", ".join(a.name for a in b.authors.all())
    genres = ", ".join(g.name for g in b.genres.all())
    tags = ", ".join(t.name for t in list(b.tags.all())[:15])
    parts = [b.title or "", f"by {authors}" if authors else "", f"Genres: {genres}" if genres else "",
             f"Tags: {tags}" if tags else "", (b.description or "")[:1500]]
    return ". ".join(p for p in parts if p)


class Command(BaseCommand):
    help = "Calculează embeddings pentru cărți (titlu, autori, genuri, taguri, descriere)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Doar primele N cărți (test)")
        parser.add_argument("--batch", type=int, default=64)

    def handle(self, *args, **o):
        t0 = time.time()
        self.stdout.write(f"Încarc modelul {MODEL} (la prima rulare se descarcă)...")
        model = TextEmbedding(MODEL)

        qs = Book.objects.prefetch_related("authors", "genres", "tags").order_by("id")
        if o["limit"]:
            qs = qs[: o["limit"]]
        books = list(qs)
        self.stdout.write(f"{len(books):,} cărți de procesat.")

        done = 0
        for i in range(0, len(books), o["batch"]):
            chunk = books[i : i + o["batch"]]
            vecs = np.array(list(model.embed([book_text(b) for b in chunk])), dtype=np.float32)
            vecs /= np.maximum(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-9)
            BookEmbedding.objects.bulk_create(
                [BookEmbedding(book=b, embedding=v.tolist(), model_name=MODEL) for b, v in zip(chunk, vecs)],
                update_conflicts=True,
                unique_fields=["book"],
                update_fields=["embedding", "model_name"],
            )
            done += len(chunk)
            if (i // o["batch"]) % 10 == 0:
                self.stdout.write(f"  {done:,}/{len(books):,} ({time.time() - t0:.0f}s)")

        self.stdout.write(self.style.SUCCESS(f"Gata: {done:,} embeddings în {time.time() - t0:.0f}s."))