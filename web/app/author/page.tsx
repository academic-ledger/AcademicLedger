import Brand from "@/components/Brand";
import AuthorView from "@/components/AuthorView";
import { getAuthorRecord } from "@/lib/queries";

export const dynamic = "force-dynamic";

// The nav "Author" tab lands here. Default to a recognizable example author; use the in-page
// search to jump to any other author. Specific authors live at /author/:oaid.
const DEFAULT_AUTHOR = "A5003086136"; // Charles Darwin

export default async function AuthorIndex() {
  const payload = await getAuthorRecord(DEFAULT_AUTHOR);
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
