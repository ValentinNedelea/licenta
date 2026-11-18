"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Book } from "@/lib/types";
import BookCard from "./BookCard";

export default function SimilarBooks({ bookId }: { bookId: number }) {
  const [books, setBooks] = useState<Book[]>([]);

  useEffect(() => {
    api<Book[]>(`/api/books/${bookId}/similar/?limit=8`)
      .then(setBooks)
      .catch(() => setBooks([]));
  }, [bookId]);

  if (books.length === 0) return null;

  return (
    <section className="mt-10 border-t border-stone-200 pt-6">
      <h2 className="mb-4 text-xl font-bold">Cărți similare</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {books.map((b) => (
          <BookCard key={b.id} book={b} />
        ))}
      </div>
    </section>
  );
}
