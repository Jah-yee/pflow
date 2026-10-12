import { describe, expect, it } from "vitest";

import { CALLOUT_GAP, besideAnchor, placeCallout, type Box, type Size } from "./calloutPlacement";

// The #822 geometry, measured in a real Viewer: a 5-step TD workflow whose step card is 320×160 flow
// units, framed by `pflow ui focus` (fitView, maxZoom 1.2 → the anchor centred in the pane at zoom 1.2),
// with a caption-only say box 320×127. The pane is the canvas minus the docked 460 px details panel.
const ANCHOR: Box = { x: 0, y: 0, w: 320, h: 160 };
const CAPTION: Size = { w: 320, h: 127 };
const ZOOM = 1.2;

/** The viewport fitView leaves after framing ANCHOR alone: centred in the pane at ZOOM. */
const centred = (pane: Size, zoom = ZOOM) => ({
  x: pane.w / 2 - ((ANCHOR.x + ANCHOR.w / 2) * zoom),
  y: pane.h / 2 - ((ANCHOR.y + ANCHOR.h / 2) * zoom),
  zoom,
});

/** The card's screen rect (pane px) for a flow box under a viewport. */
const onScreen = (box: Box, v: { x: number; y: number; zoom: number }) => ({
  left: box.x * v.zoom + v.x,
  top: box.y * v.zoom + v.y,
  right: (box.x + box.w) * v.zoom + v.x,
  bottom: (box.y + box.h) * v.zoom + v.y,
});

const insidePane = (box: Box, v: { x: number; y: number; zoom: number }, pane: Size): boolean => {
  const r = onScreen(box, v);
  return r.left >= 0 && r.top >= 0 && r.right <= pane.w && r.bottom <= pane.h;
};

describe("placeCallout — the #822 table (TD, details panel docked, pane height 853)", () => {
  // Window width → pane width (window − 460 panel). Before the fix the caption sat LEFT of the anchor at
  // every width: −240 / −140 px past the pane's left edge at 1200 / 1400 — the first words unreadable.
  it.each([
    { window: 1200, pane: 740 },
    { window: 1400, pane: 940 },
  ])("window $window: neither side has room, so the caption goes above — wholly visible", ({ pane: w }) => {
    const pane = { w, h: 853 };
    const v = centred(pane);
    expect(onScreen(besideAnchor(ANCHOR, CAPTION, "left"), v).left).toBeLessThan(0); // the defect

    const { side, box } = placeCallout(ANCHOR, CAPTION, "TD", v, pane);

    expect(side).toBe("above");
    expect(insidePane(box, v, pane)).toBe(true);
    expect(box).toEqual({ x: 0, y: -CALLOUT_GAP - CAPTION.h, ...CAPTION }); // the anchor's own column
  });

  it("window 1820: the left side has room, so the caption keeps its direction's side", () => {
    const pane = { w: 1360, h: 853 };
    const v = centred(pane);

    const { side, box } = placeCallout(ANCHOR, CAPTION, "TD", v, pane);

    expect(side).toBe("left");
    expect(box).toEqual(besideAnchor(ANCHOR, CAPTION, "left"));
    expect(onScreen(box, v).left).toBeCloseTo(70.4); // the measured +70 px
  });

  it("takes the mirror side before going upstream: anchor near the left edge → right", () => {
    const pane = { w: 1000, h: 853 };
    const v = { x: 40, y: 300, zoom: ZOOM }; // anchor at screen x 40..424 — no room on its left

    const { side, box } = placeCallout(ANCHOR, CAPTION, "TD", v, pane);

    expect(side).toBe("right");
    expect(insidePane(box, v, pane)).toBe(true);
  });
});

describe("placeCallout — LR", () => {
  it("keeps the card above when there is room", () => {
    const pane = { w: 740, h: 853 };
    const v = centred(pane);
    expect(placeCallout(ANCHOR, CAPTION, "LR", v, pane)).toEqual({
      side: "above",
      box: besideAnchor(ANCHOR, CAPTION, "above"),
    });
  });

  it("drops below when the anchor sits near the top edge", () => {
    const pane = { w: 740, h: 853 };
    const v = { x: 100, y: 30, zoom: ZOOM }; // anchor top at screen y 30 — no room above

    const { side, box } = placeCallout(ANCHOR, CAPTION, "LR", v, pane);

    expect(side).toBe("below");
    expect(insidePane(box, v, pane)).toBe(true);
  });

  it("a short canvas with room nowhere: the card is pushed into view, over the anchor's near edge only", () => {
    // Window 1200×560 with the panel docked (pane 740×513): measured before the fix, the caption ran 25 px
    // past the pane's top edge — above has 160 px, below 160 px, the card needs 186.
    const pane = { w: 740, h: 513 };
    const v = centred(pane);

    const { side, box } = placeCallout(ANCHOR, CAPTION, "LR", v, pane);

    expect(side).toBe("above");
    expect(insidePane(box, v, pane)).toBe(true);
    // It overlaps the anchor by the few px the canvas lacks, nowhere near covering it.
    const overlap = box.y + box.h - ANCHOR.y;
    expect(overlap).toBeGreaterThan(0);
    expect(overlap).toBeLessThan(10);
  });
});

describe("placeCallout — the card stays beside its anchor", () => {
  it("slides along the anchor edge to clear the pane's bottom, never off the anchor's span", () => {
    const tall: Size = { w: 320, h: 260 };
    const pane = { w: 1400, h: 700 };
    // Anchor at screen y 420..612; a top-aligned 312 px card would end at 732 > 688 (pane − margin).
    const v = { x: 700, y: 420, zoom: ZOOM };

    const { side, box } = placeCallout(ANCHOR, tall, "TD", v, pane);

    expect(side).toBe("left");
    expect(insidePane(box, v, pane)).toBe(true);
    expect(box.y).toBeLessThan(ANCHOR.y); // slid up…
    expect(box.y + box.h).toBeGreaterThanOrEqual(ANCHOR.y + ANCHOR.h); // …still spanning the anchor
  });

  it("an anchor panned far off-screen takes its card with it — never pinned to the canvas edge", () => {
    const pane = { w: 740, h: 853 };
    const v = { x: 300, y: 3000, zoom: ZOOM }; // anchor ~3000 px below the pane

    const { box } = placeCallout(ANCHOR, CAPTION, "TD", v, pane);

    expect(box.y + box.h).toBeGreaterThanOrEqual(ANCHOR.y); // touching the anchor's span, off-screen with it
    expect(onScreen(box, v).top).toBeGreaterThan(pane.h);
  });

  it("works at any zoom: the same anchor at zoom 0.5 has room on its preferred side", () => {
    const pane = { w: 740, h: 853 };
    const v = centred(pane, 0.5);
    expect(placeCallout(ANCHOR, CAPTION, "TD", v, pane).side).toBe("left");
  });

  it("an unmeasured pane (0×0 before React Flow sizes it) keeps the preferred side", () => {
    const v = centred({ w: 740, h: 853 });
    for (const [direction, preferred] of [["TD", "left"], ["LR", "above"]] as const) {
      const { side, box } = placeCallout(ANCHOR, CAPTION, direction, v, { w: 0, h: 0 });
      expect(side).toBe(preferred);
      expect(box).toEqual(besideAnchor(ANCHOR, CAPTION, preferred));
    }
  });
});
