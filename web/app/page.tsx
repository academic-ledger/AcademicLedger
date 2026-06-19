import Link from "next/link";
import Brand from "@/components/Brand";

export default function Home() {
  return (
    <>
      <Brand />
      <div className="wrap-home">
        <h1>
          All you need is Q<span className="a">a</span>L
        </h1>
        <p className="lede">
          Quality on the academic Ledger (<b>QaL</b>, said &ldquo;qual&rdquo;): a calibrated,
          continuously updated estimate of a paper&rsquo;s eventual standing among its peers, with a
          confidence interval, built on the open scholarly record. It splits the two jobs publishing
          conflates: distribution (already solved by SSRN, arXiv et al.) and certification, rebuilt
          as a measurement rather than a verdict.
        </p>
        <div className="cta">
          <Link className="primary" href="/explore">
            Explore the Ledger
          </Link>
          <Link className="secondary" href="/about">
            How it works
          </Link>
        </div>
        <p className="lede" style={{ fontSize: 13.5, color: "#6b7280", marginTop: 28 }}>
          Research preview. All QaL values are illustrative pending calibration.
        </p>
      </div>
    </>
  );
}
