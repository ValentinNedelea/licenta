"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Stars from "./Stars";

// Dacă backend-ul folosește alte nume pentru câmpuri, se schimbă doar aici
const TEXT_FIELD = "review_text";
const SPOILER_FIELD = "has_spoilers";

type Review = {
  id: number;
  rating: string | number;
  created_at?: string;
  user?: number | { id: number; username: string };
  username?: string;
  [key: string]: unknown;
};
type Page<T> = { results: T[] } | T[];
const rows = <T,>(p: Page<T>) => (Array.isArray(p) ? p : p.results);

const reviewUserName = (r: Review) =>
  typeof r.user === "object" && r.user
    ? r.user.username
    : (r.username ?? "utilizator");
const reviewUserId = (r: Review) =>
  typeof r.user === "object" && r.user
    ? r.user.id
    : (r.user as number | undefined);

export default function Reviews({ bookId }: { bookId: number }) {
  const { user } = useAuth();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [rating, setRating] = useState("4");
  const [text, setText] = useState("");
  const [spoiler, setSpoiler] = useState(false);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [shown, setShown] = useState<Record<number, boolean>>({});

  const load = useCallback(() => {
    api<Page<Review>>(`/api/reviews/?book=${bookId}`)
      .then((p) => setReviews(rows(p)))
      .catch(() => setReviews([]));
  }, [bookId]);

  useEffect(load, [load]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg("");
    try {
      await api("/api/reviews/", {
        method: "POST",
        body: JSON.stringify({
          book: bookId,
          rating: Number(rating),
          [TEXT_FIELD]: text,
          [SPOILER_FIELD]: spoiler,
        }),
      });
      setText("");
      setSpoiler(false);
      load();
    } catch (err) {
      setMsg(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!confirm("Ștergi recenzia?")) return;
    await api(`/api/reviews/${id}/`, { method: "DELETE" });
    load();
  }

  return (
    <section className="mt-10 border-t border-stone-200 pt-6">
      <h2 className="mb-4 text-xl font-bold">Recenzii ({reviews.length})</h2>

      {user ? (
        <form
          onSubmit={submit}
          className="mb-6 space-y-3 rounded-lg border border-stone-200 bg-white p-4"
        >
          <div className="flex items-center gap-3">
            <label className="text-sm">Nota (0–5, din 0,25):</label>
            <input
              type="number"
              min={0}
              max={5}
              step={0.25}
              value={rating}
              onChange={(e) => setRating(e.target.value)}
              className="w-24 rounded border px-2 py-1"
              required
            />
            <Stars value={Number(rating) || 0} />
          </div>
          <textarea
            className="w-full rounded border px-3 py-2"
            rows={4}
            placeholder="Scrie o recenzie (opțional)..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={spoiler}
              onChange={(e) => setSpoiler(e.target.checked)}
            />
            Conține spoilere
          </label>
          {msg && (
            <p className="whitespace-pre-line text-sm text-red-600">{msg}</p>
          )}
          <button
            disabled={busy}
            className="rounded bg-amber-800 px-4 py-2 text-white hover:bg-amber-900 disabled:opacity-50"
          >
            {busy ? "Se trimite..." : "Publică recenzia"}
          </button>
        </form>
      ) : (
        <p className="mb-6 text-sm">
          <Link href="/login" className="text-amber-800 underline">
            Autentifică-te
          </Link>{" "}
          ca să scrii o recenzie.
        </p>
      )}

      <div className="space-y-4">
        {reviews.map((r) => {
          const body = (r[TEXT_FIELD] as string | undefined) ?? "";
          const isSpoiler = Boolean(r[SPOILER_FIELD]);
          const hidden = isSpoiler && !shown[r.id];
          const mine =
            !!user &&
            (reviewUserId(r) === user.id ||
              reviewUserName(r) === user.username);

          return (
            <article
              key={r.id}
              className="rounded-lg border border-stone-200 bg-white p-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <strong>{reviewUserName(r)}</strong>
                  <Stars value={Number(r.rating)} />
                  <span className="text-sm text-stone-500">
                    {Number(r.rating).toFixed(2)}
                  </span>
                </div>
                {mine && (
                  <button
                    onClick={() => remove(r.id)}
                    className="text-sm text-red-600 hover:underline"
                  >
                    Șterge
                  </button>
                )}
              </div>
              {body &&
                (hidden ? (
                  <button
                    onClick={() => setShown((s) => ({ ...s, [r.id]: true }))}
                    className="mt-2 text-sm text-stone-500 underline"
                  >
                    Recenzie cu spoilere. Apasă ca să o afișezi.
                  </button>
                ) : (
                  <p className="mt-2 whitespace-pre-line">{body}</p>
                ))}
            </article>
          );
        })}
        {reviews.length === 0 && (
          <p className="text-stone-500">Nicio recenzie încă.</p>
        )}
      </div>
    </section>
  );
}
