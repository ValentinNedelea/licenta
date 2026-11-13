"use client";

import { useEffect, useState } from "react";
import { api, errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Shelf = { id: number; name: string; kind: string };
type Page<T> = { results: T[] } | T[];
const rows = <T,>(p: Page<T>) => (Array.isArray(p) ? p : p.results);
const STATE_KINDS = ["want_to_read", "currently_reading", "read"];

// Favorites și rafturile personalizate (cele de stare se setează din butoane)
export default function ShelfPicker({ bookId }: { bookId: number }) {
  const { user } = useAuth();
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [shelfId, setShelfId] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!user) return;
    api<Page<Shelf>>("/api/shelves/")
      .then((p) => {
        const list = rows(p).filter((s) => !STATE_KINDS.includes(s.kind));
        setShelves(list);
        if (list.length) setShelfId(String(list[0].id));
      })
      .catch(() => setShelves([]));
  }, [user]);

  if (!user || shelves.length === 0) return null;

  async function add() {
    setMsg("");
    try {
      await api(`/api/shelves/${shelfId}/add-book/`, {
        method: "POST",
        body: JSON.stringify({ book: bookId }),
      });
      setMsg("Adăugată pe raft.");
    } catch (e) {
      setMsg(errorText(e));
    }
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
      <select
        className="rounded border bg-white px-2 py-1"
        value={shelfId}
        onChange={(e) => setShelfId(e.target.value)}
      >
        {shelves.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>
      <button
        onClick={add}
        className="rounded border bg-white px-3 py-1 hover:bg-stone-100"
      >
        Adaugă pe raft
      </button>
      {msg && <span className="whitespace-pre-line text-stone-600">{msg}</span>}
    </div>
  );
}
