"use client";
import { SessionProvider } from "next-auth/react";

// Wraps the app so the client-side <AuthStatus/> in the brand bar can read the session.
// (Session is JWT; this just exposes it to client components.)
export default function Providers({ children }: { children: React.ReactNode }) {
  return <SessionProvider>{children}</SessionProvider>;
}
