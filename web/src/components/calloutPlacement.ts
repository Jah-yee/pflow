// Where a NodeCallout's card sits: beside its anchor node, on the first side that keeps the whole card
// inside the visible canvas (#822 — placing by flow direction alone clipped a TD caption at the canvas
// edge whenever the details panel narrowed the canvas). Pure geometry in FLOW units, so it is tested
// without React Flow; the caller passes RF's live viewport transform and pane size.

import type { Direction } from "../graph/flow";

export type CalloutSide = "left" | "right" | "above" | "below";

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Size {
  w: number;
  h: number;
}

/** React Flow's viewport transform: screen = flow × zoom + (x, y), relative to the pane. */
export interface Viewport {
  x: number;
  y: number;
  zoom: number;
}

/** Flow units between the anchor and the card. */
export const CALLOUT_GAP = 28;
/** Screen px kept clear between the card and the pane edge. */
const EDGE_MARGIN = 12;
// Float slack for the fit test and the most-visible tie-break (ties keep the earlier side).
const EPSILON = 1e-6;

// Off the spine first — the direction's own side, then its mirror — then upstream along the spine (the
// card covers the previous step there, never its own anchor).
const SIDES: Record<Direction, readonly CalloutSide[]> = {
  TD: ["left", "right", "above"],
  LR: ["above", "below", "left"],
};

/** Anchor ∪ the card on its direction's own side — what a frame-on-mount centres the camera on, so the
 *  card fits there whenever the canvas is wide enough. */
export function frameBox(anchor: Box, card: Size, direction: Direction): Box {
  const box = besideAnchor(anchor, card, SIDES[direction][0]!);
  const x = Math.min(anchor.x, box.x);
  const y = Math.min(anchor.y, box.y);
  return { x, y, w: Math.max(anchor.x + anchor.w, box.x + box.w) - x, h: Math.max(anchor.y + anchor.h, box.y + box.h) - y };
}

/** The card's box on one side of the anchor, a GAP away, aligned to the anchor's top / left edge. */
export function besideAnchor(anchor: Box, card: Size, side: CalloutSide): Box {
  switch (side) {
    case "left":
      return { x: anchor.x - CALLOUT_GAP - card.w, y: anchor.y, ...card };
    case "right":
      return { x: anchor.x + anchor.w + CALLOUT_GAP, y: anchor.y, ...card };
    case "above":
      return { x: anchor.x, y: anchor.y - CALLOUT_GAP - card.h, ...card };
    case "below":
      return { x: anchor.x, y: anchor.y + anchor.h + CALLOUT_GAP, ...card };
  }
}

/**
 * The first side (in the direction's order) whose card fits wholly inside the visible pane, slid along
 * the anchor's edge as far as it still overlaps the anchor. When no side fits (a cramped canvas), the side
 * showing the most of the card, pushed into view — over the anchor's near edge if it must, but never past
 * the anchor, so a card whose anchor is panned away leaves with it. An unmeasured pane (RF reports 0
 * before it sizes its container) keeps the preferred side.
 */
export function placeCallout(
  anchor: Box,
  card: Size,
  direction: Direction,
  viewport: Viewport,
  pane: Size,
): { side: CalloutSide; box: Box } {
  const sides = SIDES[direction];
  if (pane.w <= 0 || pane.h <= 0) return { side: sides[0]!, box: besideAnchor(anchor, card, sides[0]!) };
  const visible: Box = {
    x: (EDGE_MARGIN - viewport.x) / viewport.zoom,
    y: (EDGE_MARGIN - viewport.y) / viewport.zoom,
    w: (pane.w - 2 * EDGE_MARGIN) / viewport.zoom,
    h: (pane.h - 2 * EDGE_MARGIN) / viewport.zoom,
  };
  let best: { side: CalloutSide; box: Box } | null = null;
  let bestArea = -1;
  for (const side of sides) {
    const box = slideAlongAnchor(besideAnchor(anchor, card, side), anchor, side, visible);
    if (contains(visible, box)) return { side, box };
    const area = overlapArea(box, visible);
    if (area > bestArea + EPSILON) {
      best = { side, box };
      bestArea = area;
    }
  }
  return { side: best!.side, box: slideOverAnchor(best!.box, anchor, best!.side, visible) };
}

// Move `pos` (a card edge on one axis) toward the visible span, but only within [a, b] — the card's
// leash to its anchor. A card larger than the view shows its start (the title row / first words).
function slide(pos: number, size: number, visPos: number, visSize: number, a: number, b: number): number {
  const inView = Math.max(visPos, Math.min(pos, visPos + visSize - size));
  return Math.min(Math.max(inView, Math.min(a, b)), Math.max(a, b));
}

// Along the anchor edge the card sits on (vertically beside a left/right card, horizontally for
// above/below), as far as its span still overlaps the anchor's — so while any of the anchor is on screen
// the card sits beside that visible part, and an anchor straddling the pane edge never clips its card.
function slideAlongAnchor(box: Box, anchor: Box, side: CalloutSide, visible: Box): Box {
  return side === "left" || side === "right"
    ? { ...box, y: slide(box.y, box.h, visible.y, visible.h, anchor.y - box.h, anchor.y + anchor.h) }
    : { ...box, x: slide(box.x, box.w, visible.x, visible.w, anchor.x - box.w, anchor.x + anchor.w) };
}

// Toward the anchor, from its beside position up to flush with the anchor's FAR edge (covering it).
function slideOverAnchor(box: Box, anchor: Box, side: CalloutSide, visible: Box): Box {
  switch (side) {
    case "left":
      return { ...box, x: slide(box.x, box.w, visible.x, visible.w, box.x, anchor.x + anchor.w - box.w) };
    case "right":
      return { ...box, x: slide(box.x, box.w, visible.x, visible.w, box.x, anchor.x) };
    case "above":
      return { ...box, y: slide(box.y, box.h, visible.y, visible.h, box.y, anchor.y + anchor.h - box.h) };
    case "below":
      return { ...box, y: slide(box.y, box.h, visible.y, visible.h, box.y, anchor.y) };
  }
}


function contains(outer: Box, inner: Box): boolean {
  return (
    inner.x >= outer.x - EPSILON &&
    inner.y >= outer.y - EPSILON &&
    inner.x + inner.w <= outer.x + outer.w + EPSILON &&
    inner.y + inner.h <= outer.y + outer.h + EPSILON
  );
}

function overlapArea(a: Box, b: Box): number {
  const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
  const h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return w > 0 && h > 0 ? w * h : 0;
}
