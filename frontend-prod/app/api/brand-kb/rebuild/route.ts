import { proxy } from "@/lib/backend";

export async function POST() {
  return proxy("/api/brand-kb/rebuild", { method: "POST" });
}
