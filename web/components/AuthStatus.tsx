"use client";
import { useSession, signIn, signOut } from "next-auth/react";

// The identity indicator in the brand bar. Signed out: a "Sign in with ORCID" button. Signed in:
// "Signed in as [name] · ORCID verified" + a sign-out control. Client-side so the static pages
// (home/about/for-authors) stay static; the session is fetched from /api/auth/session.
export default function AuthStatus() {
  const { data, status } = useSession();

  if (status === "loading") {
    return <span className="authstat authstat-loading" aria-hidden="true" />;
  }

  if (data?.user) {
    return (
      <span className="authstat">
        <span className="who">
          Signed in as <b>{data.user.name}</b>
          <span className="verified" title="Identity verified via ORCID OAuth">
            {" "}
            · ORCID verified
          </span>
        </span>
        <button className="authbtn" onClick={() => signOut()}>
          Sign out
        </button>
      </span>
    );
  }

  return (
    <button className="authbtn authbtn-in" onClick={() => signIn("orcid")}>
      Sign in with ORCID
    </button>
  );
}
