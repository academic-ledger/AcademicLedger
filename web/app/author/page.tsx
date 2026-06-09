import Brand from "@/components/Brand";
import AuthorView from "@/components/AuthorView";
import { getAuthorRecord, getDefaultAuthorId } from "@/lib/queries";

export const dynamic = "force-dynamic";

// The bare /author route lands on the default author (project initiator) so the
// nav tab always shows something. Specific authors live at /author/:oaid.
export default async function AuthorIndex() {
  const id = await getDefaultAuthorId();
  const payload = id ? await getAuthorRecord(id) : null;
  return (
    <>
      <Brand active="author" />
      {payload ? (
        <AuthorView payload={payload} />
      ) : (
        <div className="notfound">No author records yet. Run the seed/pipeline to populate.</div>
      )}
    </>
  );
}
