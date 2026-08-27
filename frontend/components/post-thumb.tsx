import { Badge } from "@/components/ui/badge";
import type { SourcePost } from "@/lib/types";

// A single viewable post: its image (thumbnail) + platform + engagement. Uses a
// plain <img> because the thumbnails come from arbitrary platform CDNs (IG,
// TikTok), which next/image would require whitelisting.

export function PostThumb({ post }: { post: SourcePost }) {
  const inner = (
    <div className="group overflow-hidden rounded-lg border border-[var(--line)] bg-white">
      <div className="relative aspect-square w-full bg-gray-100">
        {post.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={post.thumbnail_url}
            alt={post.text.slice(0, 60) || "post"}
            loading="lazy"
            referrerPolicy="no-referrer"
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-xs text-gray-400">
            no image
          </div>
        )}
        <div className="absolute left-2 top-2">
          <Badge tone="brand">{post.platform}</Badge>
        </div>
      </div>
      <div className="p-2">
        <p className="line-clamp-2 text-xs text-gray-600">{post.text || "—"}</p>
        <p className="mt-1 text-[11px] text-[var(--muted)]">
          ♥ {post.likes.toLocaleString()} · 💬 {post.comments.toLocaleString()}
        </p>
      </div>
    </div>
  );

  return post.url ? (
    <a href={post.url} target="_blank" rel="noreferrer" title="Open original post">
      {inner}
    </a>
  ) : (
    inner
  );
}
