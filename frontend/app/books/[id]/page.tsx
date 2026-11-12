"use client";

import { use, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Book, authorNames, coverOf, genreNames, ratingOf } from "@/lib/types";
import Stars from "@/components/Stars";
import Cover from "@/components/Cover";
import ShelfButton from "@/components/ShelfButton";
import Reviews from "@/components/Reviews";

export default function BookPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [book, setBook] = useState<Book | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api<Book>(`/api/books/${id}/`)
      .then(setBook)
      .catch(() => setError(true));
  }, [id]);

  if (error) return <p>Cartea nu a fost găsită.</p>;
  if (!book) return <p className="text-stone-500">Se încarcă...</p>;

  const cover = coverOf(book);
  const rating = ratingOf(book);

  return (
    <>
      <div className="flex flex-col gap-6 sm:flex-row">
        <div className="shrink-0">
          <Cover
            src={cover}
            alt={book.title}
            className="h-72 w-48 rounded shadow"
          />
        </div>

        <div>
          <h1 className="text-3xl font-bold">{book.title}</h1>
          {book.subtitle && (
            <p className="text-lg text-stone-600">{book.subtitle}</p>
          )}
          <p className="mt-1 text-stone-700">
            de {authorNames(book) || "autor necunoscut"}
          </p>

          {rating && (
            <p className="mt-2 flex items-center gap-2">
              <Stars value={rating.value} />
              <span className="font-semibold">{rating.value.toFixed(2)}</span>
              <span className="text-sm text-stone-500">
                ({rating.count.toLocaleString("ro-RO")} rating-uri
                {rating.external ? ", Goodreads/dataset" : ""})
              </span>
            </p>
          )}

          <div className="mt-3 flex flex-wrap gap-2">
            {genreNames(book).map((g) => (
              <span
                key={g}
                className="rounded-full bg-amber-100 px-3 py-0.5 text-xs text-amber-900"
              >
                {g}
              </span>
            ))}
          </div>

          <ShelfButton bookId={book.id} />

          <p className="mt-3 text-sm text-stone-500">
            {book.page_count ? `${book.page_count} pagini` : ""}
            {book.page_count && book.publication_date ? " · " : ""}
            {book.publication_date
              ? `publicată ${String(book.publication_date).slice(0, 4)}`
              : ""}
            {book.isbn13 ? ` · ISBN ${book.isbn13}` : ""}
          </p>

          {book.description && (
            <p className="mt-4 whitespace-pre-line leading-relaxed">
              {book.description}
            </p>
          )}
        </div>
      </div>

      <Reviews bookId={book.id} />
    </>
  );
}
