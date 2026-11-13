"use client";

import { use, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Book } from "@/lib/types";
import BookCard from "@/components/BookCard";

type Detail = {
  id: number;
  title: string;
  description?: string;
  likes_count?: number;
  liked_by_me?: boolean;
  items?: unknown[];
  books?: unknown[];
  [key: string]: unknown;
};

const ownerOf = (d: Detail) =>
  d.owner_user ?? d.owner ?? d.user ?? d.created_by_user;
const ownerName = (o: unknown) =>
  o && typeof o === "object"
    ? (o as { username?: string }).username
    : undefined;
const ownerId = (o: unknown) =>
  o && typeof o === "object"
    ? (o as { id?: number }).id
    : (o as number | undefined);

function toBook(it: unknown): Book | null {
  const o = it as { book?: unknown };
  if (o && typeof o.book === "object" && o.book) return o.book as Book;
  if (o && typeof (it as Book).title === "string") return it as Book;
  return null;
}

export default function ListPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user } = useAuth();
  const router = useRouter();
  const [d, setD] = useState<Detail | null>(null);
  const [error, setError] = useState(false);

  const load = useCallback(() => {
    api<Detail>(`/api/lists/${id}/`)
      .then(setD)
      .catch(() => setError(true));
  }, [id]);

  useEffect(load, [load]);

  if (error) return <p>Lista nu a fost găsită.</p>;
  if (!d) return <p className="text-stone-500">Se încarcă...</p>;

  const o = ownerOf(d);
  const mine =
    !!user && (ownerId(o) === user.id || ownerName(o) === user.username);
  const books = (d.items ?? d.books ?? [])
    .map(toBook)
    .filter((b): b is Book => b !== null);

  async function removeBook(bookId: number) {
    await api(`/api/lists/${id}/books/${bookId}/`, { method: "DELETE" });
    load();
  }
  async function deleteList() {
    if (!confirm("Ștergi lista?")) return;
    await api(`/api/lists/${id}/`, { method: "DELETE" });
    router.push("/lists");
  }
  async function toggleLike() {
    if (!user || !d) return;
    await api(`/api/lists/${id}/like/`, {
      method: d.liked_by_me ? "DELETE" : "POST",
    });
    load();
  }

  return (
    <div>
      <h1 className="text-3xl font-bold">{d.title}</h1>
      {ownerName(o) && (
        <p className="text-sm text-stone-500">de {ownerName(o)}</p>
      )}
      {d.description && (
        <p className="mt-2 whitespace-pre-line">{d.description}</p>
      )}

      <div className="mt-3 flex items-center gap-4 text-sm">
        <button
          onClick={toggleLike}
          disabled={!user}
          className={`rounded border px-3 py-0.5 ${d.liked_by_me ? "border-amber-800 bg-amber-800 text-white" : "bg-white hover:bg-stone-100 disabled:opacity-60"}`}
        >
          ♥ {d.likes_count ?? 0}
        </button>
        {mine && (
          <button onClick={deleteList} className="text-red-600 hover:underline">
            Șterge lista
          </button>
        )}
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {books.map((b) => (
          <div key={b.id} className="space-y-1">
            <BookCard book={b} />
            {mine && (
              <button
                onClick={() => removeBook(b.id)}
                className="text-xs text-red-600 hover:underline"
              >
                Scoate din listă
              </button>
            )}
          </div>
        ))}
      </div>
      {books.length === 0 && (
        <p className="py-6 text-center text-stone-500">
          Lista nu are cărți încă. Adaugă-le din pagina unei cărți.
        </p>
      )}
    </div>
  );
}
