"use client";

import { useEffect, useState } from "react";
import { api, errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";

// Dacă backend-ul folosește altă valoare pentru sursa sesiunii, se schimbă aici
const SOURCE = "timer";

const key = (bookId: number) => `reading-timer:${bookId}`;

function readStart(bookId: number): number | null {
  try {
    const v = localStorage.getItem(key(bookId));
    return v ? Number(v) : null;
  } catch {
    return null;
  }
}
function writeStart(bookId: number, v: number | null) {
  try {
    if (v === null) localStorage.removeItem(key(bookId));
    else localStorage.setItem(key(bookId), String(v));
  } catch {
    /* ignorat */
  }
}

const fmt = (s: number) => {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const p = (n: number) => String(n).padStart(2, "0");
  return `${h > 0 ? p(h) + ":" : ""}${p(m)}:${p(sec)}`;
};

export default function ReadingTimer({ bookId }: { bookId: number }) {
  const { user } = useAuth();
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [finishing, setFinishing] = useState<{
    start: number;
    end: number;
  } | null>(null);
  const [startPage, setStartPage] = useState("");
  const [endPage, setEndPage] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setStartedAt(readStart(bookId));
  }, [bookId]);

  useEffect(() => {
    if (startedAt === null) return;
    const tick = () => setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, [startedAt]);

  if (!user) return null;

  function start() {
    const now = Date.now();
    writeStart(bookId, now);
    setStartedAt(now);
    setMsg("");
  }

  function stop() {
    if (startedAt === null) return;
    setFinishing({ start: startedAt, end: Date.now() });
  }

  function cancel() {
    writeStart(bookId, null);
    setStartedAt(null);
    setFinishing(null);
    setElapsed(0);
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!finishing) return;
    setBusy(true);
    setMsg("");
    const body: Record<string, unknown> = {
      book: bookId,
      started_at: new Date(finishing.start).toISOString(),
      ended_at: new Date(finishing.end).toISOString(),
      duration_seconds: Math.max(
        1,
        Math.round((finishing.end - finishing.start) / 1000),
      ),
      source: SOURCE,
    };
    if (startPage !== "") body.start_page = Number(startPage);
    if (endPage !== "") body.end_page = Number(endPage);
    try {
      await api("/api/sessions/", {
        method: "POST",
        body: JSON.stringify(body),
      });
      writeStart(bookId, null);
      setStartedAt(null);
      setFinishing(null);
      setElapsed(0);
      setStartPage("");
      setEndPage("");
      setMsg("Sesiune salvată. Vezi progresul în Statistici.");
    } catch (err) {
      setMsg(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-4 rounded-lg border border-stone-200 bg-white p-3">
      <p className="mb-2 text-sm font-semibold">Cronometru de citit</p>

      {finishing ? (
        <form onSubmit={save} className="space-y-2">
          <p className="text-sm">
            Ai citit {fmt(Math.round((finishing.end - finishing.start) / 1000))}
            . Adaugă paginile (opțional):
          </p>
          <div className="flex gap-2">
            <input
              type="number"
              min={0}
              placeholder="De la pagina"
              className="w-32 rounded border px-2 py-1"
              value={startPage}
              onChange={(e) => setStartPage(e.target.value)}
            />
            <input
              type="number"
              min={0}
              placeholder="Până la pagina"
              className="w-36 rounded border px-2 py-1"
              value={endPage}
              onChange={(e) => setEndPage(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <button
              disabled={busy}
              className="rounded bg-amber-800 px-3 py-1 text-sm text-white hover:bg-amber-900 disabled:opacity-50"
            >
              Salvează sesiunea
            </button>
            <button
              type="button"
              onClick={cancel}
              className="rounded border px-3 py-1 text-sm hover:bg-stone-100"
            >
              Renunță
            </button>
          </div>
        </form>
      ) : startedAt === null ? (
        <button
          onClick={start}
          className="rounded bg-amber-800 px-3 py-1 text-sm text-white hover:bg-amber-900"
        >
          ▶ Începe sesiunea
        </button>
      ) : (
        <div className="flex items-center gap-3">
          <span className="font-mono text-2xl">{fmt(elapsed)}</span>
          <button
            onClick={stop}
            className="rounded bg-stone-800 px-3 py-1 text-sm text-white hover:bg-stone-900"
          >
            ■ Oprește
          </button>
        </div>
      )}

      {msg && (
        <p className="mt-2 whitespace-pre-line text-sm text-stone-600">{msg}</p>
      )}
    </div>
  );
}
