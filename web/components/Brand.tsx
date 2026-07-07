import Link from "next/link";
import AuthStatus from "./AuthStatus";

type Tab = "explore" | "check-references" | "author" | "about" | "for-authors" | "talk" | null;

export default function Brand({
  active = null,
  badge = "BETA",
}: {
  active?: Tab;
  badge?: string;
}) {
  return (
    <header className="brand">
      <div className="left">
        <Link className="lock" href="/" title="academic Ledger">
          <span className="al">
            <span className="i">a</span>L
          </span>
          <span className="nm">
            <span className="ac">academic</span>
            <span className="le">Ledger</span>
          </span>
        </Link>
        <span className="proto" title="Beta — QaL values are illustrative pending calibration">
          {badge}
        </span>
      </div>
      <nav className="nav">
        <Link className={active === "explore" ? "on" : ""} href="/explore">
          Explore
        </Link>
        <Link className={active === "check-references" ? "on" : ""} href="/check-references">
          Check refs
        </Link>
        <Link className={active === "author" ? "on" : ""} href="/author">
          Author
        </Link>
        <Link className={active === "about" ? "on" : ""} href="/about">
          About
        </Link>
        <Link className={active === "for-authors" ? "on" : ""} href="/for-authors">
          For authors
        </Link>
        <Link className={active === "talk" ? "on" : ""} href="/talk">
          Talk
        </Link>
        <AuthStatus />
      </nav>
    </header>
  );
}
