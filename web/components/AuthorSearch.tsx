"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

interface Sug {
  oaid: string;
  name: string;
  institution: string | null;
  works_count: number | null;
}

// Typeahead to jump to any author's page. Debounced query to /api/authors/search (OpenAlex
// autocomplete), a dropdown of name + institution, keyboard-navigable; selecting routes to
// the author's on-the-fly /author/{oaid} page.
export default function AuthorSearch() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<Sug[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const router = useRouter();
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(async () => {
      const term = q.trim();
      if (term.length < 2) {
        setItems([]);
        return;
      }
      try {
        const r = await fetch("/api/authors/search?q=" + encodeURIComponent(term));
        const d = await r.json();
        if (cancelled) return;
        setItems(d.items ?? []);
        setOpen(true);
        setActive(0);
      } catch {
        if (!cancelled) setItems([]);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q]);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  function go(s: Sug) {
    setOpen(false);
    setQ("");
    router.push(`/author/${s.oaid}`);
  }

  function onKey(e: React.KeyboardEvent) {
    if (!open || !items.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      go(items[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="authsearch" ref={box}>
      <input
        type="text"
        value={q}
        placeholder="Search another author…"
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={onKey}
        onFocus={() => items.length && setOpen(true)}
        aria-label="Search authors"
      />
      {open && items.length > 0 && (
        <ul className="authsug">
          {items.map((s, i) => (
            <li
              key={s.oaid}
              className={i === active ? "on" : ""}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => {
                e.preventDefault();
                go(s);
              }}
            >
              <span className="nm">{s.name}</span>
              <span className="meta">
                {s.institution || "—"}
                {s.works_count != null ? ` · ${s.works_count.toLocaleString()} works` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
