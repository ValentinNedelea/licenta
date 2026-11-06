import { Suspense } from "react";

async function BackendStatus() {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/health/`, {
    cache: "no-store",
  });
  const data = await res.json();
  return <h1 className="text-2xl font-bold">Backend: {data.status}</h1>;
}

export default function Home() {
  return (
    <main className="p-8">
      <Suspense fallback={<p>Se încarcă...</p>}>
        <BackendStatus />
      </Suspense>
    </main>
  );
}
