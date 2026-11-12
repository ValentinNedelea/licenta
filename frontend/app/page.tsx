import Link from "next/link";

export default function Home() {
  return (
    <div className="py-12 text-center">
      <h1 className="text-4xl font-bold text-amber-800">Bookshelf</h1>
      <p className="mx-auto mt-3 max-w-md text-stone-600">
        Urmărește ce citești, notează cărțile și descoperă următoarea lectură.
      </p>
      <Link
        href="/books"
        className="mt-6 inline-block rounded bg-amber-800 px-5 py-2 text-white hover:bg-amber-900"
      >
        Explorează cărțile
      </Link>
    </div>
  );
}
