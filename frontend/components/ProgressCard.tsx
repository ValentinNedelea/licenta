"use client";

import { useState } from "react";
import { api, errorText } from "@/lib/api";
import { Book } from "@/lib/types";
import BookCard from "./BookCard";

export type Progress = {
  id: number;
  book: Book;
  status: string;
  current_page: number;
  percent: string | number;
  started_at: string | null;
  finished_at: string | null;
  read_number: number;
};

export default function ProgressCard({
  p,
  onChanged,
}: {
  p: Progress;
  onChanged: () => void;
}) {
  const reading = p.status === "reading";
  const [page, setPage] = useState(String(p.current_page ?? 0));
  const [started, setStarted] = useState(p.started_at ?? "");
  const [finished, setFinished] = useState(p.finished_at ?? "");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const pct = Math.min(100, Math.round(Number(p.percent ?? 0)));

  async function save() {
    setBusy(true);
    setMsg("");
    const body: Record<string, unknown> = {
      started_at: started || null,
      finished_at: finished || null,
    };
    if (reading) body.current_page = Number(page || 0);
    try {
      await api(`/api/progress/${p.id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setMsg("Salvat.");
      onChanged();
    } catch (e) {
      setMsg(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  async function markRead() {
    setBusy(true);
    setMsg("");
    try {
      await api("/api/progress/set-status/", {
        method: "POST",
        body: JSON.stringify({ book: p.book.id, status: "read" }),
      });
      onChanged();
    } catch (e) {
      setMsg(errorText(e));
      setBusy(false);
    }
  }

  return (
    <div className="space-y-2 rounded-lg border border-stone-200 bg-white p-3">
      <BookCard book={p.book} />

      {reading && (
        <div>
          <div className="h-3 rounded bg-stone-100">
            <div
              className="h-3 rounded bg-amber-700"
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-stone-500">{pct}% citit</p>
        </div>
      )}
      {!reading && p.read_number > 1 && (
        <p className="text-xs text-stone-500">Citirea nr. {p.read_number}</p>
      )}

      <div className="flex flex-wrap items-end gap-3 text-sm">
        {reading && (
          <label className="flex flex-col">
            <span className="text-xs text-stone-500">Pagina curentă</span>
            <input
              type="number"
              min={0}
              className="w-24 rounded border px-2 py-1"
              value={page}
              onChange={(e) => setPage(e.target.value)}
            />
          </label>
        )}
        <label className="flex flex-col">
          <span className="text-xs text-stone-500">Început</span>
          <input
            type="date"
            className="rounded border px-2 py-1"
            value={started}
            onChange={(e) => setStarted(e.target.value)}
          />
        </label>
        <label className="flex flex-col">
          <span className="text-xs text-stone-500">Final</span>
          <input
            type="date"
            className="rounded border px-2 py-1"
            value={finished}
            onChange={(e) => setFinished(e.target.value)}
          />
        </label>
        <button
          onClick={save}
          disabled={busy}
          className="rounded bg-amber-800 px-3 py-1 text-white hover:bg-amber-900 disabled:opacity-50"
        >
          Salvează
        </button>
        {reading && (
          <button
            onClick={markRead}
            disabled={busy}
            className="rounded border px-3 py-1 hover:bg-stone-100 disabled:opacity-50"
          >
            Am terminat-o
          </button>
        )}
      </div>
      {msg && (
        <p className="whitespace-pre-line text-sm text-stone-600">{msg}</p>
      )}
    </div>
  );
}
