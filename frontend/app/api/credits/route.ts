import { proxy } from "@/lib/backend";

// Live ScrapeCreators credit balance, proxied from the Python backend.
export async function GET() {
  return proxy("/api/credits");
}
