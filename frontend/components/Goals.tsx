"use client";

import { useCallback, useEffect, useState } from "react";
import { api, errorText } from "@/lib/api";

// Dacă backend-ul folosește alte valori pentru tipul obiectivului, se schimbă aici
const GOAL_TYPES = [
  { value: "books", label: "Cărți", unit: "cărți" },
  { value: "pages", label: "Pagini", unit: "pagini" },
  { value: "minutes", label: "Minute", unit: "minute" },
];

type Goal = {
  id: number;
  year: number;
  goal_type: string;
  target: number;
  progress?: number;
  percent?: number;
  on_track?: boolean | null;
};
type Page<T> = { results: T[] } | T[];
const rows = <T,>(p: Page<T>) => (Array.isArray(p) ? p : p.results);

export default function Goals({ year }: { year: number }) {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [type, setType] = useState("books");
  const [target, setTarget] = useState("12");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<Page<Goal>>(`/api/goals/?year=${year}`)
      .then((p) => setGoals(rows(p)))
      .catch(() => setGoals([]));
  }, [year]);

  useEffect(load, [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg("");
    try {
      await api("/api/goals/", {
        method: "POST",
        body: JSON.stringify({ year, goal_type: type, target: Number(target) }),
      });
      load();
    } catch (err) {
      setMsg(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!confirm("Ștergi obiectivul?")) return;
    await api(`/api/goals/${id}/`, { method: "DELETE" });
    load();
  }

  const label = (t: string) => GOAL_TYPES.find((g) => g.value === t);

  return (
    <div className="mb-6 rounded-lg border border-stone-200 bg-white p-4">
      <h2 className="mb-3 font-semibold">Obiective {year}</h2>

      <div className="space-y-3">
        {goals.map((g) => {
          const pct = Math.min(100, Math.round(Number(g.percent ?? 0)));
          const info = label(g.goal_type);
          return (
            <div key={g.id}>
              <div className="flex items-center justify-between text-sm">
                <span>
                  {info?.label ?? g.goal_type}: {Number(g.progress ?? 0)} /{" "}
                  {g.target} {info?.unit ?? ""}
                </span>
                <span className="flex items-center gap-3">
                  {g.on_track === true && (
                    <span className="text-green-700">la zi</span>
                  )}
                  {g.on_track === false && (
                    <span className="text-amber-700">în urmă</span>
                  )}
                  <button
                    onClick={() => remove(g.id)}
                    className="text-red-600 hover:underline"
                  >
                    Șterge
                  </button>
                </span>
              </div>
              <div className="mt-1 h-3 rounded bg-stone-100">
                <div
                  className="h-3 rounded bg-amber-700"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className="text-xs text-stone-500">{pct}%</p>
            </div>
          );
        })}
        {goals.length === 0 && (
          <p className="text-sm text-stone-500">
            Nu ai niciun obiectiv pentru {year}.
          </p>
        )}
      </div>

      <form
        onSubmit={create}
        className="mt-4 flex flex-wrap items-center gap-2 border-t pt-3"
      >
        <select
          className="rounded border bg-white px-2 py-1"
          value={type}
          onChange={(e) => setType(e.target.value)}
        >
          {GOAL_TYPES.map((g) => (
            <option key={g.value} value={g.value}>
              {g.label}
            </option>
          ))}
        </select>
        <input
          type="number"
          min={1}
          className="w-24 rounded border px-2 py-1"
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          required
        />
        <button
          disabled={busy}
          className="rounded bg-amber-800 px-3 py-1 text-white hover:bg-amber-900 disabled:opacity-50"
        >
          Adaugă obiectiv
        </button>
        {msg && (
          <p className="w-full whitespace-pre-line text-sm text-red-600">
            {msg}
          </p>
        )}
      </form>
    </div>
  );
}
