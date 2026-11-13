"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Stars from "./Stars";
import ReviewComments from "./ReviewComments";

type Review = {
  id: number;
  rating: string | number;
  review_text: string;
  has_spoilers: boolean;
  helpful_count: number;
  comments_count: number;
  liked_by_me: boolean;
  user: { id: number; username: string };
};
type Page<T> = { results: T[] } | T[];
const rows = <T,>(p: Page<T>) => (Array.isArray(p) ? p : p.results);

export default function Reviews({ bookId }: { bookId: number }) {
  const { user } = useAuth();
  const [reviews, setReviews] = useState<Review[]>([]);
  const [editing, setEditing] = useState<number | null>(null);
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

  function resetForm() {
    setEditing(null);
    setRating("4");
    setText("");
    setSpoiler(false);
    setMsg("");
  }

  function startEdit(r: Review) {
    setEditing(r.id);
    setRating(String(Number(r.rating)));
    setText(r.review_text);
    setSpoiler(r.has_spoilers);
    setMsg("");
    window.scrollTo({ behavior: "smooth", top: document.body.scrollHeight });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg("");
    const payload = {
      rating: Number(rating),
      review_text: text,
      has_spoilers: spoiler,
    };
    try {
      if (editing !== null) {
        await api(`/api/reviews/${editing}/`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        await api("/api/reviews/", {
          method: "POST",
          body: JSON.stringify({ book: bookId, ...payload }),
        });
      }
      resetForm();
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
    if (editing === id) resetForm();
    load();
  }

  async function toggleLike(r: Review) {
    if (!user) return;
    await api(`/api/reviews/${r.id}/like/`, {
      method: r.liked_by_me ? "DELETE" : "POST",
    });
    setReviews((list) =>
      list.map((x) =>
        x.id === r.id
          ? {
              ...x,
              liked_by_me: !r.liked_by_me,
              helpful_count: x.helpful_count + (r.liked_by_me ? -1 : 1),
            }
          : x,
      ),
    );
  }

  const hasMine = !!user && reviews.some((r) => r.user.id === user.id);
  const showForm = !!user && (editing !== null || !hasMine);

  return (
    <section className="mt-10 border-t border-stone-200 pt-6">
      <h2 className="mb-4 text-xl font-bold">Recenzii ({reviews.length})</h2>

      {user ? (
        showForm ? (
          <form
            onSubmit={submit}
            className="mb-6 space-y-3 rounded-lg border border-stone-200 bg-white p-4"
          >
            <p className="font-semibold">
              {editing !== null ? "Editează recenzia" : "Scrie o recenzie"}
            </p>
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
            <div className="flex gap-2">
              <button
                disabled={busy}
                className="rounded bg-amber-800 px-4 py-2 text-white hover:bg-amber-900 disabled:opacity-50"
              >
                {busy
                  ? "Se trimite..."
                  : editing !== null
                    ? "Salvează"
                    : "Publică recenzia"}
              </button>
              {editing !== null && (
                <button
                  type="button"
                  onClick={resetForm}
                  className="rounded border px-4 py-2 hover:bg-stone-100"
                >
                  Anulează
                </button>
              )}
            </div>
          </form>
        ) : (
          <p className="mb-6 text-sm text-stone-600">
            Ai scris deja o recenzie pentru această carte. O poți edita mai jos.
          </p>
        )
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
          const hidden = r.has_spoilers && !shown[r.id];
          const mine = !!user && r.user.id === user.id;

          return (
            <article
              key={r.id}
              className="rounded-lg border border-stone-200 bg-white p-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <strong>{r.user.username}</strong>
                  <Stars value={Number(r.rating)} />
                  <span className="text-sm text-stone-500">
                    {Number(r.rating).toFixed(2)}
                  </span>
                </div>
                {mine && (
                  <div className="flex gap-3 text-sm">
                    <button
                      onClick={() => startEdit(r)}
                      className="text-stone-600 hover:underline"
                    >
                      Editează
                    </button>
                    <button
                      onClick={() => remove(r.id)}
                      className="text-red-600 hover:underline"
                    >
                      Șterge
                    </button>
                  </div>
                )}
              </div>

              {r.review_text &&
                (hidden ? (
                  <button
                    onClick={() => setShown((s) => ({ ...s, [r.id]: true }))}
                    className="mt-2 text-sm text-stone-500 underline"
                  >
                    Recenzie cu spoilere. Apasă ca să o afișezi.
                  </button>
                ) : (
                  <p className="mt-2 whitespace-pre-line">{r.review_text}</p>
                ))}

              <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-stone-500">
                {" "}
                <button
                  onClick={() => toggleLike(r)}
                  disabled={!user}
                  className={`rounded border px-3 py-0.5 ${
                    r.liked_by_me
                      ? "border-amber-800 bg-amber-800 text-white"
                      : "bg-white hover:bg-stone-100 disabled:opacity-60"
                  }`}
                >
                  👍 Util · {r.helpful_count}
                </button>
                <ReviewComments reviewId={r.id} count={r.comments_count} />{" "}
              </div>
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
