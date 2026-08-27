"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { fetchSystem, logout } from "@/lib/api";
import type { SystemInfo } from "@/lib/types";

export default function SettingsPage() {
  const router = useRouter();
  const [sys, setSys] = useState<SystemInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSystem()
      .then(setSys)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  async function onLogout() {
    await logout();
    router.replace("/login");
    router.refresh();
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* Account */}
      <section className="card p-6">
        <span className="eyebrow">Account</span>
        <div className="mt-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--brand)] text-sm font-extrabold text-[var(--brand-ink)]">
              OP
            </div>
            <div>
              <p className="text-sm font-semibold">Operator</p>
              <p className="text-xs text-[var(--muted)]">Single-user internal account</p>
            </div>
          </div>
          <Button variant="ghost" onClick={onLogout}>
            <Icon.Logout className="h-4 w-4" /> Sign out
          </Button>
        </div>
        <p className="mt-4 rounded-xl bg-[var(--panel-2)] p-3 text-xs text-[var(--muted)]">
          Login credentials are set via the <code className="font-semibold">DASHBOARD_USERNAME</code>{" "}
          and <code className="font-semibold">DASHBOARD_PASSWORD</code> environment variables.
        </p>
      </section>

      {/* Integrations status */}
      <section className="card p-6">
        <span className="eyebrow">Integrations</span>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        {!sys && !error ? (
          <div className="mt-3 space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="skeleton h-6 rounded-lg" />
            ))}
          </div>
        ) : (
          sys && (
            <div className="mt-3 grid gap-2.5 sm:grid-cols-2">
              <StatusRow label="Post discovery (ScrapeCreators)" ok={sys.configured.scrapecreators} />
              <StatusRow label="Text generation (Bedrock)" ok={sys.configured.bedrock} />
              <StatusRow label="Image generation (Gemini)" ok={sys.configured.gemini} />
              <StatusRow label="Embeddings (Hugging Face)" ok={sys.configured.embeddings} />
            </div>
          )
        )}
      </section>

      {/* Configuration */}
      {sys && (
        <section className="card p-6">
          <span className="eyebrow">Configuration</span>
          <dl className="mt-3 divide-y divide-[var(--line-2)]">
            <Row label="Detection model" value={sys.models.detection} />
            <Row label="Generation model" value={sys.models.generation} />
            <Row label="Image model" value={sys.models.image} />
            <Row label="Embedding model" value={sys.models.embeddings} />
            <Row label="Bedrock region" value={sys.regions.bedrock} />
            <Row label="AWS region" value={sys.regions.aws} />
            <Row label="Brand KB bucket" value={sys.brand_kb_bucket} />
            <Row
              label="Discovery credits"
              value={sys.credits === null ? "—" : sys.credits.toLocaleString()}
            />
          </dl>
        </section>
      )}
    </div>
  );
}

function StatusRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-[var(--line)] bg-[var(--panel-2)] px-3.5 py-2.5">
      <span
        className={`flex h-5 w-5 items-center justify-center rounded-full ${
          ok ? "bg-emerald-100 text-emerald-600" : "bg-gray-200 text-gray-400"
        }`}
      >
        {ok ? <Icon.Check className="h-3 w-3" /> : <span className="text-[10px]">—</span>}
      </span>
      <span className="text-sm">{label}</span>
      <span className={`ml-auto text-xs font-medium ${ok ? "text-emerald-600" : "text-[var(--faint)]"}`}>
        {ok ? "Connected" : "Not set"}
      </span>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <dt className="text-sm text-[var(--muted)]">{label}</dt>
      <dd className="truncate text-right font-mono text-xs text-[var(--ink)]">{value}</dd>
    </div>
  );
}
