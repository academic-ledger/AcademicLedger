import Link from "next/link";
import type { Authorship } from "@/lib/types";

// A byline with each known author name linked to their author page (§12 display rule: all
// co-authors when < 11, else first author + "et al."). Falls back to the plain string when
// per-author identity isn't available (e.g. cached records not yet re-pulled with authorships).
export default function Byline({
  authorships,
  fallback,
}: {
  authorships?: Authorship[] | null;
  fallback?: string | null;
}) {
  if (authorships && authorships.length) {
    const shown = authorships.length < 11 ? authorships : authorships.slice(0, 1);
    return (
      <>
        {shown.map((a, i) => (
          <span key={(a.oaid ?? a.name) + i}>
            {i > 0 ? ", " : ""}
            {a.oaid ? (
              <Link href={`/author/${a.oaid}`} className="aulink">
                {a.name}
              </Link>
            ) : (
              a.name
            )}
          </span>
        ))}
        {authorships.length >= 11 ? " et al." : null}
      </>
    );
  }
  return <>{fallback ?? ""}</>;
}
