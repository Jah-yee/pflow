// A floating callout anchored to a canvas node, in FLOW-space (it pans/zooms WITH the canvas, like a
// node) via ViewportPortal — NOT a side panel and NOT a store node (so it never perturbs the
// contract-driven ELK layout). Placed beside the anchor on the first side with room in the visible canvas
// (calloutPlacement.ts — off the spine first: TD → left, LR → above, mirroring the spine-avoiding Tines
// layout). On show it frames the camera over anchor ∪ callout.
//
// THE REUSABLE PRIMITIVE (Task 175 + 174): the run-progress stream drops in as children now; Task 174's
// agent "say" bubble reuses the same shell (anchor a styled box to any node) but passes
// frameOnMount={false} — the point message that precedes a say already owns the camera. Content-
// agnostic by design — it owns anchoring + chrome + (optional) framing, never what's inside.

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useReactFlow, useStore, ViewportPortal } from "@xyflow/react";

import type { Direction } from "../graph/flow";
import { frameBox, placeCallout, type Size } from "./calloutPlacement";

// Nominal callout size in FLOW units — frames the camera generously (over-framing slightly is fine,
// clipping the callout is not) and stands in for the card's size until the box is measured.
const NOMINAL: Size = { w: 320, h: 280 };

export function NodeCallout({
  anchorId,
  direction,
  icon,
  title,
  subtitle,
  frameOnMount = true,
  onClose,
  className,
  children,
}: {
  anchorId: string;
  direction: Direction;
  // An optional extra class on the outer box — the shell stays content-agnostic, but a caller can
  // add a state modifier (Task 174's say bubble adds `say-playing` while its clip is speaking).
  className?: string;
  // An optional leading header element (rendered before the title) — the run callout passes the pflow
  // chevrons; the shell stays content-agnostic, so Task 174's "say" bubble can pass its own mark or none.
  icon?: ReactNode;
  title: string;
  // An optional muted header slot between the title and the ✕ (the run callout puts the run id here;
  // Task 174's "say" bubble can use it for a label). Absent → just title + ✕.
  subtitle?: ReactNode;
  // Whether opening this callout frames the camera over anchor ∪ callout (the one-shot effect below).
  // Default true (the run callout's behavior); the say bubble passes false — its point message owns
  // the camera.
  frameOnMount?: boolean;
  onClose: () => void;
  children: ReactNode;
}): JSX.Element | null {
  const { getInternalNode, setCenter } = useReactFlow();
  // Placement reads the live viewport + pane size, so the card re-picks its side as the camera moves.
  const [viewX, viewY, zoom] = useStore((s) => s.transform);
  const paneW = useStore((s) => s.width);
  const paneH = useStore((s) => s.height);
  const anchor = getInternalNode(anchorId);
  // Flow-space rect of the anchor. RF re-measures EVERY node on a beautiful-mode expansion re-layout (any
  // node click), during which the anchor's `measured` transiently goes undefined — dropping to null then
  // would unmount/remount the box (a flicker, user-caught). Cache the last good rect and render at it
  // through the transient; only the very first render (before any measure) has no rect.
  const liveRect =
    anchor && anchor.measured.width != null
      ? {
          x: anchor.internals.positionAbsolute.x,
          y: anchor.internals.positionAbsolute.y,
          w: anchor.measured.width,
          h: anchor.measured.height ?? 0,
        }
      : null;
  const lastRectRef = useRef(liveRect);
  if (liveRect) lastRectRef.current = liveRect;
  const rect = liveRect ?? lastRectRef.current;
  const ready = rect != null;

  // The card's real size (CSS px = flow units; offset sizes ignore the viewport's scale). Measured before
  // paint and on every resize — a say box's caption or the run list changes its height.
  const boxRef = useRef<HTMLDivElement>(null);
  const [cardSize, setCardSize] = useState<Size>(NOMINAL);
  useLayoutEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const measure = (): void => {
      const w = el.offsetWidth;
      const h = el.offsetHeight;
      if (w > 0 && h > 0) setCardSize((prev) => (prev.w === w && prev.h === h ? prev : { w, h }));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [ready]);

  // Frame anchor ∪ callout EXACTLY ONCE, on the first measured render after this callout opens — a strict
  // one-shot. It must NOT re-fire on later churn: selecting/deselecting a node (beautiful-mode expansion)
  // re-layouts the canvas, which re-measures every node and transiently flips `ready`; a reactive frame
  // would then yank the camera back to the callout on every click. The ref makes it fire once per mount;
  // a NEW launch remounts the callout (runCalloutOpen false→true) and re-arms it.
  const framedRef = useRef(false);
  useEffect(() => {
    if (!frameOnMount || framedRef.current || !rect) return;
    framedRef.current = true;
    const bounds = frameBox(rect, NOMINAL, direction);
    // Center the anchor ∪ callout region at a FIXED, modest zoom rather than fitBounds (which over-zooms a
    // small region, blowing the compact box up to fill the screen). A predictable zoom keeps the box small
    // and leaves the rest of the canvas in view. Synchronous one-shot (framedRef) — on a `?run=` deep-link
    // load the competing whole-graph mount-fit is suppressed (GraphView passes suppressInitialFit), so this
    // is uncontested; the interactive-pin / launch cases never had a competing fit.
    void setCenter(bounds.x + bounds.w / 2, bounds.y + bounds.h / 2, { zoom: 1.1, duration: 400 });
    // One-shot: read rect/direction/setCenter at fire time; `ready` only re-arms the first-measure case.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  if (!rect) return null;

  const { side, box } = placeCallout(rect, cardSize, direction, { x: viewX, y: viewY, zoom }, { w: paneW, h: paneH });

  return (
    <ViewportPortal>
      {/* `nopan`/`nodrag`: the callout lives inside the RF viewport, whose d3-drag pan handler would
          otherwise swallow the pointer (the ✕ and the step buttons wouldn't click). `nowheel` lets the
          body scroll without zooming the canvas. */}
      <div
        ref={boxRef}
        className={`node-callout nopan nodrag nowheel${className ? ` ${className}` : ""}`}
        data-side={side}
        style={{ position: "absolute", left: box.x, top: box.y }}
      >
        <div className="node-callout-head">
          {icon != null ? <span className="node-callout-lead">{icon}</span> : null}
          <span className="node-callout-title">{title}</span>
          {subtitle != null ? <span className="node-callout-subtitle">{subtitle}</span> : null}
          <button className="node-callout-close" onClick={onClose} aria-label="Close" title="Close">
            ✕
          </button>
        </div>
        <div className="node-callout-body">{children}</div>
      </div>
    </ViewportPortal>
  );
}
