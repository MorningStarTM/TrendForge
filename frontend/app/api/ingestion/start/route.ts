import { proxy } from "@/lib/backend";

// Real pull → normalize → detect, proxied to the Python backend.
export async function POST(request: Request) {
  const body = await request.text();
  return proxy("/api/ingestion/start", { method: "POST", body });
}
