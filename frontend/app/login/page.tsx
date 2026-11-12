"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { errorText } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username, password);
      router.push("/");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="mb-4 text-2xl font-bold">Autentificare</h1>
      <form onSubmit={onSubmit} className="space-y-3">
        <input
          className="w-full rounded border px-3 py-2"
          placeholder="Utilizator"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <input
          className="w-full rounded border px-3 py-2"
          type="password"
          placeholder="Parolă"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && (
          <p className="whitespace-pre-line text-sm text-red-600">{error}</p>
        )}
        <button
          disabled={busy}
          className="w-full rounded bg-amber-800 py-2 text-white hover:bg-amber-900 disabled:opacity-50"
        >
          {busy ? "Se încarcă..." : "Intră în cont"}
        </button>
      </form>
      <p className="mt-4 text-sm text-stone-600">
        Nu ai cont?{" "}
        <Link href="/register" className="text-amber-800 underline">
          Creează unul
        </Link>
      </p>
    </div>
  );
}
