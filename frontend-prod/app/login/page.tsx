"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error ?? "Invalid credentials");
      }
      router.replace("/");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--dark)] px-4">
      {/* Ambient brand glow */}
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(600px circle at 30% 20%, rgba(255,255,70,0.10), transparent 40%)",
        }}
      />
      <div className="relative w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--brand)] text-xl font-extrabold text-[var(--brand-ink)]">
            TF
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">TrendForge</h1>
          <p className="mt-1 text-sm text-gray-400">Sign in to your content studio</p>
        </div>

        <form onSubmit={onSubmit} className="card space-y-4 p-6">
          <div>
            <label className="label" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              className="input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
            />
          </div>
          <div>
            <label className="label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
          )}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? <Spinner /> : "Sign in"}
          </Button>
        </form>
      </div>
    </div>
  );
}
