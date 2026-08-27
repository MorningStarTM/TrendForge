import { CreditsBadge } from "@/components/credits-badge";
import { Sidebar } from "@/components/sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex">
      <Sidebar />
      <main className="flex h-screen flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-end border-b border-[var(--line)] bg-white px-8 py-3">
          <CreditsBadge />
        </header>
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-6xl px-8 py-8">{children}</div>
        </div>
      </main>
    </div>
  );
}
