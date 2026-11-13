"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type BookList = { id: number; title: string };
type Page<T> = { results: T[] } | T[];
const rows = <T,>(p: Page<T>) => (Array.isArray(p) ? p : p.results);

export default function ListPicker({ bookId }: { bookId: number }) {
  const { user } = useAuth();
  const [lists, setLists] = useState<BookList[] | null>(null);
  const [listId, setListId] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!user) return;
    api<Page<BookList>>("/api/lists/?mine=1")
      .then((p) => {
        const l = rows(p);
        setLists(l);
        if (l.length) setListId(String(l[0].id));
      })
      .catch(() => setLists([]));
  }, [user]);

  if (!user || lists === null) return null;
  if (lists.length === 0) {
    return (
      <p className="mt-3 text-sm text-stone-500">
        <Link href="/lists" className="text-amber-800 underline">
          Creează o listă
        </Link>{" "}
        ca să poți adăuga cărți în ea.
      </p>
    );
  }

  async function add() {
    setMsg("");
    try {
      await api(`/api/lists/${listId}/add-book/`, {
        method: "POST",
        body: JSON.stringify({ book: bookId }),
      });
      setMsg("Adăugată în listă.");
    } catch (e) {
      setMsg(errorText(e));
    }
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
      <select
        className="rounded border bg-white px-2 py-1"
        value={listId}
        onChange={(e) => setListId(e.target.value)}
      >
        {lists.map((l) => (
          <option key={l.id} value={l.id}>
            {l.title}
          </option>
        ))}
      </select>
      <button
        onClick={add}
        className="rounded border bg-white px-3 py-1 hover:bg-stone-100"
      >
        Adaugă în listă
      </button>
      {msg && <span className="whitespace-pre-line text-stone-600">{msg}</span>}
    </div>
  );
}
