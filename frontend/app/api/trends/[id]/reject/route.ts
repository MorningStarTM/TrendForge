import { NextResponse } from "next/server";

import { rejectTrend } from "@/lib/store";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { notes } = await request.json().catch(() => ({}));
  const trend = rejectTrend(id, notes);
  if (!trend) return NextResponse.json({ error: "Trend not found" }, { status: 404 });
  return NextResponse.json(trend);
}
