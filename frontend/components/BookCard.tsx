import Link from "next/link";
import { Book, authorNames, coverOf, ratingOf } from "@/lib/types";
import Stars from "./Stars";
import Cover from "./Cover";

export default function BookCard({ book }: { book: Book }) {
  const cover = coverOf(book);
  const rating = ratingOf(book);

  return (
    <Link
      href={`/books/${book.id}`}
      className="flex gap-3 rounded-lg border border-stone-200 bg-white p-3 hover:shadow-md"
    >
      <Cover src={cover} className="h-28 w-20 shrink-0 rounded" />
      <div className="min-w-0">
        <h3 className="line-clamp-2 font-semibold">{book.title}</h3>
        <p className="truncate text-sm text-stone-600">{authorNames(book)}</p>
        {rating && (
          <p className="mt-1 flex items-center gap-1 text-xs text-stone-500">
            <Stars value={rating.value} />
            {rating.value.toFixed(2)}
          </p>
        )}
      </div>
    </Link>
  );
}
