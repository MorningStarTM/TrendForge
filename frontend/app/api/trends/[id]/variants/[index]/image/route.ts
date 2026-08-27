import { proxy } from "@/lib/backend";

// Render an image (Gemini nano banana) for one caption variant. Returns a
// base64 data URL the UI displays and lets the user download.
export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string; index: string }> },
) {
  const { id, index } = await params;
  return proxy(`/api/trends/${id}/variants/${index}/image`, { method: "POST" });
}
