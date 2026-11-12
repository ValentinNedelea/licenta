"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function Navbar() {
  const { user, loading, logout } = useAuth();

  return (
    <header className="border-b border-stone-200 bg-white">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" className="text-lg font-bold text-amber-800">
          Bookshelf
        </Link>
        <div className="flex items-center gap-4 text-sm">
          <Link href="/books" className="hover:underline">
            Cărți
          </Link>
          {loading ? null : user ? (
            <>
              <Link href="/library" className="hover:underline">
                Biblioteca mea
              </Link>
              <span className="text-stone-500">{user.username}</span>
              <button
                onClick={logout}
                className="rounded border px-3 py-1 hover:bg-stone-100"
              >
                Ieșire
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="hover:underline">
                Login
              </Link>
              <Link
                href="/register"
                className="rounded bg-amber-800 px-3 py-1 text-white hover:bg-amber-900"
              >
                Cont nou
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
