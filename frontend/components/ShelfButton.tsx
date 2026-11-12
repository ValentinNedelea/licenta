"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const STATUSES = [
  { value: "want_to_read", label: "Vreau să citesc" },
  { value: "reading", label: "Citesc acum" },
  { value: "read", label: "Citită" },
];

type Progress = { id: number; status: string; book: number | { id: number } };
type Page<T> = { results: T[] } | T[];

const rows = <T,>(p: Page<T>) => (Array.isArray(p) ? p : p.results);

export default function ShelfButton({ bookId }: { bookId: number }) {
  const { user, loading } = useAuth();
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!user) return;
    api<Page<Progress>>(`/api/progress/?book=${bookId}`)
      .then((p) => {
        const list = rows(p);
        // cea mai recentă citire (id-ul cel mai mare)
        const last = [...list].sort((a, b) => b.id - a.id)[0];
        setStatus(last?.status ?? "");
      })
      .catch(() => {});
  }, [user, bookId]);

  if (loading) return null;
  if (!user) {
    return (
      <p className="mt-4 text-sm">
        <Link href="/login" className="text-amber-800 underline">
          Autentifică-te
        </Link>{" "}
        ca să adaugi cartea în bibliotecă.
      </p>
    );
  }

  async function choose(value: string) {
    setBusy(true);
    setMsg("");
    try {
      await api("/api/progress/set-status/", {
        method: "POST",
        body: JSON.stringify({ book: bookId, status: value }),
      });
      setStatus(value);
      setMsg("Salvat.");
    } catch (e) {
      setMsg(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-4">
      <div className="flex flex-wrap gap-2">
        {STATUSES.map((s) => (
          <button
            key={s.value}
            disabled={busy}
            onClick={() => choose(s.value)}
            className={`rounded border px-3 py-1 text-sm disabled:opacity-50 ${
              status === s.value
                ? "border-amber-800 bg-amber-800 text-white"
                : "bg-white hover:bg-stone-100"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
      {msg && (
        <p className="mt-2 whitespace-pre-line text-sm text-stone-600">{msg}</p>
      )}
    </div>
  );
}
