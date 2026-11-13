"use client";

import { useCallback, useEffect, useState } from "react";
import { api, errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Quote = {
  id: number;
  text: string;
  page_number?: number | null;
  note?: string;
  is_public?: boolean;
  likes_count?: number;
  liked_by_me?: boolean;
  user?: { id: number; username: string } | number;
  created_by_user?: { id: number; username: string } | number;
  username?: string;
};
type Page<T> = { results: T[] } | T[];
const rows = <T,>(p: Page<T>) => (Array.isArray(p) ? p : p.results);

const owner = (q: Quote) => q.user ?? q.created_by_user;
const ownerName = (q: Quote) =>
  typeof owner(q) === "object" && owner(q)
    ? (owner(q) as { username: string }).username
    : (q.username ?? "");
const ownerId = (q: Quote) =>
  typeof owner(q) === "object" && owner(q)
    ? (owner(q) as { id: number }).id
    : owner(q);

export default function Quotes({ bookId }: { bookId: number }) {
  const { user } = useAuth();
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [text, setText] = useState("");
  const [page, setPage] = useState("");
  const [note, setNote] = useState("");
  const [isPublic, setIsPublic] = useState(true);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<Page<Quote>>(`/api/quotes/?book=${bookId}`)
      .then((p) => setQuotes(rows(p)))
      .catch(() => setQuotes([]));
  }, [bookId]);

  useEffect(load, [load]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg("");
    try {
      await api("/api/quotes/", {
        method: "POST",
        body: JSON.stringify({
          book: bookId,
          text,
          page_number: page === "" ? null : Number(page),
          note,
          is_public: isPublic,
        }),
      });
      setText("");
      setPage("");
      setNote("");
      load();
    } catch (err) {
      setMsg(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!confirm("Ștergi citatul?")) return;
    await api(`/api/quotes/${id}/`, { method: "DELETE" });
    load();
  }

  async function toggleLike(q: Quote) {
    if (!user) return;
    await api(`/api/quotes/${q.id}/like/`, {
      method: q.liked_by_me ? "DELETE" : "POST",
    });
    setQuotes((list) =>
      list.map((x) =>
        x.id === q.id
          ? {
              ...x,
              liked_by_me: !q.liked_by_me,
              likes_count: (x.likes_count ?? 0) + (q.liked_by_me ? -1 : 1),
            }
          : x,
      ),
    );
  }

  return (
    <section className="mt-10 border-t border-stone-200 pt-6">
      <h2 className="mb-4 text-xl font-bold">Citate ({quotes.length})</h2>

      {user && (
        <form
          onSubmit={submit}
          className="mb-6 space-y-2 rounded-lg border border-stone-200 bg-white p-4"
        >
          <textarea
            className="w-full rounded border px-3 py-2"
            rows={3}
            placeholder="Un citat din carte..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            required
          />
          <div className="flex flex-wrap gap-2">
            <input
              type="number"
              min={0}
              placeholder="Pagina"
              className="w-24 rounded border px-2 py-1"
              value={page}
              onChange={(e) => setPage(e.target.value)}
            />
            <input
              className="min-w-[200px] flex-1 rounded border px-2 py-1"
              placeholder="Notă personală (opțional)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
            />
            Public (vizibil pentru toți)
          </label>
          {msg && (
            <p className="whitespace-pre-line text-sm text-red-600">{msg}</p>
          )}
          <button
            disabled={busy}
            className="rounded bg-amber-800 px-4 py-2 text-white hover:bg-amber-900 disabled:opacity-50"
          >
            Adaugă citatul
          </button>
        </form>
      )}

      <div className="space-y-3">
        {quotes.map((q) => {
          const mine =
            !!user &&
            (ownerId(q) === user.id || ownerName(q) === user.username);
          return (
            <blockquote
              key={q.id}
              className="rounded-lg border-l-4 border-amber-700 bg-white p-4"
            >
              <p className="whitespace-pre-line italic">„{q.text}”</p>
              <p className="mt-1 text-xs text-stone-500">
                {ownerName(q) && `${ownerName(q)} · `}
                {q.page_number ? `pagina ${q.page_number}` : ""}
                {q.is_public === false ? " · privat" : ""}
              </p>
              {mine && q.note && (
                <p className="mt-1 text-sm text-stone-600">Notă: {q.note}</p>
              )}
              <div className="mt-2 flex items-center gap-3 text-sm">
                <button
                  onClick={() => toggleLike(q)}
                  disabled={!user}
                  className={`rounded border px-3 py-0.5 ${
                    q.liked_by_me
                      ? "border-amber-800 bg-amber-800 text-white"
                      : "bg-white hover:bg-stone-100 disabled:opacity-60"
                  }`}
                >
                  ♥ {q.likes_count ?? 0}
                </button>
                {mine && (
                  <button
                    onClick={() => remove(q.id)}
                    className="text-red-600 hover:underline"
                  >
                    Șterge
                  </button>
                )}
              </div>
            </blockquote>
          );
        })}
        {quotes.length === 0 && (
          <p className="text-stone-500">Niciun citat încă.</p>
        )}
      </div>
    </section>
  );
}
