import { NextResponse } from "next/server";

import { approveTrendAndGenerate } from "@/lib/store";

export async function POST(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const pkg = approveTrendAndGenerate(id);
  if (!pkg) return NextResponse.json({ error: "Trend not found" }, { status: 404 });
  return NextResponse.json(pkg);
}
