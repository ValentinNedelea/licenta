"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Book, Genre, Paginated } from "@/lib/types";
import BookCard from "@/components/BookCard";

const PAGE_SIZE = 20;

export default function BooksPage() {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [genre, setGenre] = useState("");
  const [ordering, setOrdering] = useState("");
  const [page, setPage] = useState(1);
  const [genres, setGenres] = useState<Genre[]>([]);
  const [data, setData] = useState<Paginated<Book> | null>(null);
  const [loading, setLoading] = useState(true);

  // genurile pentru filtru (primele 100, cele mai mari întâi)
  useEffect(() => {
    api<Paginated<Genre> | Genre[]>("/api/genres/?page_size=100")
      .then((r) => setGenres(Array.isArray(r) ? r : r.results))
      .catch(() => setGenres([]));
  }, []);

  // așteaptă 400 ms după ultima tastă înainte de căutare
  useEffect(() => {
    const t = setTimeout(() => {
      setQuery(search);
      setPage(1);
    }, 400);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    const params = new URLSearchParams({ page: String(page) });
    if (query) params.set("search", query);
    if (genre) params.set("genre", genre);
    if (ordering) params.set("ordering", ordering);
    setLoading(true);
    api<Paginated<Book>>(`/api/books/?${params}`)
      .then(setData)
      .finally(() => setLoading(false));
  }, [query, genre, ordering, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;

  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">Cărți</h1>

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          className="min-w-[220px] flex-1 rounded border bg-white px-3 py-2"
          placeholder="Caută după titlu, autor sau ISBN..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="rounded border bg-white px-3 py-2"
          value={genre}
          onChange={(e) => {
            setGenre(e.target.value);
            setPage(1);
          }}
        >
          <option value="">Toate genurile</option>
          {genres.map((g) => (
            <option key={g.id} value={g.slug ?? g.id}>
              {" "}
              {g.name}
            </option>
          ))}
        </select>
        <select
          className="rounded border bg-white px-3 py-2"
          value={ordering}
          onChange={(e) => {
            setOrdering(e.target.value);
            setPage(1);
          }}
        >
          <option value="">Implicit</option>
          <option value="-external_avg_rating">Rating (mare → mic)</option>
          <option value="-external_rating_count">Cele mai populare</option>
          <option value="title">Titlu (A → Z)</option>
        </select>
      </div>

      {data && (
        <p className="mb-3 text-sm text-stone-500">
          {data.count.toLocaleString("ro-RO")} rezultate
        </p>
      )}

      <div
        className={`grid gap-3 sm:grid-cols-2 ${loading ? "opacity-50" : ""}`}
      >
        {data?.results.map((b) => (
          <BookCard key={b.id} book={b} />
        ))}
      </div>

      {data && data.results.length === 0 && (
        <p className="py-8 text-center text-stone-500">Nicio carte găsită.</p>
      )}

      <div className="mt-6 flex items-center justify-center gap-4">
        <button
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
          className="rounded border bg-white px-3 py-1 disabled:opacity-40"
        >
          ← Înapoi
        </button>
        <span className="text-sm">
          Pagina {page} din {totalPages}
        </span>
        <button
          disabled={page >= totalPages}
          onClick={() => setPage((p) => p + 1)}
          className="rounded border bg-white px-3 py-1 disabled:opacity-40"
        >
          Înainte →
        </button>
      </div>
    </div>
  );
}
