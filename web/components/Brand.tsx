import Link from "next/link";
import AuthStatus from "./AuthStatus";

type Tab = "explore" | "author" | "about" | "for-authors" | null;

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
        <Link className={active === "author" ? "on" : ""} href="/author">
          Author
        </Link>
        <Link className={active === "about" ? "on" : ""} href="/about">
          About
        </Link>
        <Link className={active === "for-authors" ? "on" : ""} href="/for-authors">
          For authors
        </Link>
        {/* static reveal.js deck served from /public, so a plain anchor (not router Link) */}
        <a href="/talk.html">Talk</a>
        <AuthStatus />
      </nav>
    </header>
  );
}
