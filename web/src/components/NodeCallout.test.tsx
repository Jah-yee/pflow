// @vitest-environment jsdom
// NodeCallout's placement wiring (#822): the card reads React Flow's LIVE viewport + pane size and its own
// measured size, and takes the first side with room (calloutPlacement.ts owns the geometry and its table).
// jsdom lays nothing out, so the pane's and the card's offset sizes are stubbed to the #822 measurements.

import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render } from "@testing-library/react";
import { ReactFlow, ReactFlowProvider, useReactFlow, type Node, type ReactFlowInstance } from "@xyflow/react";

// Observe the frame-on-mount camera call; everything else is the real instance.
const setCenterSpy = vi.hoisted(() => vi.fn());
vi.mock("@xyflow/react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@xyflow/react")>();
  return {
    ...actual,
    useReactFlow: (): ReturnType<typeof actual.useReactFlow> => {
      const inst = actual.useReactFlow();
      return { ...inst, setCenter: (...args: Parameters<typeof inst.setCenter>) => (setCenterSpy(...args), inst.setCenter(...args)) };
    },
  };
});

import { installReactFlowJsdomMocks } from "../test/rf-jsdom";
import type { Direction } from "../graph/flow";
import { NodeCallout } from "./NodeCallout";

// A 320×160 step card, framed the way `pflow ui focus` frames it: centred in the pane at zoom 1.2.
const ANCHOR: Node = { id: "a", position: { x: 0, y: 0 }, data: { label: "summarize" }, measured: { width: 320, height: 160 } };
const PANE_H = 853;
const CAPTION_H = 127; // a caption-only say box, 320 wide
const card = { w: 320, h: CAPTION_H };

let paneW = 0;
const offset = (dim: "w" | "h") =>
  function (this: HTMLElement): number {
    // React Flow sizes its pane from `.react-flow__renderer` (useResizeHandler's zoom-pane ref).
    if (this.classList.contains("react-flow__renderer")) return dim === "w" ? paneW : PANE_H;
    if (this.classList.contains("node-callout")) return card[dim];
    return 0;
  };

const jsdomOffsets = {
  offsetWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth")!,
  offsetHeight: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight")!,
};
// rf-jsdom's ResizeObserver never fires; this one fires on demand, so a test can resize the pane (React
// Flow's own observer re-reads it) and the card (NodeCallout's observer re-measures it) after mount.
let observed: Array<() => void> = [];
class FireableResizeObserver {
  private readonly fire: () => void;
  constructor(callback: ResizeObserverCallback) {
    this.fire = () => callback([], this as unknown as ResizeObserver);
  }
  observe(): void {
    observed.push(this.fire);
  }
  unobserve(): void {}
  disconnect(): void {
    observed = observed.filter((fire) => fire !== this.fire);
  }
}
const fireResize = (): void => act(() => observed.forEach((fire) => fire()));

beforeAll(() => {
  installReactFlowJsdomMocks();
  Object.assign(globalThis, { ResizeObserver: FireableResizeObserver });
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", { configurable: true, get: offset("w") });
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", { configurable: true, get: offset("h") });
});
afterAll(() => {
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", jsdomOffsets.offsetWidth);
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", jsdomOffsets.offsetHeight);
});
beforeEach(() => {
  setCenterSpy.mockClear();
  observed = []; // drop the previous test's (unmounted) observers
  card.h = CAPTION_H;
});
afterEach(cleanup);

const centredAt = (pane: number, zoom = 1.2) => ({ x: pane / 2 - 160 * zoom, y: PANE_H / 2 - 80 * zoom, zoom });

const mount = (
  pane: number,
  direction: Direction,
  { frameOnMount = false, viewport = centredAt(pane) } = {},
): { box: () => HTMLElement; flow: () => ReactFlowInstance } => {
  paneW = pane;
  let flow: ReactFlowInstance | null = null;
  const Grab = (): null => {
    flow = useReactFlow();
    return null;
  };
  const { container } = render(
    <ReactFlowProvider>
      <ReactFlow nodes={[ANCHOR]} edges={[]} defaultViewport={viewport}>
        <Grab />
        <NodeCallout anchorId="a" direction={direction} title="Agent" frameOnMount={frameOnMount} onClose={() => {}}>
          <p>This is the workflow: five steps that turn a folder into a report.</p>
        </NodeCallout>
      </ReactFlow>
    </ReactFlowProvider>,
  );
  return { box: () => container.querySelector<HTMLElement>(".node-callout")!, flow: () => flow! };
};
const renderCallout = (pane: number, direction: Direction, frameOnMount = false): HTMLElement =>
  mount(pane, direction, { frameOnMount }).box();

describe("NodeCallout placement (#822)", () => {
  it("a TD caption in a canvas narrowed by the docked panel goes above its anchor, not off the left edge", () => {
    const box = renderCallout(740, "TD"); // window 1200 − 460 px panel

    expect(box.dataset.side).toBe("above");
    // Flow units: the anchor's column, one GAP (28) above its top, at the card's MEASURED height.
    expect(box.style.left).toBe("0px");
    expect(box.style.top).toBe(`${-28 - CAPTION_H}px`);
  });

  it("a TD caption with room on the left keeps the left side", () => {
    const box = renderCallout(1360, "TD"); // window 1820 − 460

    expect(box.dataset.side).toBe("left");
    expect(box.style.left).toBe(`${-28 - card.w}px`);
    expect(box.style.top).toBe("0px");
  });

  it.each([
    // The preferred side's nominal 320×280 box ∪ the anchor, centred — the frame the run/gate callouts had.
    { direction: "TD" as const, center: [(-348 + 320) / 2, 280 / 2] },
    { direction: "LR" as const, center: [320 / 2, (-308 + 160) / 2] },
  ])("frame-on-mount still frames anchor ∪ its $direction preferred side, once", ({ direction, center }) => {
    renderCallout(1360, direction, true);

    expect(setCenterSpy).toHaveBeenCalledTimes(1);
    expect(setCenterSpy).toHaveBeenCalledWith(center[0], center[1], { zoom: 1.1, duration: 400 });
  });

  it("the mounted card re-picks its side as the camera moves", () => {
    const { box, flow } = mount(1360, "TD");
    const card0 = box();
    expect(card0.dataset.side).toBe("left");

    // Pan so the anchor sits 40 px from the pane's left edge — no room for the card on its left.
    act(() => void flow().setViewport({ x: 40, y: centredAt(1360).y, zoom: 1.2 }));

    expect(box()).toBe(card0); // the same box, moved — not a remount
    expect(card0.dataset.side).toBe("right");
    expect(card0.style.left).toBe(`${320 + 28}px`);
  });

  it("the mounted card re-picks its side when the pane narrows (a panel docks)", () => {
    // Anchor at pane x 40: the card sits on the RIGHT, ending at screen x ~842.
    const { box } = mount(1360, "TD", { viewport: { x: 40, y: centredAt(1360).y, zoom: 1.2 } });
    expect(box().dataset.side).toBe("right");

    paneW = 800; // the details panel docks; React Flow's observer re-reads the pane
    fireResize();

    expect(box().dataset.side).toBe("above");
  });

  it("the mounted card re-places itself when its content grows (a longer caption on the same anchor)", () => {
    const { box } = mount(1360, "LR");
    expect(box().style.top).toBe(`${-28 - CAPTION_H}px`);

    card.h = 200; // the box grows; NodeCallout's observer re-measures it
    fireResize();

    expect(box().dataset.side).toBe("above");
    expect(box().style.top).toBe(`${-28 - 200}px`); // its bottom stays one GAP above the anchor
  });
});
