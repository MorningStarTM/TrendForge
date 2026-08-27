import { Icon } from "@/components/icons";
import type { SourcePost } from "@/lib/types";

function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return `${n}`;
}

export function PostThumb({ post }: { post: SourcePost }) {
  const isVideo = post.media_type === "video";
  const body = (
    <>
      <div className="relative aspect-[4/5] w-full overflow-hidden bg-gray-100">
        {post.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={post.thumbnail_url}
            alt={post.text?.slice(0, 60) || "Post"}
            referrerPolicy="no-referrer"
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-gray-300">
            <Icon.Image className="h-8 w-8" />
          </div>
        )}
        <span className="absolute left-2 top-2 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white backdrop-blur">
          {post.platform}
        </span>
        <span className="absolute right-2 top-2 rounded-md bg-black/60 p-1 text-white backdrop-blur">
          {isVideo ? <Icon.Play className="h-3 w-3" /> : <Icon.Image className="h-3 w-3" />}
        </span>
      </div>
      <div className="space-y-1.5 p-2.5">
        <p className="line-clamp-2 min-h-[2.1rem] text-[11px] leading-snug text-gray-600">
          {post.text || "—"}
        </p>
        <div className="flex items-center gap-3 text-[11px] font-medium text-gray-500">
          <span className="inline-flex items-center gap-1">
            <Icon.Heart className="h-3 w-3" /> {compact(post.likes)}
          </span>
          <span className="inline-flex items-center gap-1">
            <Icon.Comment className="h-3 w-3" /> {compact(post.comments)}
          </span>
          {post.audio_title && (
            <span className="ml-auto inline-flex max-w-[45%] items-center gap-1 truncate text-[#caab00]">
              <Icon.Music className="h-3 w-3 shrink-0" />
              <span className="truncate">{post.audio_title}</span>
            </span>
          )}
        </div>
      </div>
    </>
  );

  const className =
    "group block overflow-hidden rounded-xl border border-[var(--line)] bg-white transition-shadow hover:shadow-[var(--shadow-md)]";

  return post.url ? (
    <a href={post.url} target="_blank" rel="noreferrer" className={className}>
      {body}
    </a>
  ) : (
    <div className={className}>{body}</div>
  );
}
