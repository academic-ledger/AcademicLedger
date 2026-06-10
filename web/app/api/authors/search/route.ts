import { NextResponse } from "next/server";
import { autocompleteAuthors } from "@/lib/openalex";

export const dynamic = "force-dynamic";

// Author typeahead: proxies OpenAlex /autocomplete/authors so the premium key stays server-side.
export async function GET(req: Request) {
  const q = new URL(req.url).searchParams.get("q") || "";
  try {
    return NextResponse.json({ items: await autocompleteAuthors(q) });
  } catch {
    return NextResponse.json({ items: [] });
  }
}
