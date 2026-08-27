import { proxy } from "@/lib/backend";

export async function POST(request: Request) {
  const body = await request.text();
  return proxy("/api/brand-kb/delete", { method: "POST", body });
}
