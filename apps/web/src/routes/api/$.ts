import { createFileRoute } from "@tanstack/react-router";
import type {} from "@tanstack/start-client-core";

const HOP_BY_HOP_REQUEST_HEADERS = [
  "host",
  "accept-encoding",
  "connection",
  "keep-alive",
  "transfer-encoding",
  "te",
  "trailer",
  "upgrade",
] as const;

const HOP_BY_HOP_RESPONSE_HEADERS = [
  "content-encoding",
  "content-length",
  "transfer-encoding",
  "connection",
] as const;

async function proxy(request: Request): Promise<Response> {
  const target = process.env.API_TARGET || "http://localhost:8100";
  const incoming = new URL(request.url);
  const upstream = new URL(incoming.pathname + incoming.search, target);

  const headers = new Headers(request.headers);
  for (const name of HOP_BY_HOP_REQUEST_HEADERS) headers.delete(name);
  headers.set("host", upstream.host);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const resp = await fetch(upstream, {
    method: request.method,
    headers,
    body: hasBody ? request.body : undefined,
    // @ts-expect-error Node fetch requires duplex to stream a request body
    duplex: hasBody ? "half" : undefined,
    redirect: "manual",
  });

  const responseHeaders = new Headers(resp.headers);
  for (const name of HOP_BY_HOP_RESPONSE_HEADERS) responseHeaders.delete(name);

  return new Response(resp.body, {
    status: resp.status,
    statusText: resp.statusText,
    headers: responseHeaders,
  });
}

export const Route = createFileRoute("/api/$")({
  server: {
    handlers: {
      GET: ({ request }) => proxy(request),
      POST: ({ request }) => proxy(request),
      PUT: ({ request }) => proxy(request),
      PATCH: ({ request }) => proxy(request),
      DELETE: ({ request }) => proxy(request),
      HEAD: ({ request }) => proxy(request),
      OPTIONS: ({ request }) => proxy(request),
    },
  },
});
