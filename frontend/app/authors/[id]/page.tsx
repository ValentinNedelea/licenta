"use client";

import { use, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Book, Paginated } from "@/lib/types";
import BookCard from "@/components/BookCard";

type Author = {
  id: number;
  name: string;
  bio: string;
  avatar_url: string;
  country: string;
  birth_date: string | null;
  death_date: string | null;
};

export default function AuthorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [author, setAuthor] = useState<Author | null>(null);
  const [books, setBooks] = useState<Paginated<Book> | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api<Author>(`/api/authors/${id}/`)
      .then(setAuthor)
      .catch(() => setError(true));
    api<Paginated<Book>>(`/api/books/?author=${id}`)
      .then(setBooks)
      .catch(() => setBooks(null));
  }, [id]);

  if (error) return <p>Autorul nu a fost găsit.</p>;
  if (!author) return <p className="text-stone-500">Se încarcă...</p>;

  return (
    <div>
      <div className="mb-6 flex gap-4">
        {author.avatar_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={author.avatar_url}
            alt=""
            className="h-28 w-28 rounded-full object-cover"
            referrerPolicy="no-referrer"
          />
        )}
        <div>
          <h1 className="text-3xl font-bold">{author.name}</h1>
          <p className="text-sm text-stone-500">
            {[
              author.country,
              author.birth_date && `născut ${author.birth_date.slice(0, 4)}`,
              author.death_date && `decedat ${author.death_date.slice(0, 4)}`,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          {author.bio && (
            <p className="mt-3 whitespace-pre-line leading-relaxed">
              {author.bio}
            </p>
          )}
        </div>
      </div>

      <h2 className="mb-3 text-xl font-bold">
        Cărți {books ? `(${books.count})` : ""}
      </h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {books?.results.map((b) => (
          <BookCard key={b.id} book={b} />
        ))}
      </div>
      {books && books.results.length === 0 && (
        <p className="text-stone-500">Nu am găsit cărți pentru acest autor.</p>
      )}
    </div>
  );
}
