import { proxyForm } from "@/lib/backend";

// Forward the multipart upload to the backend unchanged.
export async function POST(request: Request) {
  const form = await request.formData();
  return proxyForm("/api/brand-kb/upload", form);
}
