"use client";
import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

// Behavior gate (client side): the expensive synthetic-field compute is triggered ONLY here, after
// the page has mounted in a real browser. Flat crawler GETs don't run this effect, so they never
// trigger the compute — they just keep the cheap universal layer the server rendered. On success the
// compute is cached server-side, so we refresh the server component to swap in the official
// synthetic-field headline. No-ops when the server already served the synthetic field.
export default function SyntheticLoader({ oaid, needed }: { oaid: string; needed: boolean }) {
  const router = useRouter();
  const ran = useRef(false);
  useEffect(() => {
    if (!needed || ran.current) return;
    ran.current = true;
    (async () => {
      try {
        const r = await fetch(`/api/synthetic/${oaid}`, { method: "POST" });
        const j = await r.json().catch(() => ({}));
        if (j?.ok) router.refresh();
      } catch {
        /* leave the universal layer in place */
      }
    })();
  }, [oaid, needed, router]);
  return null;
}
