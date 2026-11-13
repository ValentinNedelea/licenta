"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Goals from "@/components/Goals";

type Month = {
  month: number;
  books_finished: number;
  pages_read: number;
  minutes_read: number;
};
type Overview = {
  year: number;
  books_finished: number;
  pages_read: number;
  minutes_read: number;
  days_read: number;
  avg_rating_given: number | null;
  avg_book_pages: number | null;
  longest_book: unknown;
  top_genres: unknown[];
  months: Month[];
};
type Streak = {
  current_streak: number;
  longest_streak: number;
  last_read_date: string | null;
  read_today: boolean;
};

const MONTHS = [
  "Ian",
  "Feb",
  "Mar",
  "Apr",
  "Mai",
  "Iun",
  "Iul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
type Metric = "books_finished" | "pages_read" | "minutes_read";
const METRICS: { key: Metric; label: string }[] = [
  { key: "books_finished", label: "Cărți" },
  { key: "pages_read", label: "Pagini" },
  { key: "minutes_read", label: "Minute" },
];

const nf = (n: number) => n.toLocaleString("ro-RO");

function Tile({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4">
      <p className="text-sm text-stone-500">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs text-stone-500">{sub}</p>}
    </div>
  );
}

// longest_book poate fi un obiect (cu titlu) sau o carte imbricată
function longestBookText(v: unknown): string | null {
  if (!v || typeof v !== "object") return null;
  const o = v as Record<string, unknown>;
  const b = (typeof o.book === "object" && o.book ? o.book : o) as Record<
    string,
    unknown
  >;
  const title = (b.title ?? o.title) as string | undefined;
  const pages = (b.page_count ?? o.page_count ?? o.pages) as number | undefined;
  if (!title) return null;
  return pages ? `${title} (${pages} pagini)` : title;
}

// top_genres: elemente de forma {name, count} sau similar
function genreRow(g: unknown): { name: string; count: number } {
  if (typeof g === "string") return { name: g, count: 0 };
  const o = g as Record<string, unknown>;
  const name = String(o.name ?? o.genre ?? o.slug ?? "?");
  const count = Number(
    o.count ?? o.books ?? o.books_count ?? o.books_finished ?? 0,
  );
  return { name, count };
}

export default function StatsPage() {
  const { user, loading } = useAuth();
  const thisYear = new Date().getFullYear();
  const [year, setYear] = useState(thisYear);
  const [metric, setMetric] = useState<Metric>("pages_read");
  const [data, setData] = useState<Overview | null>(null);
  const [streak, setStreak] = useState<Streak | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!user) return;
    api<Streak>("/api/streak/")
      .then(setStreak)
      .catch(() => setStreak(null));
  }, [user]);

  useEffect(() => {
    if (!user) return;
    setError(false);
    api<Overview>(`/api/stats/overview/?year=${year}`)
      .then(setData)
      .catch(() => setError(true));
  }, [user, year]);

  if (loading) return <p className="text-stone-500">Se încarcă...</p>;
  if (!user) {
    return (
      <p>
        <Link href="/login" className="text-amber-800 underline">
          Autentifică-te
        </Link>{" "}
        ca să-ți vezi statisticile.
      </p>
    );
  }
  if (error)
    return <p className="text-red-600">Nu am putut încărca statisticile.</p>;
  if (!data) return <p className="text-stone-500">Se încarcă...</p>;

  const max = Math.max(1, ...data.months.map((m) => m[metric]));
  const genres = data.top_genres.map(genreRow);
  const gMax = Math.max(1, ...genres.map((g) => g.count));
  const longest = longestBookText(data.longest_book);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Statistici</h1>
        <select
          className="rounded border bg-white px-3 py-1"
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
        >
          {[0, 1, 2, 3].map((i) => (
            <option key={i} value={thisYear - i}>
              {thisYear - i}
            </option>
          ))}
        </select>
      </div>

      {streak && (
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-4">
          <p className="text-lg font-semibold">
            🔥 Streak: {streak.current_streak}{" "}
            {streak.current_streak === 1 ? "zi" : "zile"}
          </p>
          <p className="text-sm text-stone-600">
            Cel mai lung: {streak.longest_streak} zile ·{" "}
            {streak.read_today
              ? "Ai citit azi, bravo!"
              : streak.current_streak > 0
                ? "Citește azi ca să păstrezi seria."
                : "Citește azi ca să începi o serie."}
          </p>
        </div>
      )}

      <Goals year={year} />

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Tile label="Cărți citite" value={nf(data.books_finished)} />
        <Tile label="Pagini citite" value={nf(data.pages_read)} />
        <Tile
          label="Timp de citit"
          value={`${Math.floor(data.minutes_read / 60)} h ${data.minutes_read % 60} min`}
        />
        <Tile label="Zile cu lectură" value={nf(data.days_read)} />
        <Tile
          label="Nota medie dată"
          value={
            data.avg_rating_given !== null
              ? Number(data.avg_rating_given).toFixed(2)
              : "-"
          }
        />
        <Tile
          label="Pagini / carte (medie)"
          value={
            data.avg_book_pages !== null
              ? nf(Math.round(Number(data.avg_book_pages)))
              : "-"
          }
        />
        <div className="col-span-2 rounded-lg border border-stone-200 bg-white p-4">
          <p className="text-sm text-stone-500">Cea mai lungă carte</p>
          <p className="mt-1 font-semibold">{longest ?? "-"}</p>
        </div>
      </div>

      <div className="mb-6 rounded-lg border border-stone-200 bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold">Pe luni, {data.year}</h2>
          <div className="flex gap-1">
            {METRICS.map((m) => (
              <button
                key={m.key}
                onClick={() => setMetric(m.key)}
                className={`rounded border px-3 py-0.5 text-sm ${
                  metric === m.key
                    ? "border-amber-800 bg-amber-800 text-white"
                    : "bg-white"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex h-40 items-end gap-2">
          {data.months.map((m) => (
            <div
              key={m.month}
              className="flex flex-1 flex-col items-center justify-end gap-1"
            >
              <span className="text-xs text-stone-500">{m[metric] || ""}</span>
              <div
                className="w-full rounded-t bg-amber-700"
                style={{
                  height: `${(m[metric] / max) * 100}%`,
                  minHeight: m[metric] ? 4 : 1,
                }}
                title={`${MONTHS[m.month - 1]}: ${m[metric]}`}
              />
              <span className="text-xs">{MONTHS[m.month - 1]}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-4">
        <h2 className="mb-3 font-semibold">Genurile tale preferate</h2>
        {genres.length === 0 ? (
          <p className="text-sm text-stone-500">
            Marchează câteva cărți ca „Citită” ca să apară aici.
          </p>
        ) : (
          <div className="space-y-2">
            {genres.map((g) => (
              <div key={g.name} className="flex items-center gap-3 text-sm">
                <span className="w-32 truncate">{g.name}</span>
                <div className="h-3 flex-1 rounded bg-stone-100">
                  <div
                    className="h-3 rounded bg-amber-700"
                    style={{ width: `${(g.count / gMax) * 100}%` }}
                  />
                </div>
                <span className="w-8 text-right text-stone-500">{g.count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
