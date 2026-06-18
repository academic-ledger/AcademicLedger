import { NextResponse } from "next/server";

// TEMPORARY C1 diagnostic — reports whether each auth env var is PRESENT on this deployment
// (booleans + the non-secret issuer/url values only; never the secret values themselves).
// Remove before merging C1. Behind Vercel deployment protection on previews.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const present = (k: string) => Boolean(process.env[k] && String(process.env[k]).length > 0);
  return NextResponse.json({
    note: "C1 env presence check — booleans only, no secret values. Remove before merge.",
    AUTH_SECRET: present("AUTH_SECRET"),
    NEXTAUTH_SECRET_legacy: present("NEXTAUTH_SECRET"),
    ORCID_CLIENT_ID: present("ORCID_CLIENT_ID"),
    ORCID_CLIENT_SECRET: present("ORCID_CLIENT_SECRET"),
    ORCID_ISSUER: process.env.ORCID_ISSUER ?? "(unset → code default https://sandbox.orcid.org)",
    ORCID_API_BASE: process.env.ORCID_API_BASE ?? "(unset → code default https://pub.sandbox.orcid.org)",
    AUTH_URL: process.env.AUTH_URL ?? "(unset)",
    DATABASE_URL: present("DATABASE_URL"),
  });
}
