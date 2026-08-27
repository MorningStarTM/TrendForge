import { proxy } from "@/lib/backend";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string; index: string }> },
) {
  const { id, index } = await params;
  return proxy(`/api/trends/${id}/variants/${index}/image`, { method: "POST" });
}
