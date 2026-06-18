import NextAuth from "next-auth";
import { upsertUserAndCacheWorks } from "@/lib/users";

// ── ORCID sign-in (Auth.js v5, OIDC) ──────────────────────────────────────────────────────────
// The endpoints are discovered from {issuer}/.well-known/openid-configuration, so flipping the
// ORCID *sandbox* to *production* is purely an env change — no code edit:
//   sandbox:  ORCID_ISSUER=https://sandbox.orcid.org   ORCID_API_BASE=https://pub.sandbox.orcid.org
//   prod:     ORCID_ISSUER=https://orcid.org           ORCID_API_BASE=https://pub.orcid.org
//
// JWT sessions (no database session adapter): the session is a signed cookie, so NONE of the
// metric/data tables are touched by auth. Our only writes are to our own user-data tables
// (users, orcid_works), in the signIn event below — and those are best-effort.
const ORCID_ISSUER = process.env.ORCID_ISSUER ?? "https://sandbox.orcid.org";

function nameFrom(profile: any): string {
  return (
    profile?.name ||
    [profile?.given_name, profile?.family_name].filter(Boolean).join(" ") ||
    profile?.sub ||
    "ORCID user"
  );
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  trustHost: true,
  session: { strategy: "jwt" },
  providers: [
    {
      id: "orcid",
      name: "ORCID",
      type: "oidc",
      issuer: ORCID_ISSUER,
      clientId: process.env.ORCID_CLIENT_ID,
      clientSecret: process.env.ORCID_CLIENT_SECRET,
      // ORCID supports ONLY the `openid` scope (discovery: scopes_supported = ["openid"]). Auth.js's
      // default OIDC scope is "openid profile email" — ORCID rejects the extra scopes *before* login
      // and bounces straight back as an error, so we must request openid only.
      authorization: { params: { scope: "openid" } },
      // ORCID's authorization server is happiest with a plain `state` check; its PKCE/nonce
      // support has historically been uneven (discovery advertises no PKCE).
      checks: ["state"],
      profile(profile: any) {
        return { id: profile.sub, name: nameFrom(profile), orcid: profile.sub };
      },
    },
  ],
  callbacks: {
    async jwt({ token, profile }) {
      const orcid = (profile as any)?.sub;
      if (orcid) {
        token.orcid = orcid;
        token.name = token.name || nameFrom(profile);
      }
      return token;
    },
    async session({ session, token }) {
      (session as any).orcid = (token as any).orcid ?? null;
      if (session.user) (session.user as any).orcid = (token as any).orcid ?? null;
      return session;
    },
  },
  events: {
    // Side effect ONLY in our own user-data tables (users, orcid_works) — never the metric tables.
    // Best-effort: a DB or ORCID-API hiccup must not block login (the session is a signed JWT).
    async signIn({ profile }) {
      const orcid = (profile as any)?.sub;
      if (!orcid) return;
      try {
        await upsertUserAndCacheWorks(orcid, nameFrom(profile));
      } catch (e) {
        console.error("[auth] upsertUserAndCacheWorks failed (login still succeeds):", e);
      }
    },
  },
});
