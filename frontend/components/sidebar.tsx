"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { logout } from "@/lib/api";

const NAV = [
  { href: "/", label: "Pull Posts", step: "1" },
  { href: "/trends", label: "Trends", step: "2" },
  { href: "/generated", label: "Generated", step: "3" },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  async function onLogout() {
    await logout();
    router.replace("/login");
    router.refresh();
  }

  const linkClass = (active: boolean) =>
    `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
      active ? "bg-[var(--brand)] text-[var(--brand-ink)]" : "text-gray-300 hover:bg-white/10"
    }`;

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col bg-[var(--dark)] text-white">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--brand)] text-sm font-extrabold text-[var(--brand-ink)]">
          TF
        </div>
        <div className="font-bold leading-tight">
          TrendForge
          <div className="text-[11px] font-normal text-gray-400">Content Console</div>
        </div>
      </div>

      <div className="px-5 pb-2 pt-2 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
        Workflow
      </div>
      <nav className="space-y-1 px-3">
        {NAV.map((item) => {
          const active = isActive(item.href);
          return (
            <Link key={item.href} href={item.href} className={linkClass(active)}>
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold ${
                  active ? "bg-[var(--brand-ink)] text-[var(--brand)]" : "bg-white/10 text-gray-300"
                }`}
              >
                {item.step}
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <nav className="mt-4 flex-1 px-3">
        <Link href="/history" className={linkClass(isActive("/history"))}>
          <span aria-hidden>🕑</span>
          History
        </Link>
      </nav>

      <div className="border-t border-white/10 p-3">
        <button
          onClick={onLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-300 hover:bg-white/10"
        >
          <span aria-hidden>⎋</span>
          Sign out
        </button>
      </div>
    </aside>
  );
}
