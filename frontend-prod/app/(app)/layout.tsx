import { Sidebar } from "@/components/app-shell/sidebar";
import { Topbar } from "@/components/app-shell/topbar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex">
      <Sidebar />
      <main className="flex h-screen flex-1 flex-col overflow-hidden">
        <Topbar />
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-6xl px-8 py-8">{children}</div>
        </div>
      </main>
    </div>
  );
}
