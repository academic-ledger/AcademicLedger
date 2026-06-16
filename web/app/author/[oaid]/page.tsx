import Brand from "@/components/Brand";
import AuthorView from "@/components/AuthorView";
import { getAuthorRecord } from "@/lib/queries";

export const dynamic = "force-dynamic";
// Keep author pages out of search indexes and don't follow links from them. (Misbehaving bots that
// ignore this are bounded separately; author works are fetched live, so this also discourages
// compliant crawlers from driving that fetch.)
export const metadata = { robots: { index: false, follow: false } };

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
