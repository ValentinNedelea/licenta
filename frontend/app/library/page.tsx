"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Book } from "@/lib/types";
import BookCard from "@/components/BookCard";
import ProgressCard, { Progress } from "@/components/ProgressCard";

type Shelf = {
  id: number;
  name: string;
  kind: string;
  books_count?: number;
  is_public?: boolean;
};
type Page<T> = { results: T[] } | T[];
const rows = <T,>(p: Page<T>) => (Array.isArray(p) ? p : p.results);

const DEFAULT_KINDS = [
  "want_to_read",
  "currently_reading",
  "read",
  "favorites",
];

export default function LibraryPage() {
  const { user, loading } = useAuth();
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [active, setActive] = useState<number | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [progress, setProgress] = useState<Progress[]>([]);
  const [busy, setBusy] = useState(false);
  const [newName, setNewName] = useState("");
  const [msg, setMsg] = useState("");

  const current = shelves.find((s) => s.id === active) ?? null;

  const loadShelves = useCallback(async (selectId?: number) => {
    const list = rows(await api<Page<Shelf>>("/api/shelves/"));
    setShelves(list);
    setActive((a) => selectId ?? a ?? (list.length ? list[0].id : null));
  }, []);

  useEffect(() => {
    if (user)
      loadShelves().catch(() => setMsg("Eroare la încărcarea rafturilor."));
  }, [user, loadShelves]);

  const loadContent = useCallback(async () => {
    if (!current) return;
    setBusy(true);
    try {
      if (current.kind === "currently_reading" || current.kind === "read") {
        const status = current.kind === "read" ? "read" : "reading";
        setProgress(
          rows(await api<Page<Progress>>(`/api/progress/?status=${status}`)),
        );
        setBooks([]);
      } else {
        const items = rows(
          await api<Page<{ book: Book }>>(`/api/shelves/${current.id}/books/`),
        );
        setBooks(items.map((i) => i.book));
        setProgress([]);
      }
    } catch {
      setBooks([]);
      setProgress([]);
      setMsg("Eroare la încărcarea cărților.");
    } finally {
      setBusy(false);
    }
  }, [current]);

  useEffect(() => {
    loadContent();
  }, [loadContent]);

  async function createShelf(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setMsg("");
    try {
      const s = await api<Shelf>("/api/shelves/", {
        method: "POST",
        body: JSON.stringify({ name: newName.trim(), is_public: true }),
      });
      setNewName("");
      await loadShelves(s.id);
    } catch (err) {
      setMsg(errorText(err));
    }
  }

  async function deleteShelf() {
    if (!current || !confirm(`Ștergi raftul „${current.name}”?`)) return;
    await api(`/api/shelves/${current.id}/`, { method: "DELETE" });
    setActive(null);
    await loadShelves(shelves[0]?.id);
  }

  async function removeBook(bookId: number) {
    if (!current) return;
    await api(`/api/shelves/${current.id}/books/${bookId}/`, {
      method: "DELETE",
    });
    await loadShelves(current.id);
    loadContent();
  }

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

  const isProgressShelf =
    current?.kind === "currently_reading" || current?.kind === "read";
  const isCustom = !!current && !DEFAULT_KINDS.includes(current.kind);
  const empty = isProgressShelf ? progress.length === 0 : books.length === 0;

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
            {s.name} ({s.books_count ?? 0})
          </button>
        ))}
      </div>

      <form onSubmit={createShelf} className="mb-4 flex gap-2">
        <input
          className="w-56 rounded border bg-white px-3 py-1 text-sm"
          placeholder="Raft nou (ex: SF)"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
        />
        <button className="rounded border bg-white px-3 py-1 text-sm hover:bg-stone-100">
          + Creează raft
        </button>
        {isCustom && (
          <button
            type="button"
            onClick={deleteShelf}
            className="ml-auto text-sm text-red-600 hover:underline"
          >
            Șterge raftul
          </button>
        )}
      </form>
      {msg && (
        <p className="mb-3 whitespace-pre-line text-sm text-red-600">{msg}</p>
      )}

      <div className={`grid gap-3 sm:grid-cols-2 ${busy ? "opacity-50" : ""}`}>
        {isProgressShelf
          ? progress.map((p) => (
              <ProgressCard
                key={p.id}
                p={p}
                onChanged={() => {
                  loadShelves(current?.id);
                  loadContent();
                }}
              />
            ))
          : books.map((b) => (
              <div key={b.id} className="space-y-1">
                <BookCard book={b} />
                <button
                  onClick={() => removeBook(b.id)}
                  className="text-xs text-red-600 hover:underline"
                >
                  Scoate de pe raft
                </button>
              </div>
            ))}
      </div>

      {!busy && empty && (
        <p className="py-8 text-center text-stone-500">
          Raftul e gol. Adaugă cărți din{" "}
          <Link href="/books" className="text-amber-800 underline">
            catalog
          </Link>
          .
        </p>
      )}
    </div>
  );
}
