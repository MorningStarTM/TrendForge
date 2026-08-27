import { NextResponse } from "next/server";

import { refineVariant } from "@/lib/store";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string; variantId: string }> },
) {
  const { id, variantId } = await params;
  const { notes } = await request.json().catch(() => ({}));
  if (!notes || typeof notes !== "string") {
    return NextResponse.json({ error: "notes required" }, { status: 400 });
  }
  const pkg = refineVariant(id, variantId, notes);
  if (!pkg) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json(pkg);
}
