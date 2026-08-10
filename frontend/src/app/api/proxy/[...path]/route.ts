import { NextRequest, NextResponse } from "next/server";

/**
 * Server-side proxy to the FastAPI dashboard backend. The backend API key
 * (BACKEND_API_KEY, no NEXT_PUBLIC_ prefix) is attached here and never sent
 * to the browser — client code only ever calls this same-origin route.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const baseUrl = process.env.BACKEND_API_BASE_URL;
  const apiKey = process.env.BACKEND_API_KEY;

  if (!baseUrl || !apiKey) {
    return NextResponse.json(
      { detail: "Frontend misconfigured: BACKEND_API_BASE_URL / BACKEND_API_KEY not set" },
      { status: 500 }
    );
  }

  const targetUrl = new URL(`/api/${path.join("/")}`, baseUrl);
  request.nextUrl.searchParams.forEach((value, key) => {
    targetUrl.searchParams.append(key, value);
  });

  let upstream: Response;
  try {
    upstream = await fetch(targetUrl, {
      headers: { "X-API-Key": apiKey },
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: `Could not reach backend at ${baseUrl}` },
      { status: 502 }
    );
  }

  const body = await upstream.text();
  return new NextResponse(body, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
  });
}
