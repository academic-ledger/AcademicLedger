import Brand from "@/components/Brand";
import AuthorView from "@/components/AuthorView";
import { getAuthorRecord } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function AuthorPage({ params }: { params: { oaid: string } }) {
  const payload = await getAuthorRecord(params.oaid);
  return (
    <>
      <Brand active="author" />
      {payload ? (
        <AuthorView payload={payload} />
      ) : (
        <div className="notfound">No author record for {params.oaid}.</div>
      )}
    </>
  );
}
