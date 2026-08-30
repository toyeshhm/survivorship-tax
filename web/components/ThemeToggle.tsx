"use client";

import { useEffect, useState } from "react";

type Mode = "system" | "light" | "dark";

/**
 * Three-state theme control. "System" stamps no attribute, so the page follows
 * prefers-color-scheme; the explicit choices stamp data-theme and win in both
 * directions. Reads and writes are guarded: storage throws in some contexts.
 */
export function ThemeToggle() {
  const [mode, setMode] = useState<Mode>("system");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("svtax-theme") as Mode | null;
      if (saved === "light" || saved === "dark" || saved === "system") setMode(saved);
    } catch {
      /* private mode or blocked site data: fall back to system */
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (mode === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", mode);
    try {
      localStorage.setItem("svtax-theme", mode);
    } catch {
      /* non-fatal: the theme still applies for this page view */
    }
  }, [mode]);

  const next: Record<Mode, Mode> = { system: "light", light: "dark", dark: "system" };
  const label: Record<Mode, string> = { system: "Auto", light: "Light", dark: "Dark" };

  return (
    <button
      type="button"
      onClick={() => setMode(next[mode])}
      aria-label={`Theme: ${label[mode]}. Activate to switch.`}
      style={{
        font: "inherit",
        fontSize: "0.8125rem",
        color: "var(--ink-2)",
        background: "var(--surface)",
        border: "1px solid var(--rule)",
        borderRadius: 5,
        padding: "0.28rem 0.6rem",
        cursor: "pointer",
        transition: "background 160ms var(--ease), border-color 160ms var(--ease)",
      }}
    >
      {label[mode]}
    </button>
  );
}
