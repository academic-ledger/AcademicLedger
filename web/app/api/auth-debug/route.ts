import { NextResponse } from "next/server";
import { recentAuthErrors } from "@/lib/users";

// TEMPORARY C1 diagnostic — returns the most recent NextAuth errors captured to the DB. Separate
// route from the broken /api/auth/* so it loads regardless. Remove before merging C1.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({
    note: "TEMP C1 auth-error capture — remove before merge",
    errors: await recentAuthErrors(),
  });
}
