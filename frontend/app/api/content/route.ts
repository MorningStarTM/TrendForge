import { NextResponse } from "next/server";

import { getPackageByTrend } from "@/lib/store";

export async function GET(request: Request) {
  const trendId = new URL(request.url).searchParams.get("trend");
  if (!trendId) return NextResponse.json({ error: "trend query param required" }, { status: 400 });
  const pkg = getPackageByTrend(trendId);
  if (!pkg) return NextResponse.json({ error: "No content package for trend" }, { status: 404 });
  return NextResponse.json(pkg);
}
