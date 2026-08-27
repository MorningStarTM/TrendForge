import { NextResponse } from "next/server";

import { setVariantStatus } from "@/lib/store";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string; variantId: string }> },
) {
  const { id, variantId } = await params;
  const { status } = await request.json().catch(() => ({}));
  if (status !== "approved" && status !== "rejected") {
    return NextResponse.json({ error: "status must be approved or rejected" }, { status: 400 });
  }
  const pkg = setVariantStatus(id, variantId, status);
  if (!pkg) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json(pkg);
}
