import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { fetchWork } from "@/lib/openalex";
import { getUserIdByOrcid, isAuthorOfWork, addNote, updateNote, deleteNote } from "@/lib/notes";

// C2 write API — the project's first AUTHENTICATED MUTATION. Every call verifies (1) an ORCID session
// and (2) that the signed-in author actually authored this paper, server-side, before any write.
// Writes only paper_notes (overlay); never the metric tables; never changes QaL.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function gate(oaid: string): Promise<{ userId: number } | { error: NextResponse }> {
  const session: any = await auth();
  const orcid = session?.orcid;
  if (!orcid) return { error: NextResponse.json({ error: "Sign in with ORCID to add a note." }, { status: 401 }) };
  const userId = await getUserIdByOrcid(orcid);
  if (!userId) return { error: NextResponse.json({ error: "No account for this ORCID." }, { status: 401 }) };
  const work = await fetchWork(oaid);
  if (!work) return { error: NextResponse.json({ error: "Unknown work." }, { status: 404 }) };
  if (!(await isAuthorOfWork(orcid, userId, work as any)))
    return { error: NextResponse.json({ error: "Only an author of this paper can add notes." }, { status: 403 }) };
  return { userId };
}

export async function POST(req: Request, { params }: { params: { oaid: string } }) {
  const g = await gate(params.oaid);
  if ("error" in g) return g.error;
  const item = await req.json().catch(() => ({}));
  try {
    const id = await addNote(g.userId, params.oaid, item);
    return NextResponse.json({ ok: true, id });
  } catch (e: any) {
    return NextResponse.json({ ok: false, error: e?.message ?? "error" }, { status: 400 });
  }
}

export async function PUT(req: Request, { params }: { params: { oaid: string } }) {
  const g = await gate(params.oaid);
  if ("error" in g) return g.error;
  const item = await req.json().catch(() => ({}));
  if (!item?.id) return NextResponse.json({ error: "id required" }, { status: 400 });
  try {
    await updateNote(g.userId, Number(item.id), item);
    return NextResponse.json({ ok: true });
  } catch (e: any) {
    return NextResponse.json({ ok: false, error: e?.message ?? "error" }, { status: 400 });
  }
}

export async function DELETE(req: Request, { params }: { params: { oaid: string } }) {
  const g = await gate(params.oaid);
  if ("error" in g) return g.error;
  const item = await req.json().catch(() => ({}));
  if (!item?.id) return NextResponse.json({ error: "id required" }, { status: 400 });
  await deleteNote(g.userId, Number(item.id));
  return NextResponse.json({ ok: true });
}
