import csv
import time

from django.core.management.base import BaseCommand, CommandError

from apps.ai.models import DatasetRating
from apps.catalog.models import Book

DATASET = "goodbooks10k"
FLUSH_EVERY = 50_000


class Command(BaseCommand):
    help = "Importă rating-urile Goodbooks-10k (ratings.csv) în dataset_ratings."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Calea către ratings.csv")
        parser.add_argument("--limit", type=int, default=0, help="Citește doar primele N rânduri (test)")
        parser.add_argument("--replace", action="store_true", help="Șterge întâi rating-urile existente din acest dataset")

    def handle(self, *args, **opts):
        mapping = {
            str(ext): pk
            for ext, pk in Book.objects.filter(external_source=DATASET).values_list("external_id", "id")
        }
        if not mapping:
            raise CommandError("Nu există cărți importate din Goodbooks-10k în baza de date.")

        if opts["replace"]:
            DatasetRating.objects.filter(dataset=DATASET)._raw_delete(using="default")
            self.stdout.write("Rating-urile vechi au fost șterse.")

        limit = opts["limit"]
        batch, read, skipped = [], 0, 0
        started = time.time()

        with open(opts["path"], newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if limit and read >= limit:
                    break
                read += 1
                book_pk = mapping.get(row["book_id"])
                if book_pk is None:
                    skipped += 1
                    continue
                batch.append(
                    DatasetRating(
                        dataset=DATASET,
                        external_user_id=row["user_id"],
                        book_id=book_pk,
                        rating=int(row["rating"]),
                    )
                )
                if len(batch) >= FLUSH_EVERY:
                    DatasetRating.objects.bulk_create(batch, ignore_conflicts=True, batch_size=10_000)
                    batch = []
                    self.stdout.write(f"  {read:,} rânduri citite ({time.time() - started:.0f}s)")

        if batch:
            DatasetRating.objects.bulk_create(batch, ignore_conflicts=True, batch_size=10_000)

        total = DatasetRating.objects.filter(dataset=DATASET).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Gata: {read:,} rânduri citite, {skipped:,} sărite (carte necunoscută). "
                f"În baza de date: {total:,} rating-uri. Durată: {time.time() - started:.0f}s."
            )
        )