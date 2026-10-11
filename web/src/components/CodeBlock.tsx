// THE component that renders a param/code value in a panel. The synchronous
// first paint is the LEGACY rendering — exactly today's output, including the
// `${ref}` marks when `highlightRef` is set (several EdgePanel tests pin that
// synchronous presence). Shiki's hast only ever SWAPS IN later: highlighting is
// strictly an upgrade, never a downgrade of marks — and with `highlightRef` set
// the swap is GATED on the highlighted tree landing exactly as many marks as the
// plain text carries (a `${ref}` the tokenizer split across text nodes would
// otherwise un-mark the one thing this panel exists to point at). No spinner, no
// Suspense — plain state + effect, like the rest of the app.

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { toJsxRuntime } from "hast-util-to-jsx-runtime";
import { Fragment, jsx, jsxs } from "react/jsx-runtime";
import type { ElementContent } from "hast";

import type { ParamMode } from "../types";
import { fullValue, parseTemplate, refMatchesHighlight } from "../utils/format";
import { codeChildren, highlight, markRefs } from "../utils/highlight";

export function CodeBlock({
  code,
  lang,
  mode,
  highlightRef,
  expandLabel,
  modalBody,
}: {
  // The value shown: text as is; a param's dict/list value as `fullValue`'s JSON, its
  // `${…}` read per string leaf (`parseTemplate`).
  code: unknown;
  lang: string | null;
  // The param's mode when `code` is a param's value (which `${…}` are pflow's —
  // `templateTokens`); absent for any other text, read as a Template.
  mode?: ParamMode;
  highlightRef?: string;
  // The ⛶ expand-to-modal title. Every value box carries the expand by default
  // (the 320px scroll cap keeps panels skimmable; long values are READ in the
  // full-screen overlay) — undefined falls back to "value". Pass null to
  // DISABLE it: the modal's own inner CodeBlock (the recursion guard) and any
  // surface where a full-screen read makes no sense.
  expandLabel?: string | null;
  // Custom modal content — the modal is a READING surface, and a caller that
  // still holds the structured value can render it more readably than this
  // component's stringified `code` (RunValue's per-field document for dicts).
  // Absent → the modal shows the same code, un-capped.
  modalBody?: JSX.Element;
}): JSX.Element {
  // Markdown (prompts, cached prefix) and plain values teal ALL their refs — the
  // canvas-language treatment the source pane uses. Code/shell/yaml/json values do
  // NOT (shiki owns them; a bash variable is not a pflow ref), exactly as the
  // source pane leaves those fences to their grammar.
  const tealRefs = lang === "markdown" || lang === null;
  const text = fullValue(code);
  const segments = parseTemplate(code, mode);
  // The count rule's target: the marks the plain paint carries.
  const expectedMarks = highlightRef ? segments.filter((s) => refMatchesHighlight(s, highlightRef)).length : 0;

  // The highlighted tree is keyed by its inputs: a re-render with new props must
  // never paint a stale highlight of the OLD value while the effect catches up.
  const key = `${lang ?? ""}\u0000${mode ?? ""}\u0000${highlightRef ?? ""}\u0000${text}`;
  const [highlighted, setHighlighted] = useState<{ key: string; nodes: ElementContent[] } | null>(null);
  const nodes = highlighted?.key === key ? highlighted.nodes : null;

  useEffect(() => {
    if (!lang) return;
    let cancelled = false;
    void highlight(text, lang).then((root) => {
      if (cancelled || !root) return;
      // The count rule (highlightRef only): swap only when every plain-text mark
      // landed in the hast. tealRest decoration is best-effort and never gates.
      const landed = markRefs(root, highlightRef, { tealRest: tealRefs, mode });
      if (highlightRef && landed !== expectedMarks) return;
      const children = codeChildren(root);
      if (children) setHighlighted({ key, nodes: children });
    });
    return () => {
      cancelled = true;
    };
  }, [text, lang, mode, highlightRef, key, tealRefs, expectedMarks]);

  // ONE <pre> — when the hast lands, the <code>'s children render inside OUR
  // container so the box recipe (pre-wrap, scroll cap) keeps governing; shiki's
  // own <pre> would nest UA `white-space: pre` and bring back horizontal
  // scrollbars.
  const pre = nodes ? (
    <pre className="read-param-value shiki-host">
      {toJsxRuntime({ type: "root", children: nodes }, { Fragment, jsx, jsxs })}
    </pre>
  ) : (
    <pre className="read-param-value">
      {highlightRef != null || tealRefs
        ? segments.map((seg, i) => {
            if (!seg.isRef) return seg.text;
            const t = `\${${seg.text}}`;
            if (highlightRef != null && refMatchesHighlight(seg, highlightRef)) {
              return (
                <mark className="ref-mark" key={i}>
                  {t}
                </mark>
              );
            }
            return tealRefs ? (
              <span className="src-ref" key={i}>
                {t}
              </span>
            ) : (
              t
            );
          })
        : text}
    </pre>
  );

  // An empty value gets no expand — a full-screen read of nothing is noise.
  if (expandLabel === null || text === "") return pre;
  return (
    <ExpandableBox
      pre={pre}
      code={code}
      lang={lang}
      mode={mode}
      highlightRef={highlightRef}
      label={expandLabel ?? "value"}
      modalBody={modalBody}
    />
  );
}

