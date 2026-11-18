"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Book } from "@/lib/types";
import BookCard from "./BookCard";

type Rec = Book & {
  score?: number | null;
  reason?: { type: string; title?: string; book_id?: number };
};

export default function Recommended() {
  const { user, loading } = useAuth();
  const [recs, setRecs] = useState<Rec[]>([]);

  useEffect(() => {
    if (!user) return;
    api<Rec[]>("/api/recommendations/?limit=12")
      .then(setRecs)
      .catch(() => setRecs([]));
  }, [user]);

  if (loading || !user || recs.length === 0) return null;

  return (
    <section className="mt-10">
      <h2 className="mb-4 text-xl font-bold">Recomandate pentru tine</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {recs.map((r) => (
          <div key={r.id} className="space-y-1">
            <BookCard book={r} />
            <p className="text-xs text-stone-500">
              {r.reason?.type === "similar_to" && r.reason.title
                ? `Pentru că ți-a plăcut „${r.reason.title}”`
                : "Populară în catalog"}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
