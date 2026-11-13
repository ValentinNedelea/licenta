"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Me = {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  avatar_url: string;
  bio: string;
  country: string;
  date_of_birth: string | null;
  date_joined: string;
};

export default function ProfilePage() {
  const { user, loading } = useAuth();
  const [me, setMe] = useState<Me | null>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    api<Me>("/api/auth/me/").then(setMe);
  }, [user]);

  if (loading) return <p className="text-stone-500">Se încarcă...</p>;
  if (!user) {
    return (
      <p>
        <Link href="/login" className="text-amber-800 underline">
          Autentifică-te
        </Link>{" "}
        ca să-ți vezi profilul.
      </p>
    );
  }
  if (!me) return <p className="text-stone-500">Se încarcă...</p>;

  const set = (k: keyof Me, v: string) => setMe({ ...me, [k]: v });

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!me) return;
    setBusy(true);
    setMsg("");
    try {
      await api("/api/auth/me/", {
        method: "PATCH",
        body: JSON.stringify({
          first_name: me.first_name,
          last_name: me.last_name,
          avatar_url: me.avatar_url,
          bio: me.bio,
          country: me.country,
          date_of_birth: me.date_of_birth || null,
        }),
      });
      setMsg("Profil salvat.");
    } catch (err) {
      setMsg(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  const input = "w-full rounded border bg-white px-3 py-2";

  return (
    <div className="mx-auto max-w-lg">
      <div className="mb-4 flex items-center gap-4">
        {me.avatar_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={me.avatar_url}
            alt=""
            className="h-16 w-16 rounded-full object-cover"
            referrerPolicy="no-referrer"
          />
        ) : (
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-amber-200 text-2xl font-bold text-amber-900">
            {me.username[0]?.toUpperCase()}
          </div>
        )}
        <div>
          <h1 className="text-2xl font-bold">{me.username}</h1>
          <p className="text-sm text-stone-500">
            {me.email} · membru din {me.date_joined.slice(0, 10)}
          </p>
        </div>
      </div>

      <form onSubmit={save} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <input
            className={input}
            placeholder="Prenume"
            value={me.first_name}
            onChange={(e) => set("first_name", e.target.value)}
          />
          <input
            className={input}
            placeholder="Nume"
            value={me.last_name}
            onChange={(e) => set("last_name", e.target.value)}
          />
        </div>
        <input
          className={input}
          placeholder="Link poză de profil"
          value={me.avatar_url}
          onChange={(e) => set("avatar_url", e.target.value)}
        />
        <textarea
          className={input}
          rows={4}
          placeholder="Despre tine"
          value={me.bio}
          onChange={(e) => set("bio", e.target.value)}
        />
        <input
          className={input}
          placeholder="Țara"
          value={me.country}
          onChange={(e) => set("country", e.target.value)}
        />
        <label className="block text-sm">
          Data nașterii
          <input
            type="date"
            className={input}
            value={me.date_of_birth ?? ""}
            onChange={(e) => set("date_of_birth", e.target.value)}
          />
        </label>
        {msg && (
          <p className="whitespace-pre-line text-sm text-stone-600">{msg}</p>
        )}
        <button
          disabled={busy}
          className="rounded bg-amber-800 px-4 py-2 text-white hover:bg-amber-900 disabled:opacity-50"
        >
          Salvează
        </button>
      </form>
    </div>
  );
}
