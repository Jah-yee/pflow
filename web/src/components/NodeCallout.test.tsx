// @vitest-environment jsdom
// NodeCallout's placement wiring (#822): the card reads React Flow's LIVE viewport + pane size and its own
// measured size, and takes the first side with room (calloutPlacement.ts owns the geometry and its table).
// jsdom lays nothing out, so the pane's and the card's offset sizes are stubbed to the #822 measurements.

import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { ReactFlow, ReactFlowProvider, type Node } from "@xyflow/react";

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
const CARD = { w: 320, h: 127 }; // a caption-only say box

let paneW = 0;
const offset = (dim: "w" | "h") =>
  function (this: HTMLElement): number {
    if (this.classList.contains("react-flow")) return dim === "w" ? paneW : PANE_H;
    if (this.classList.contains("node-callout")) return CARD[dim];
    return 0;
  };

const jsdomOffsets = {
  offsetWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth")!,
  offsetHeight: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight")!,
};
beforeAll(() => {
  installReactFlowJsdomMocks();
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", { configurable: true, get: offset("w") });
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", { configurable: true, get: offset("h") });
});
afterAll(() => {
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", jsdomOffsets.offsetWidth);
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", jsdomOffsets.offsetHeight);
});
beforeEach(() => setCenterSpy.mockClear());
afterEach(cleanup);

const renderCallout = (pane: number, direction: Direction, frameOnMount = false): HTMLElement => {
  paneW = pane;
  const zoom = 1.2;
  const viewport = { x: pane / 2 - 160 * zoom, y: PANE_H / 2 - 80 * zoom, zoom };
  const { container } = render(
    <ReactFlowProvider>
      <div style={{ width: pane, height: PANE_H }}>
        <ReactFlow nodes={[ANCHOR]} edges={[]} defaultViewport={viewport}>
          <NodeCallout anchorId="a" direction={direction} title="Agent" frameOnMount={frameOnMount} onClose={() => {}}>
            <p>This is the workflow: five steps that turn a folder into a report.</p>
          </NodeCallout>
        </ReactFlow>
      </div>
    </ReactFlowProvider>,
  );
  return container.querySelector<HTMLElement>(".node-callout")!;
};

describe("NodeCallout placement (#822)", () => {
  it("a TD caption in a canvas narrowed by the docked panel goes above its anchor, not off the left edge", () => {
    const box = renderCallout(740, "TD"); // window 1200 − 460 px panel

    expect(box.dataset.side).toBe("above");
    // Flow units: the anchor's column, one GAP (28) above its top, at the card's MEASURED height.
    expect(box.style.left).toBe("0px");
    expect(box.style.top).toBe(`${-28 - CARD.h}px`);
  });

  it("a TD caption with room on the left keeps the left side", () => {
    const box = renderCallout(1360, "TD"); // window 1820 − 460

    expect(box.dataset.side).toBe("left");
    expect(box.style.left).toBe(`${-28 - CARD.w}px`);
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
});