// The ⛶ expand affordance every panel value box carries: the box stays
// scroll-capped; the modal shows the SAME content un-capped, full-screen.
function ExpandableBox({
  pre,
  code,
  lang,
  mode,
  highlightRef,
  label,
  modalBody,
}: {
  pre: JSX.Element;
  code: unknown;
  lang: string | null;
  mode?: ParamMode;
  highlightRef?: string;
  label: string;
  modalBody?: JSX.Element;
}): JSX.Element {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="code-box">
      {pre}
      <button
        className="value-expand"
        title="Expand"
        aria-label={`Expand ${label}`}
        onClick={() => setExpanded(true)}
      >
        ⛶
      </button>
      {expanded && (
        <ValueModal
          code={code}
          lang={lang}
          mode={mode}
          highlightRef={highlightRef}
          label={label}
          modalBody={modalBody}
          onClose={() => setExpanded(false)}
        />
      )}
    </div>
  );
}

// The full-screen reading overlay. Portaled to <body> so no panel overflow or
// stacking context clips it; `.value-modal-overlay` is in index.css's scoped
// chrome-token list (portals escape the .read-panel scope, so the tokens must
// be re-declared on it). Esc / backdrop / × close.
function ValueModal({
  code,
  lang,
  mode,
  highlightRef,
  label,
  modalBody,
  onClose,
}: {
  code: unknown;
  lang: string | null;
  mode?: ParamMode;
  highlightRef?: string;
  label: string;
  modalBody?: JSX.Element;
  onClose: () => void;
}): JSX.Element {
  const closeRef = useRef<HTMLButtonElement>(null);
  // Focus the dialog and lock the page scroll on OPEN; restore both on close.
  // Mount-only ([] deps) — the inline `onClose` gets a fresh identity every
  // render, so merging this into the Esc effect below would re-steal focus each
  // render and capture the close button itself as the restore target.
  useEffect(() => {
    const returnFocus = document.activeElement as HTMLElement | null;
    const bodyOverflow = document.body.style.overflow;
    closeRef.current?.focus();
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = bodyOverflow;
      returnFocus?.focus?.();
    };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return createPortal(
    // Backdrop click closes; a click INSIDE the dialog bubbles up to the
    // overlay, so guard on the event landing on the overlay itself.
    <div
      className="value-modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="value-modal" role="dialog" aria-modal="true" aria-label={label}>
        <header className="value-modal-head">
          <span className="value-modal-title">{label}</span>
          <button ref={closeRef} className="value-modal-close" aria-label="Close" onClick={onClose}>
            ✕
          </button>
        </header>
        <div className="value-modal-body">
          {modalBody ?? <CodeBlock code={code} lang={lang} mode={mode} highlightRef={highlightRef} expandLabel={null} />}
        </div>
      </div>
    </div>,
    document.body,
  );
}
