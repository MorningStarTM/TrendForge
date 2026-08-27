import { proxy } from "@/lib/backend";

// Real detected trends from the Python rule engine.
export async function GET() {
  return proxy("/api/trends");
}
