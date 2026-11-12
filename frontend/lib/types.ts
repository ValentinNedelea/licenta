export type Author = { id: number; name: string };
export type Genre = { id: number; name: string; slug?: string };

export type Book = {
  id: number;
  title: string;
  subtitle?: string;
  description?: string;
  authors?: (Author | string)[];
  genres?: (Genre | string)[];
  cover_url?: string | null;
  cover_img_url?: string | null;
  cover_image_url?: string | null;
  page_count?: number | null;
  publication_date?: string | null;
  isbn13?: string | null;
  avg_rating?: string | number | null;
  rating_count?: number | null;
  external_avg_rating?: string | number | null;
  external_rating_count?: number | null;
  [key: string]: unknown;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export const authorNames = (b: Book) =>
  (b.authors ?? []).map((a) => (typeof a === "string" ? a : a.name)).join(", ");

export const genreNames = (b: Book) =>
  (b.genres ?? []).map((g) => (typeof g === "string" ? g : g.name));

export const coverOf = (b: Book) =>
  b.cover_img_url ?? b.cover_url ?? b.cover_image_url ?? null;
// Dacă aplicația nu are încă rating-uri proprii, arătăm ratingul din dataset
export function ratingOf(
  b: Book,
): { value: number; count: number; external: boolean } | null {
  const own = Number(b.avg_rating ?? 0);
  if (own > 0)
    return { value: own, count: b.rating_count ?? 0, external: false };
  const ext = Number(b.external_avg_rating ?? 0);
  if (ext > 0)
    return { value: ext, count: b.external_rating_count ?? 0, external: true };
  return null;
}
