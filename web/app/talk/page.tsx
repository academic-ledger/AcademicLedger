import Brand from "@/components/Brand";

export const metadata = { title: "Talk — academic Ledger" };

// Site-framed view of the seminar deck: the academic Ledger brand bar on top, the reveal.js deck
// (served statically from /public/talk.html) filling the rest — so "Talk" stays inside the site
// environment. The raw full-screen deck is still at /talk.html for presenting (press F to fullscreen).
export default function TalkPage() {
  return (
    <>
      <Brand active="talk" />
      <iframe src="/talk.html" title="academic Ledger — seminar talk" className="talk-frame" />
    </>
  );
}
