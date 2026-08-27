import { proxy } from "@/lib/backend";

export async function GET() {
  return proxy("/api/credits");
}
