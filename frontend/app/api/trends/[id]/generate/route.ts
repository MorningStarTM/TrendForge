import { proxy } from "@/lib/backend";

// Real content generation (Haiku classify + Sonnet captions/prompts via Bedrock).
export async function POST(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxy(`/api/trends/${id}/generate`, { method: "POST" });
}
