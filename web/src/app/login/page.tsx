"use client";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function LoginForm() {
  const [code, setCode] = useState("");
  const [err, setErr] = useState(false);
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  const next = useSearchParams().get("next") || "/";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(false);
    const res = await fetch("/api/auth", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ code }),
    });
    setBusy(false);
    if (res.ok) router.replace(next);
    else setErr(true);
  }

  return (
    <form onSubmit={submit} className="w-full max-w-xs space-y-4">
      <h1 className="text-lg font-semibold text-zinc-100">Watchlist</h1>
      <input
        type="password"
        inputMode="numeric"
        autoFocus
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="Passcode"
        className="w-full rounded-lg bg-zinc-900 px-4 py-3 text-zinc-100 ring-1 ring-zinc-800 outline-none focus:ring-sky-500"
      />
      {err && <p className="text-sm text-rose-400">Incorrect passcode.</p>}
      <button
        disabled={busy}
        className="w-full rounded-lg bg-sky-500 py-3 font-medium text-white disabled:opacity-50"
      >
        {busy ? "…" : "Enter"}
      </button>
    </form>
  );
}

export default function Login() {
  return (
    <main className="min-h-dvh grid place-items-center bg-zinc-950 px-6">
      <Suspense>
        <LoginForm />
      </Suspense>
    </main>
  );
}
