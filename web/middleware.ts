import { NextResponse, type NextRequest } from "next/server";

// Egress control (Neon public-transfer bill, Aug 2026). robots.txt stops COMPLIANT crawlers; this
// middleware stops the non-compliant ones (which ignore robots.txt) and throttles bursts, so no bot
// can re-query Neon on every hit. Applies only to the expensive DB-backed routes (see `config`).

// User-agents to block outright on these routes: AI scrapers + aggressive SEO crawlers + generic
// scraping libraries. Real browsers and the app's own client fetches are unaffected. Trim as needed.
const BLOCKED_UA =
  /(bytespider|gptbot|oai-searchbot|chatgpt-user|ccbot|claudebot|anthropic-ai|claude-web|google-extended|perplexitybot|amazonbot|applebot-extended|meta-externalagent|diffbot|cohere-ai|dataforseo|semrushbot|ahrefsbot|mj12bot|dotbot|petalbot|megaindex|imagesiftbot|scrapy|python-requests|python-urllib|go-http-client|okhttp|libwww-perl|curl\/|wget\/)/i;

// Best-effort per-IP burst limiter. In-memory + per edge instance, so it catches rapid bursts but is
// not a durable global limit — for that, back it with Vercel KV / Upstash. Numbers are generous for
// humans (a page load is a handful of requests) and tight for scrapers.
const WINDOW_MS = 10_000;
const MAX_HITS = 40;
const hits = new Map<string, { n: number; reset: number }>();

function rateLimited(ip: string): boolean {
  const now = Date.now();
  if (hits.size > 5000) hits.clear(); // cheap unbounded-growth guard
  const e = hits.get(ip);
  if (!e || now > e.reset) {
    hits.set(ip, { n: 1, reset: now + WINDOW_MS });
    return false;
  }
  e.n += 1;
  return e.n > MAX_HITS;
}

export function middleware(req: NextRequest) {
  const ua = req.headers.get("user-agent") || "";
  if (!ua || BLOCKED_UA.test(ua)) {
    return new NextResponse("Forbidden", { status: 403 });
  }
  const ip =
    (req as any).ip ||
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    "0.0.0.0";
  if (rateLimited(ip)) {
    return new NextResponse("Too Many Requests", {
      status: 429,
      headers: { "Retry-After": "10" },
    });
  }
  return NextResponse.next();
}

// Guard only the expensive, DB-backed routes; static assets, _next, and marketing pages are untouched.
export const config = {
  matcher: ["/paper/:path*", "/author/:path*", "/explore/:path*", "/api/:path*"],
};
