"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type BookList = {
  id: number;
  title: string;
  description?: string;
  is_public?: boolean;
  items_count?: number;
  books_count?: number;
  likes_count?: number;
  [key: string]: unknown;
};
type Page<T> = { results: T[] } | T[];
const rows = <T,>(p: Page<T>) => (Array.isArray(p) ? p : p.results);

export default function ListsPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<"public" | "mine">("public");
  const [lists, setLists] = useState<BookList[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isPublic, setIsPublic] = useState(true);
  const [msg, setMsg] = useState("");

  const load = useCallback(() => {
    api<Page<BookList>>(`/api/lists/${tab === "mine" ? "?mine=1" : ""}`)
      .then((p) => setLists(rows(p)))
      .catch(() => setLists([]));
  }, [tab]);

  useEffect(load, [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setMsg("");
    try {
      await api("/api/lists/", {
        method: "POST",
        body: JSON.stringify({
          title,
          description,
          cover_img_url: "",
          is_public: isPublic,
        }),
      });
      setTitle("");
      setDescription("");
      setTab("mine");
      load();
    } catch (err) {
      setMsg(errorText(err));
    }
  }

  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">Liste de cărți</h1>

      <div className="mb-4 flex gap-2">
        {(["public", "mine"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            disabled={t === "mine" && !user}
            className={`rounded-full border px-4 py-1 text-sm disabled:opacity-40 ${
              tab === t
                ? "border-amber-800 bg-amber-800 text-white"
                : "bg-white hover:bg-stone-100"
            }`}
          >
            {t === "public" ? "Publice" : "Ale mele"}
          </button>
        ))}
      </div>

      {user && (
        <form
          onSubmit={create}
          className="mb-6 space-y-2 rounded-lg border border-stone-200 bg-white p-4"
        >
          <p className="font-semibold">Listă nouă</p>
          <input
            className="w-full rounded border px-3 py-2"
            placeholder="Titlu (ex: Cele mai bune SF)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
          <textarea
            className="w-full rounded border px-3 py-2"
            rows={2}
            placeholder="Descriere (opțional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
            />
            Publică (vizibilă pentru toți)
          </label>
          {msg && (
            <p className="whitespace-pre-line text-sm text-red-600">{msg}</p>
          )}
          <button className="rounded bg-amber-800 px-4 py-2 text-white hover:bg-amber-900">
            Creează lista
          </button>
        </form>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {lists.map((l) => {
          const n = l.items_count ?? l.books_count;
          return (
            <Link
              key={l.id}
              href={`/lists/${l.id}`}
              className="rounded-lg border border-stone-200 bg-white p-4 hover:shadow-md"
            >
              <h3 className="font-semibold">{l.title}</h3>
              {l.description && (
                <p className="line-clamp-2 text-sm text-stone-600">
                  {l.description}
                </p>
              )}
              <p className="mt-1 text-xs text-stone-500">
                {n !== undefined ? `${n} cărți` : ""}
                {l.is_public === false ? " · privată" : ""}
                {l.likes_count ? ` · ♥ ${l.likes_count}` : ""}
              </p>
            </Link>
          );
        })}
      </div>
      {lists.length === 0 && (
        <p className="py-6 text-center text-stone-500">Nicio listă încă.</p>
      )}
    </div>
  );
}
