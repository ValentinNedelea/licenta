"use client";

import { useCallback, useState } from "react";
import { api, errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Comment = {
  id: number;
  body: string;
  parent_comment: number | { id: number } | null;
  user?: { id: number; username: string } | number;
  username?: string;
  created_at?: string;
  is_deleted?: boolean;
};
type Page<T> = { results: T[] } | T[];
const rows = <T,>(p: Page<T>) => (Array.isArray(p) ? p : p.results);

const parentId = (c: Comment) =>
  c.parent_comment && typeof c.parent_comment === "object"
    ? c.parent_comment.id
    : (c.parent_comment as number | null);
const userName = (c: Comment) =>
  typeof c.user === "object" && c.user
    ? c.user.username
    : (c.username ?? "utilizator");
const userId = (c: Comment) =>
  typeof c.user === "object" && c.user ? c.user.id : c.user;

// Folosit ca fragment în rândul cu like-uri al recenziei
export default function ReviewComments({
  reviewId,
  count,
}: {
  reviewId: number;
  count: number;
}) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [comments, setComments] = useState<Comment[] | null>(null);
  const [text, setText] = useState("");
  const [replyTo, setReplyTo] = useState<number | null>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<Page<Comment>>(`/api/comments/?review=${reviewId}`)
      .then((p) => setComments(rows(p)))
      .catch(() => setComments([]));
  }, [reviewId]);

  function toggle() {
    if (!open && comments === null) load();
    setOpen((o) => !o);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setMsg("");
    try {
      await api("/api/comments/", {
        method: "POST",
        body: JSON.stringify({
          review: reviewId,
          parent_comment: replyTo,
          body: text,
        }),
      });
      setText("");
      setReplyTo(null);
      load();
    } catch (err) {
      setMsg(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!confirm("Ștergi comentariul?")) return;
    await api(`/api/comments/${id}/`, { method: "DELETE" });
    load();
  }

  const visible = (comments ?? []).filter((c) => !c.is_deleted);
  const top = visible.filter(
    (c) => parentId(c) === null || parentId(c) === undefined,
  );
  const repliesOf = (id: number) => visible.filter((c) => parentId(c) === id);
  const shownCount = comments === null ? count : visible.length;

  function renderComment(c: Comment, nested = false) {
    const mine =
      !!user && (userId(c) === user.id || userName(c) === user.username);
    return (
      <div key={c.id} className={nested ? "ml-6 border-l pl-3" : ""}>
        <p className="text-sm">
          <strong>{userName(c)}</strong>{" "}
          <span className="text-stone-700">{c.body}</span>
        </p>
        <div className="flex gap-3 text-xs text-stone-500">
          {user && !nested && (
            <button
              onClick={() => setReplyTo(c.id)}
              className="hover:underline"
            >
              Răspunde
            </button>
          )}
          {mine && (
            <button
              onClick={() => remove(c.id)}
              className="text-red-600 hover:underline"
            >
              Șterge
            </button>
          )}
        </div>
        {!nested && repliesOf(c.id).map((r) => renderComment(r, true))}
      </div>
    );
  }

  return (
    <>
      <button onClick={toggle} className="hover:underline">
        {open ? "Ascunde comentariile" : `${shownCount} comentarii`}
      </button>

      {open && (
        <div className="basis-full space-y-3 border-t border-stone-100 pt-3 text-stone-900">
          {comments === null && (
            <p className="text-sm text-stone-500">Se încarcă...</p>
          )}
          {top.map((c) => renderComment(c))}
          {comments !== null && top.length === 0 && (
            <p className="text-sm text-stone-500">Niciun comentariu încă.</p>
          )}

          {user && (
            <form onSubmit={submit} className="space-y-2">
              {replyTo !== null && (
                <p className="text-xs text-stone-500">
                  Răspunzi unui comentariu.{" "}
                  <button
                    type="button"
                    onClick={() => setReplyTo(null)}
                    className="underline"
                  >
                    Anulează
                  </button>
                </p>
              )}
              <div className="flex gap-2">
                <input
                  className="flex-1 rounded border px-3 py-1 text-sm"
                  placeholder="Scrie un comentariu..."
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                />
                <button
                  disabled={busy}
                  className="rounded bg-amber-800 px-3 py-1 text-sm text-white hover:bg-amber-900 disabled:opacity-50"
                >
                  Trimite
                </button>
              </div>
              {msg && (
                <p className="whitespace-pre-line text-sm text-red-600">
                  {msg}
                </p>
              )}
            </form>
          )}
        </div>
      )}
    </>
  );
}
