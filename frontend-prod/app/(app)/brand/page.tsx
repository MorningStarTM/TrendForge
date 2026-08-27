"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Icon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Spinner } from "@/components/ui/spinner";
import {
  deleteBrandDoc,
  fetchBrandKb,
  rebuildBrandKb,
  uploadBrandDoc,
} from "@/lib/api";
import type { BrandDoc } from "@/lib/types";

const ACCEPT = ".pdf,.docx,.md,.markdown,.txt";

function formatSize(bytes: number): string {
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${bytes} B`;
}

export default function BrandPage() {
  const [docs, setDocs] = useState<BrandDoc[] | null>(null);
  const [categories, setCategories] = useState<Record<string, string>>({});
  const [category, setCategory] = useState("guidelines");
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [rebuildMsg, setRebuildMsg] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await fetchBrandKb();
      setDocs(data.documents);
      setCategories(data.categories);
    } catch (e) {
      setDocs([]);
      setError(e instanceof Error ? e.message : "Failed to load brand KB");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      for (const file of Array.from(files)) {
        await uploadBrandDoc(file, category);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function onDelete(key: string) {
    try {
      await deleteBrandDoc(key);
      setDocs((d) => d?.filter((x) => x.key !== key) ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  async function onRebuild() {
    setRebuilding(true);
    setRebuildMsg(null);
    setError(null);
    try {
      const { chunks } = await rebuildBrandKb();
      setRebuildMsg(`Re-indexed ${chunks} chunks from the brand KB.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rebuild failed");
    } finally {
      setRebuilding(false);
    }
  }

  const catLabel = (c: string) => categories[c] ?? c;

  return (
    <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
      {/* Upload */}
      <div className="h-fit space-y-4">
        <div className="card p-6">
          <div className="mb-4 flex items-center gap-2">
            <Icon.Upload className="h-5 w-5" />
            <h2 className="text-base font-bold">Upload material</h2>
          </div>

          <label className="label" htmlFor="cat">
            Category
          </label>
          <select
            id="cat"
            className="input mb-4"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {Object.entries(categories).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
            {Object.keys(categories).length === 0 && (
              <option value="guidelines">Brand guidelines</option>
            )}
          </select>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              handleFiles(e.dataTransfer.files);
            }}
            onClick={() => inputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
              dragging
                ? "border-[var(--brand-deep)] bg-[#fcfcdf]"
                : "border-[var(--line)] bg-[var(--panel-2)] hover:border-[var(--faint)]"
            }`}
          >
            {uploading ? (
              <>
                <Spinner />
                <p className="mt-2 text-sm text-gray-600">Uploading…</p>
              </>
            ) : (
              <>
                <Icon.Upload className="h-7 w-7 text-[var(--faint)]" />
                <p className="mt-2 text-sm font-medium">Drop files or click to browse</p>
                <p className="mt-0.5 text-xs text-[var(--muted)]">PDF, DOCX, Markdown, TXT</p>
              </>
            )}
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPT}
              multiple
              hidden
              onChange={(e) => handleFiles(e.target.files)}
            />
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-sm font-bold">Re-index knowledge base</h3>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Extract, chunk and embed all documents so generation can retrieve them.
          </p>
          <Button
            variant="dark"
            className="mt-3 w-full"
            onClick={onRebuild}
            disabled={rebuilding}
          >
            {rebuilding ? (
              <>
                <Spinner /> Re-indexing…
              </>
            ) : (
              <>
                <Icon.Refresh className="h-4 w-4" /> Rebuild index
              </>
            )}
          </Button>
          {rebuildMsg && (
            <p className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
              {rebuildMsg}
            </p>
          )}
        </div>
      </div>

      {/* Document list */}
      <div>
        {error && (
          <div className="card mb-4 border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            {error}
          </div>
        )}

        {docs === null ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="skeleton h-16 rounded-xl" />
            ))}
          </div>
        ) : docs.length === 0 ? (
          <div className="card flex flex-col items-center justify-center px-6 py-16 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--panel-2)] text-[var(--faint)]">
              <Icon.Brand className="h-7 w-7" />
            </div>
            <h3 className="text-base font-semibold">No documents yet</h3>
            <p className="mt-1 max-w-sm text-sm text-[var(--muted)]">
              Upload brand guidelines, do&apos;s &amp; don&apos;ts, or regional notes. They shape
              every generated caption and image.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="mb-3 text-sm text-[var(--muted)]">
              {docs.length} document{docs.length === 1 ? "" : "s"} in the knowledge base
            </p>
            {docs.map((doc) => (
              <div
                key={doc.key}
                className="card flex items-center gap-3 p-3.5 transition-shadow hover:shadow-[var(--shadow-md)]"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--panel-2)] text-[var(--muted)]">
                  <Icon.File className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{doc.filename}</p>
                  <div className="mt-0.5 flex items-center gap-2 text-xs text-[var(--muted)]">
                    <Chip tone="neutral">{catLabel(doc.category)}</Chip>
                    <span>{formatSize(doc.size)}</span>
                    {!doc.extractable && <Chip tone="amber">not indexable</Chip>}
                  </div>
                </div>
                <button
                  onClick={() => onDelete(doc.key)}
                  className="rounded-lg p-2 text-[var(--faint)] transition-colors hover:bg-red-50 hover:text-red-600"
                  title="Delete"
                >
                  <Icon.Trash className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
