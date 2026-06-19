import Brand from "@/components/Brand";

export const metadata = { title: "For authors — academic Ledger" };

export default function ForAuthorsPage() {
  return (
    <>
      <Brand active="for-authors" />
      <div className="wrap-about">
        <p className="kicker">For authors</p>
        <h1>Get your work on the Ledger</h1>
        <p className="lede">
          academic Ledger certifies scholarship; it does not distribute or host it. Here is how to
          get a new paper on the ledger and rated.
        </p>

        <h2>We certify; we don&rsquo;t host</h2>
        <p>
          Academic publishing bundles two jobs that don&rsquo;t belong together: <b>distribution</b>{" "}
          &mdash; getting the work out &mdash; and <b>certification</b> &mdash; judging how good it
          is. Distribution is already solved; anyone can post a paper today. academic Ledger does
          only the second job: it computes{" "}
          <span className="q">
            Q<span className="a">a</span>L
          </span>
          , a calibrated estimate of a paper&rsquo;s eventual standing, over the open scholarly
          record. We point to the canonical record of your work; we never host or archive it
          ourselves.
        </p>

        <h2>How to get listed now</h2>
        <p>
          Post your working paper to an open repository that <b>mints a DOI</b> and is indexed in the
          open scholarly record. Once it&rsquo;s there, the Ledger can find, index, and rate it &mdash;
          no submission to us required. Good options:
        </p>
        <ul className="princ">
          <li>
            <b>SSRN</b> &mdash; economics, finance, management, law, and the social sciences; mints
            DOIs (the <code>10.2139/ssrn.*</code> prefix) and is well indexed.
          </li>
          <li>
            <b>arXiv</b> &mdash; physics, math, CS, and quantitative fields; indexed directly.
          </li>
          <li>
            <b>Zenodo</b> &mdash; any discipline; mints a permanent DOI (run by CERN, free).
          </li>
          <li>
            <b>OSF Preprints</b> &mdash; any discipline; DOI plus hosting.
          </li>
          <li>
            <b>bioRxiv / medRxiv</b> &mdash; biology and medicine.
          </li>
          <li>
            <b>Your institutional repository</b> &mdash; most mint DOIs and are indexed.
          </li>
        </ul>
        <p>
          The common thread is a <b>DOI</b> in the open record &mdash; that&rsquo;s what lets the
          Ledger find and rate the work, whichever repository you choose.
        </p>

        <h2>What happens next</h2>
        <p>
          Once your paper is in the open record (via OpenAlex, our data spine), the Ledger indexes
          and rates it <b>automatically</b>. A brand-new paper has no citations yet, so its QaL
          starts as an honest, wide, illustrative estimate and sharpens as real evidence accrues.
          You&rsquo;ll be able to find it here by DOI or title.
        </p>

        <div className="pull">
          Distribution is solved. Post your work where the open record can see it, and the Ledger
          does the rest.
        </div>

        <h2>A fast-track, later</h2>
        <p>
          We may eventually offer an ORCID-verified <b>fast-track</b>: deposit a new paper, mint a DOI
          (via a service such as Zenodo), and list it on the Ledger immediately, ahead of the open
          feeds. It isn&rsquo;t built yet &mdash; for now the repository route above is the way in,
          and it keeps us in our proper place: an overlay on the record, never a host.
        </p>

        <footer>
          academic Ledger &middot; research preview. We point to the canonical record of each work
          and never host or archive it; quality estimates are built from the open scholarly record
          and are illustrative pending calibration.
        </footer>
      </div>
    </>
  );
}
