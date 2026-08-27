import { NextResponse } from "next/server";

import { SESSION_COOKIE, getCredentials, makeSessionToken } from "@/lib/auth";

export async function POST(request: Request) {
  const { username, password } = await request.json().catch(() => ({}));
  const expected = getCredentials();

  if (username !== expected.username || password !== expected.password) {
    return NextResponse.json({ error: "Invalid username or password" }, { status: 401 });
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSION_COOKIE, makeSessionToken(), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 12, // 12h
  });
  return res;
}
