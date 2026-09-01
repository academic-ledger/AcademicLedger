import type { MetadataRoute } from "next";

// Egress control (Neon public-transfer bill, Aug 2026): the /paper and /author pages are
// calibration-pending and already noindex; /api/* and /explore are expensive per-request DB reads.
// Disallow compliant crawlers from all of them so they stop re-querying Neon on every hit. The
// non-compliant tail (e.g. Bytespider) is handled by the data-layer cache in lib/queries.ts.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      // Everyone: keep bots off the expensive dynamic routes; the marketing/static pages stay open.
      {
        userAgent: "*",
        allow: ["/$", "/about", "/for-authors", "/talk", "/check-references"],
        disallow: ["/api/", "/paper/", "/author/", "/explore"],
      },
      // Aggressive AI / scraper bots: block the whole site.
      {
        userAgent: [
          "GPTBot",
          "OAI-SearchBot",
          "ChatGPT-User",
          "ClaudeBot",
          "anthropic-ai",
          "Claude-Web",
          "CCBot",
          "Google-Extended",
          "Bytespider",
          "Amazonbot",
          "Applebot-Extended",
          "PerplexityBot",
          "meta-externalagent",
          "Diffbot",
          "cohere-ai",
        ],
        disallow: "/",
      },
    ],
  };
}
