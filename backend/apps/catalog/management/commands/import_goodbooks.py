import ast
import csv
import re
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count
from django.utils.text import slugify

from apps.catalog.models import Author, Book, BookAuthor, BookGenre, Genre

SOURCE = "goodbooks10k"
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%B %d %Y", "%b %d %Y", "%B %Y", "%Y"]


def get(row, *names):
    """Prima valoare nevidă dintre coloanele date."""
    for name in names:
        value = (row.get(name) or "").strip()
        if value and value.lower() != "nan":
            return value
    return ""


def parse_list(value):
    """Acceptă "['A', 'B']" sau "A, B"."""
    if not value:
        return []
    text = value.strip()
    if text.startswith("["):
        try:
            return [str(i).strip() for i in ast.literal_eval(text) if str(i).strip()]
        except (ValueError, SyntaxError):
            text = text.strip("[]")
    return [p.strip(" '\"") for p in text.split(",") if p.strip(" '\"")]


def parse_date(text, year_fallback):
    if text:
        t = " ".join(re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text.replace(",", " ")).split())
        if re.match(r"\d{4}-\d{2}-\d{2}", t):
            t = t[:10]
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(t, fmt).date()
            except ValueError:
                pass
    try:
        year = int(float(year_fallback))
        if 1 <= year <= 9999:
            return date(year, 1, 1)
    except (TypeError, ValueError):
        pass
    return None


def to_int(value):
    try:
        number = int(float(value))
        return number if number > 0 else None
    except (TypeError, ValueError):
        return None


def parse_row(row):
    title = get(row, "title", "original_title")
    ext_id = get(row, "book_id")
    if not title or not ext_id:
        return None

    # în dataset isbn13 e adesea stricat (notație științifică): îl păstrăm doar dacă e valid
    isbn13 = get(row, "isbn13")
    isbn13 = isbn13 if re.fullmatch(r"\d{13}", isbn13) else None
    isbn10 = get(row, "isbn")
    if isbn10.isdigit() and len(isbn10) == 9:
        isbn10 = isbn10.zfill(10)
    isbn10 = isbn10.upper() if re.fullmatch(r"\d{9}[\dXx]", isbn10) else ""

    cover = get(row, "image_url")
    if not cover or "nophoto" in cover:
        isbn = isbn13 or isbn10
        # Open Library oferă coperte după ISBN; default=false => 404 dacă nu există
        cover = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false" if isbn else ""

    try:
        avg = round(float(get(row, "average_rating")), 2)
    except ValueError:
        avg = None

    authors = list(dict.fromkeys(parse_list(get(row, "authors"))))
    genres = list(dict.fromkeys(parse_list(get(row, "genres"))))

    return {
        "external_id": ext_id,
        "authors": authors,
        "genres": genres,
        "fields": {
            "title": title[:500],
            "description": " ".join(get(row, "description").split()),
            "isbn10": isbn10,
            "isbn13": isbn13,
            "cover_img_url": cover[:500],
            "publication_date": parse_date(get(row, "publishDate"), get(row, "original_publication_year")),
            "language": get(row, "language_code")[:10],
            "page_count": to_int(get(row, "pages")),
            "external_avg_rating": avg,
            "external_rating_count": to_int(get(row, "work_ratings_count", "ratings_count")) or 0,
        },
    }


class Command(BaseCommand):
    help = "Importă cărți din books_enriched.csv (Goodbooks-10k extended). Poate fi rulată de mai multe ori."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--limit", type=int, default=0, help="Importă doar primele N cărți")
        parser.add_argument("--dry-run", action="store_true", help="Doar afișează ce s-ar importa")

    def handle(self, *args, **opts):
        try:
            f = open(opts["csv_path"], newline="", encoding="utf-8-sig")
        except OSError as exc:
            raise CommandError(f"Nu pot deschide fișierul: {exc}")
        with f:
            reader = csv.DictReader(f)
            self.stdout.write("Coloane găsite: " + ", ".join(reader.fieldnames or []))
            rows = list(reader)
        if opts["limit"]:
            rows = rows[: opts["limit"]]

        parsed = [d for d in (parse_row(r) for r in rows) if d]
        self.stdout.write(f"{len(parsed)} cărți valide din {len(rows)} rânduri.")

        if opts["dry_run"]:
            for d in parsed[:3]:
                self.stdout.write(f"\n{d['fields']['title']}\n  autori: {d['authors']}\n"
                                  f"  genuri: {d['genres']}\n  {d['fields']}")
            return

        authors_cache, genres_cache = {}, {}
        created = updated = 0

        with transaction.atomic():
            for i, d in enumerate(parsed, 1):
                fields = d["fields"]
                if fields["isbn13"] and Book.objects.filter(isbn13=fields["isbn13"]).exclude(
                        external_source=SOURCE, external_id=d["external_id"]).exists():
                    fields["isbn13"] = None          # ISBN duplicat în dataset
                book, was_created = Book.objects.update_or_create(
                    external_source=SOURCE, external_id=d["external_id"], defaults=fields)
                created += was_created
                updated += not was_created

                BookAuthor.objects.filter(book=book).delete()
                for pos, name in enumerate(d["authors"]):
                    author = authors_cache.get(name)
                    if author is None:
                        author = (Author.objects.filter(name=name).first()
                                  or Author.objects.create(name=name[:255]))
                        authors_cache[name] = author
                    BookAuthor.objects.create(book=book, author=author, role="author", position=pos)

                BookGenre.objects.filter(book=book).delete()
                for name in d["genres"]:
                    slug = slugify(name)[:120]
                    if not slug:
                        continue
                    genre = genres_cache.get(slug)
                    if genre is None:
                        genre, _ = Genre.objects.get_or_create(slug=slug, defaults={"name": name[:100]})
                        genres_cache[slug] = genre
                    BookGenre.objects.get_or_create(book=book, genre=genre)

                if i % 1000 == 0:
                    self.stdout.write(f"  ... {i} cărți procesate")

            for genre in Genre.objects.annotate(n=Count("books")):
                Genre.objects.filter(pk=genre.pk).update(book_count=genre.n)

        self.stdout.write(self.style.SUCCESS(
            f"Gata: {created} cărți noi, {updated} actualizate."))