import Brand from "@/components/Brand";

export default function AboutPage() {
  return (
    <>
      <Brand active="about" />
      <div className="wrap-about">
        <p className="kicker">About academic Ledger</p>
        <h1>
          All you need is{" "}
          <span className="q">
            Q<span className="a">a</span>L
          </span>
        </h1>
        <p className="lede">
          A calibrated, continuously updated estimate of a paper&rsquo;s eventual quality, built on
          the open scholarly record.
        </p>

        <p>
          <a className="talk-link" href="/talk.html">
            &#9654;&nbsp; View the seminar talk
          </a>
        </p>

        <h2>The big idea</h2>
        <p>
          Academic publishing bundles two jobs that do not belong together: <b>distribution</b>,
          getting the work out, and <b>certification</b>, deciding how good it is. Distribution is
          effectively solved; anyone can post a paper today. Certification is the hard part, and the
          journal system does it slowly, expensively, and noisily, compressing a rich question into a
          binary accept-or-reject verdict delivered years late.
        </p>
        <p>
          academic Ledger separates the two. It leaves distribution to the existing hosts and
          rebuilds certification as a measurement. In place of a label, it reports <b>QaL</b> (said
          &ldquo;qual&rdquo;): an estimate of where a paper will eventually stand among its peers,
          expressed as a percentile with an honest interval rather than a yes or no.
        </p>

        <div className="pull">
          Quality is not a stamp you earn once. It is a quantity you can estimate, refine as evidence
          arrives, and report with its uncertainty attached.
        </div>

        <h2>The philosophy</h2>
        <ul className="princ">
          <li>
            <b>Quality is a percentile, not a label.</b> A paper&rsquo;s standing is relative to its
            field and its vintage, reported on a continuous scale.
          </li>
          <li>
            <b>Decide late.</b> We do not pretend to know a young paper&rsquo;s fate. Early estimates
            carry wide intervals that narrow only as real evidence accumulates.
          </li>
          <li>
            <b>Be honest about uncertainty.</b> Every estimate travels with an interval and a
            reference class. No false precision.
          </li>
          <li>
            <b>Transparency over secrecy.</b> The method and inputs are open and auditable; resistance
            to gaming comes from construction, not from hidden formulas.
          </li>
          <li>
            <b>No score for a person.</b> Quality is reported per paper. We deliberately do not roll a
            scholar up to a single number.
          </li>
          <li>
            <b>Built on the open record.</b> The estimate rests on open, reproducible data, so anyone
            can check it and no one has to pay to see it.
          </li>
        </ul>

        <h2>The approach</h2>
        <p>
          The Ledger begins as a lens over the public record. Using the open scholarly graph, it
          computes QaL for any indexed paper with no participants required and no cold start. A
          paper&rsquo;s reference class is the community it actually travels with in citations, which
          keeps the estimate robust to the coarse, single-field labels that mislabel interdisciplinary
          work. Human review and conferred tiers can be layered on later; the measurement comes first.
        </p>
        <p>
          Estimates are calibrated against history: we learn, from communities observed to maturity,
          how an early signal maps to eventual standing, and apply that mapping to new work.
          Calibration starts with the fields we know best in operations, information systems, and
          decision sciences, and expands from there.
        </p>

        <h2>Transparency</h2>
        <p>
          academic Ledger is an independent, non-commercial initiative built on principles of
          transparency. The full codebase and documentation can be viewed at{" "}
          <a href="https://github.com/ktulrich/AcademicLedger" target="_blank" rel="noopener noreferrer">
            our git repository
          </a>
          , and a white paper describing the methodology is{" "}
          <a href="/whitepaper.html">here</a>.
        </p>

        <div className="who">
          <h2>Who, and how to reach us</h2>
          <p className="names">Initiated by G&eacute;rard Cachon, Christian Terwiesch, and Karl Ulrich.</p>
          <p style={{ marginBottom: 0 }}>
            academic Ledger is a work in progress, currently in Beta; the numbers shown today are
            illustrative pending calibration. We welcome reactions, criticism, and ideas. Contact any
            one of us through the usual methods with your feedback.
          </p>
        </div>

        <footer>
          academic Ledger · Beta. Quality estimates are built from the open scholarly
          record and are illustrative pending calibration.
        </footer>
      </div>
    </>
  );
}
