"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Book } from "@/lib/types";
import BookCard from "@/components/BookCard";

type Shelf = {
  id: number;
  name: string;
  book_count?: number;
  is_default?: boolean;
};
type Page<T> = { results: T[] } | T[];
const rows = <T,>(p: Page<T>) => (Array.isArray(p) ? p : p.results);

// un element de pe raft poate fi { book: {...} } sau direct cartea
function toBook(item: unknown): Book | null {
  const it = item as { book?: unknown };
  if (it && typeof it.book === "object" && it.book) return it.book as Book;
  if (it && typeof (item as Book).title === "string") return item as Book;
  return null;
}

export default function LibraryPage() {
  const { user, loading } = useAuth();
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [active, setActive] = useState<number | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [busy, setBusy] = useState(false);
  const [raw, setRaw] = useState("");

  useEffect(() => {
    if (!user) return;
    api<Page<Shelf>>("/api/shelves/")
      .then((p) => {
        const list = rows(p);
        setShelves(list);
        if (list.length) setActive(list[0].id);
      })
      .catch(() => setRaw("Eroare la încărcarea rafturilor."));
  }, [user]);

  useEffect(() => {
    if (active === null) return;
    setBusy(true);
    api<Page<unknown>>(`/api/shelves/${active}/books/`)
      .then((p) => {
        setRaw(JSON.stringify(p, null, 2));
        setBooks(
          rows(p)
            .map(toBook)
            .filter((b): b is Book => b !== null),
        );
      })
      .catch(() => {
        setBooks([]);
        setRaw("Eroare de la server (500). Vezi terminalul Django.");
      })
      .finally(() => setBusy(false));
  }, [active]);

  if (loading) return <p className="text-stone-500">Se încarcă...</p>;
  if (!user) {
    return (
      <p>
        <Link href="/login" className="text-amber-800 underline">
          Autentifică-te
        </Link>{" "}
        ca să-ți vezi biblioteca.
      </p>
    );
  }

  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">Biblioteca mea</h1>

      <div className="mb-4 flex flex-wrap gap-2">
        {shelves.map((s) => (
          <button
            key={s.id}
            onClick={() => setActive(s.id)}
            className={`rounded-full border px-4 py-1 text-sm ${
              active === s.id
                ? "border-amber-800 bg-amber-800 text-white"
                : "bg-white hover:bg-stone-100"
            }`}
          >
            {s.name}
            {s.book_count !== undefined ? ` (${s.book_count})` : ""}
          </button>
        ))}
      </div>

      <div className={`grid gap-3 sm:grid-cols-2 ${busy ? "opacity-50" : ""}`}>
        {books.map((b) => (
          <BookCard key={b.id} book={b} />
        ))}
      </div>

      {!busy && books.length === 0 && (
        <p className="py-8 text-center text-stone-500">
          Raftul e gol. Adaugă cărți din{" "}
          <Link href="/books" className="text-amber-800 underline">
            catalog
          </Link>
          .
        </p>
      )}

      <pre className="mt-6 overflow-auto rounded bg-stone-900 p-3 text-xs text-stone-200">
        {raw}
      </pre>
    </div>
  );
}
