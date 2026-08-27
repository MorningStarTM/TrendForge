import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { SESSION_COOKIE } from "./lib/auth";

export function middleware(request: NextRequest) {
  const authed = Boolean(request.cookies.get(SESSION_COOKIE)?.value);
  const { pathname } = request.nextUrl;
  const isPublic = pathname.startsWith("/login") || pathname.startsWith("/api/auth");

  if (!authed && !isPublic) {
    if (pathname.startsWith("/api")) {
      return NextResponse.json({ error: "unauthorized" }, { status: 401 });
    }
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (authed && pathname.startsWith("/login")) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
