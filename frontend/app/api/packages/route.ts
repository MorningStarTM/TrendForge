import { NextResponse } from "next/server";

import { listPackages } from "@/lib/store";

export async function GET() {
  return NextResponse.json(listPackages());
}
