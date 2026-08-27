"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { Icon } from "@/components/icons";
import { logout } from "@/lib/api";

const NAV = [
  { href: "/", label: "Discover", icon: Icon.Discover },
  { href: "/trends", label: "Trends", icon: Icon.Trends },
  { href: "/brand", label: "Brand KB", icon: Icon.Brand },
  { href: "/settings", label: "Settings", icon: Icon.Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  async function onLogout() {
    await logout();
    router.replace("/login");
    router.refresh();
  }

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col bg-[var(--dark)] text-white">
      <div className="flex items-center gap-3 px-6 py-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--brand)] text-base font-extrabold text-[var(--brand-ink)]">
          TF
        </div>
        <div className="leading-tight">
          <div className="font-bold tracking-tight">TrendForge</div>
          <div className="text-[11px] text-gray-500">Content Studio</div>
        </div>
      </div>

      <nav className="mt-2 flex-1 space-y-1 px-3">
        {NAV.map(({ href, label, icon: IconCmp }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              className={`group flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-colors ${
                active
                  ? "bg-[var(--brand)] text-[var(--brand-ink)]"
                  : "text-gray-400 hover:bg-white/[0.06] hover:text-white"
              }`}
            >
              <IconCmp className="h-[18px] w-[18px]" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-white/10 p-3">
        <button
          onClick={onLogout}
          className="flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium text-gray-400 transition-colors hover:bg-white/[0.06] hover:text-white"
        >
          <Icon.Logout className="h-[18px] w-[18px]" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
