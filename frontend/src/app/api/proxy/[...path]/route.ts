import { NextRequest, NextResponse } from "next/server";

/**
 * Server-side proxy to the FastAPI dashboard backend. The backend API key
 * (BACKEND_API_KEY, no NEXT_PUBLIC_ prefix) is attached here and never sent
 * to the browser — client code only ever calls this same-origin route.
 */
async function forward(request: NextRequest, path: string[], method: "GET" | "POST") {
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

  const headers: Record<string, string> = { "X-API-Key": apiKey };
  let body: string | undefined;
  if (method === "POST") {
    body = await request.text();
    headers["Content-Type"] = "application/json";
  }

  let upstream: Response;
  try {
    upstream = await fetch(targetUrl, { method, headers, body, cache: "no-store" });
  } catch (error) {
    // Include the underlying cause — a bare "could not reach" is impossible to
    // diagnose in a deployment, where the difference between a DNS failure, a
    // refused connection and a TLS error decides what you go and fix.
    const cause = error instanceof Error ? (error.cause ?? error).toString() : String(error);
    return NextResponse.json(
      { detail: `Could not reach backend at ${baseUrl}: ${cause}` },
      { status: 502 }
    );
  }

  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
  });
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return forward(request, path, "GET");
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return forward(request, path, "POST");
}
