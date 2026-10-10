// @vitest-environment jsdom
// GateCallout (Task 176): the kind-switched gate panel content. The client seam is mocked
// (RunPanel.test.tsx pattern) with the REAL ApiError, so the refusal-body contract
// (`.body.refusal` + extras) is what these tests exercise, not a fabricated shape.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/client")>()),
  fetchGate: vi.fn(),
  resumeRun: vi.fn(),
}));

import { GateCallout, loopPosition } from "./GateCallout";
import loopPositionCases from "../test/fixtures/loop-position.json";
import { ApiError, fetchGate, resumeRun } from "../api/client";
import type { GateInfo } from "../types";

const APPROVAL: GateInfo = {
  paused_node_id: "deploy",
  gate_kind: "action_approval",
  gate_request: {
    node_id: "deploy",
    node_type: "shell",
    kind: "action_approval",
    // The preview arrives MASKED server-side — the panel renders it verbatim.
    preview: { command: "./deploy.sh --prod", api_key: "<REDACTED>" },
    question: null,
    options: [],
    recommendation: null,
    iteration: null, // a non-loop step — the wire always carries both keys (core/gate.py)
    max_iterations: null,
  },
};

// Task 179: an approval gate raised by a LOOP step at its second iteration; Task 183: with the
// author's cap (`max_iterations: 3`).
const LOOP_APPROVAL: GateInfo = {
  paused_node_id: "gated",
  gate_kind: "action_approval",
  gate_request: {
    node_id: "gated",
    node_type: "code",
    kind: "action_approval",
    preview: { iteration: 2 },
    question: null,
    options: [],
    recommendation: null,
    iteration: 2,
    max_iterations: 3,
  },
};
// The same loop gate with no limit knowable at the pause (uncapped, or a cap the gate can't know).
const UNCAPPED_LOOP_APPROVAL: GateInfo = {
  ...LOOP_APPROVAL,
  gate_request: { ...LOOP_APPROVAL.gate_request, max_iterations: null },
};
// A paused-run record written before Task 183: the key is ABSENT (not null).
const { max_iterations: _dropped, ...oldRecordRequest } = LOOP_APPROVAL.gate_request;
const OLD_RECORD_LOOP_APPROVAL: GateInfo = { ...LOOP_APPROVAL, gate_request: oldRecordRequest };

const ESCALATION: GateInfo = {
  paused_node_id: "triage",
  gate_kind: "decision_escalation",
  gate_request: {
    node_id: "triage",
    node_type: "agent",
    kind: "decision_escalation",
    preview: {},
    question: "Two migration paths are viable — which one?",
    // The second option has no label — the display falls back to `option 2`
    // (the falsy rule mirrored from core/gate.py::option_labels).
    options: [{ label: "Expand-contract", description: "Slower, zero downtime" }, { note: "no label here" }],
    recommendation: "Expand-contract",
  },
};
// An escalation raised inside a capped loop: the position shows, the bulk approval never does
// (`--auto-approve` pre-answers approval gates only).
const LOOP_ESCALATION: GateInfo = {
  ...ESCALATION,
  gate_request: { ...ESCALATION.gate_request, iteration: 2, max_iterations: 3 },
};

// The rendered eyebrow line, read whole: the position lives in its own span, so Testing Library's
// own-text matcher can't see the line — and a regex would pass on any suffix.
const eyebrowText = async (container: HTMLElement): Promise<string | null> => {
  await screen.findByRole("button", { name: /^(Approve|Answer)$/ });
  return container.querySelector(".gate-eyebrow")?.textContent ?? null;
};

afterEach(cleanup);
beforeEach(() => {
  vi.mocked(fetchGate).mockReset();
  vi.mocked(resumeRun).mockReset().mockResolvedValue("attempt-2");
});

describe("GateCallout — approval", () => {
  it("renders the node header + masked preview rows and submits Approve / Deny as {run, approve}", async () => {
    vi.mocked(fetchGate).mockResolvedValue(APPROVAL);
    const onPinRun = vi.fn();
    render(<GateCallout run="r1" onPinRun={onPinRun} />);

    await waitFor(() => expect(screen.getByText("Run this step?")).toBeTruthy());
    expect(screen.getByText("shell · deploy")).toBeTruthy();
    expect(screen.getByText("command")).toBeTruthy();
    expect(screen.getByText("./deploy.sh --prod")).toBeTruthy();
    expect(screen.getByText("<REDACTED>")).toBeTruthy(); // masked value shown AS masked

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(resumeRun).toHaveBeenCalledWith({ run: "r1", approve: "yes" }));
    // 200 → the new attempt pins (the parent's selectRun — the single pin path).
    await waitFor(() => expect(onPinRun).toHaveBeenCalledWith("attempt-2"));
  });

  it("the eyebrow names the loop position with the cap — and only what the payload knows (Tasks 179, 183)", async () => {
    // A loop gate pauses at EVERY iteration; the browser's home for "where am I, how far can it
    // go" is the eyebrow — no badge, no colour, the same muted mono line.
    const cases: Array<[GateInfo, string]> = [
      [LOOP_APPROVAL, "code · gated · iteration 2 of up to 3"],
      [UNCAPPED_LOOP_APPROVAL, "code · gated · iteration 2"], // null cap → no clause, never "of up to 100"
      [OLD_RECORD_LOOP_APPROVAL, "code · gated · iteration 2"], // pre-183 record → today's text
      [APPROVAL, "shell · deploy"], // non-loop: ends at the node id
      [LOOP_ESCALATION, "agent · triage · iteration 2 of up to 3"],
    ];
    for (const [info, text] of cases) {
      vi.mocked(fetchGate).mockResolvedValue(info);
      const { container } = render(<GateCallout run="r1" onPinRun={vi.fn()} />);
      expect(await eyebrowText(container)).toBe(text);
      cleanup();
    }
  });

  it("Deny sends approve: 'no' — a clean human no, not a failure", async () => {
    vi.mocked(fetchGate).mockResolvedValue(APPROVAL);
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Deny" }));
    await waitFor(() => expect(resumeRun).toHaveBeenCalledWith({ run: "r1", approve: "no" }));
  });

  it("disables both buttons while the answer is in flight (double-click guard)", async () => {
    vi.mocked(fetchGate).mockResolvedValue(APPROVAL);
    vi.mocked(resumeRun).mockReturnValue(new Promise(() => {})); // never settles
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));
    expect((screen.getByRole("button", { name: "Approve" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Deny" }) as HTMLButtonElement).disabled).toBe(true);
    expect(resumeRun).toHaveBeenCalledTimes(1);
  });
});

// Task 183: "Approve all remaining" — the browser's `--approve yes --auto-approve <paused step>`.
describe("GateCallout — Approve all remaining (loop approval gates)", () => {
  const BULK = "Approve all remaining";
  const footHas = (name: string): boolean =>
    screen.queryAllByRole("button", { name }).some((b) => b.closest(".gate-foot") !== null);

  it("shows on a loop approval gate — capped or not — and never on a non-loop approval or a loop escalation", async () => {
    for (const info of [LOOP_APPROVAL, UNCAPPED_LOOP_APPROVAL, OLD_RECORD_LOOP_APPROVAL]) {
      vi.mocked(fetchGate).mockResolvedValue(info);
      render(<GateCallout run="r1" onPinRun={vi.fn()} />);
      await screen.findByRole("button", { name: "Approve" });
      expect(footHas(BULK)).toBe(true);
      cleanup();
    }
    // Absence twins, each beside the answer control its panel DOES render in the foot (same medium).
    vi.mocked(fetchGate).mockResolvedValue(APPROVAL);
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    await screen.findByRole("button", { name: "Approve" });
    expect(footHas("Approve")).toBe(true);
    expect(screen.queryByRole("button", { name: BULK })).toBeNull();
    cleanup();

    vi.mocked(fetchGate).mockResolvedValue(LOOP_ESCALATION);
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    await screen.findByRole("button", { name: "Answer" });
    expect(footHas("Answer")).toBe(true);
    expect(screen.queryByRole("button", { name: BULK })).toBeNull();
  });

  it("its tooltip states the true scope (by step NAME, sub-workflows included) and the loop's bound", async () => {
    const scope =
      "Approve this and every later approval of a step named 'gated' in this run, including inside sub-workflows.";
    const cases: Array<[GateInfo, string]> = [
      [LOOP_APPROVAL, `${scope} This loop runs at most 3 iterations.`],
      [UNCAPPED_LOOP_APPROVAL, `${scope} No limit is known for this loop — it runs until its condition stops it.`],
      // Past the cap (a back edge re-entered the loop): the eyebrow drops the clause, so does this.
      [
        { ...LOOP_APPROVAL, gate_request: { ...LOOP_APPROVAL.gate_request, iteration: 4 } },
        `${scope} No limit is known for this loop — it runs until its condition stops it.`,
      ],
    ];
    for (const [info, title] of cases) {
      vi.mocked(fetchGate).mockResolvedValue(info);
      render(<GateCallout run="r1" onPinRun={vi.fn()} />);
      expect((await screen.findByRole("button", { name: BULK })).getAttribute("title")).toBe(title);
      cleanup();
    }
  });

  it("a click sends exactly {run, approve: 'yes', auto_approve: true}, disables every answer while in flight, then pins the attempt", async () => {
    let settle: (runId: string) => void = () => {};
    vi.mocked(resumeRun).mockReturnValue(new Promise<string>((resolve) => (settle = resolve)));
    vi.mocked(fetchGate).mockResolvedValue(LOOP_APPROVAL);
    const onPinRun = vi.fn();
    render(<GateCallout run="r1" onPinRun={onPinRun} />);

    fireEvent.click(await screen.findByRole("button", { name: BULK }));
    expect(resumeRun).toHaveBeenCalledTimes(1);
    // toStrictEqual, not toHaveBeenCalledWith: the latter ignores undefined-valued keys.
    expect(vi.mocked(resumeRun).mock.calls[0]![0]).toStrictEqual({ run: "r1", approve: "yes", auto_approve: true });
    for (const name of ["Deny", "Approve", BULK]) {
      expect((screen.getByRole("button", { name }) as HTMLButtonElement).disabled, name).toBe(true);
    }
    fireEvent.click(screen.getByRole("button", { name: BULK }));
    expect(resumeRun).toHaveBeenCalledTimes(1); // the double-click guard holds for the bulk action too

    settle("attempt-2");
    await waitFor(() => expect(onPinRun).toHaveBeenCalledWith("attempt-2"));
  });

  it("plain Approve on the same loop gate still answers ONE iteration — no auto_approve key", async () => {
    vi.mocked(fetchGate).mockResolvedValue(LOOP_APPROVAL);
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    await screen.findByRole("button", { name: BULK }); // both affirmatives are on screen
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(resumeRun).toHaveBeenCalledTimes(1));
    expect(vi.mocked(resumeRun).mock.calls[0]![0]).toStrictEqual({ run: "r1", approve: "yes" });
  });

  it("a stale-workflow ack after a bulk click retries the BULK answer with force", async () => {
    vi.mocked(resumeRun)
      .mockRejectedValueOnce(
        new ApiError(409, [{ title: "Workflow changed since the original run", message: "'gated' was edited." }], {
          refusal: "stale_workflow",
          hash_known: true,
        }),
      )
      .mockResolvedValueOnce("attempt-2");
    vi.mocked(fetchGate).mockResolvedValue(LOOP_APPROVAL);
    const onPinRun = vi.fn();
    render(<GateCallout run="r1" onPinRun={onPinRun} />);

    fireEvent.click(await screen.findByRole("button", { name: BULK }));
    fireEvent.click(await screen.findByRole("button", { name: "Resume anyway" }));
    await waitFor(() => expect(resumeRun).toHaveBeenCalledTimes(2));
    expect(vi.mocked(resumeRun).mock.calls[1]![0]).toStrictEqual({
      run: "r1",
      approve: "yes",
      auto_approve: true,
      force: true,
    });
    await waitFor(() => expect(onPinRun).toHaveBeenCalledWith("attempt-2"));
  });
});

// D8: the eyebrow's TS twin of core/gate.py::loop_position reads the SAME hand-authored table the
// Python test reads — row count and ids first, so an emptied or truncated table cannot pass.
describe("loopPosition — the shared case table (web/src/test/fixtures/loop-position.json)", () => {
  it("renders every row exactly as the Python renderer does", () => {
    const rows = loopPositionCases as Array<{ id: string; gate: Record<string, unknown>; text: string | null }>;
    expect(rows.map((row) => row.id)).toStrictEqual(["capped", "null-cap", "old-record", "non-loop", "empty", "past-cap"]);
    for (const row of rows) {
      expect(loopPosition(row.gate.iteration, row.gate.max_iterations), row.id).toBe(row.text);
    }
  });
});

describe("GateCallout — escalation", () => {
  it("an option click SELECTS — only the Answer button submits, with the option's LABEL (never the number)", async () => {
    // Owner decision 2026-07-12 (after the first real mis-click): an answer consumes the gate
    // token irreversibly, so option cards select and the ONE Answer button is the deliberate
    // submit. An option click alone must never POST.
    vi.mocked(fetchGate).mockResolvedValue(ESCALATION);
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);

    await waitFor(() => expect(screen.getByText("Two migration paths are viable — which one?")).toBeTruthy());
    const option = screen.getByRole("button", { name: /Expand-contract/ });
    fireEvent.click(option);
    expect(resumeRun).not.toHaveBeenCalled(); // select, never fire
    expect(option.getAttribute("aria-pressed")).toBe("true");

    // The button label stays STATIC (owner-preferred one-row layout) — the named answer rides
    // the hover tooltip; the highlighted card is the visible confirmation.
    const answer = screen.getByRole("button", { name: "Answer" });
    expect(answer.getAttribute("title")).toBe("Answer with “Expand-contract”");
    fireEvent.click(answer);
    await waitFor(() => expect(resumeRun).toHaveBeenCalledWith({ run: "r1", choose: "Expand-contract" }));
  });

  it("a label-less option falls back to 'option N' — the shared numbering rule", async () => {
    vi.mocked(fetchGate).mockResolvedValue(ESCALATION);
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: /option 2/ }));
    fireEvent.click(screen.getByRole("button", { name: "Answer" }));
    await waitFor(() => expect(resumeRun).toHaveBeenCalledWith({ run: "r1", choose: "option 2" }));
  });

  it("selection and free text are mutually exclusive: typing clears the selection, selecting clears the text", async () => {
    // One submit at the very end — a successful submit leaves `submitting` latched (the panel
    // unmounts in production), so every interaction must precede it.
    vi.mocked(fetchGate).mockResolvedValue(ESCALATION);
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    const option = await screen.findByRole("button", { name: /Expand-contract/ });
    const input = screen.getByLabelText("Free-text answer") as HTMLInputElement;

    // Type, then select → the text clears, the option is pressed, the tooltip names the label.
    fireEvent.change(input, { target: { value: "scratch that" } });
    fireEvent.click(option);
    expect(input.value).toBe("");
    expect(option.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByRole("button", { name: "Answer" }).getAttribute("title")).toBe(
      "Answer with “Expand-contract”",
    );

    // Select, then type → the selection clears and Answer submits the TEXT.
    fireEvent.change(input, { target: { value: "do both" } });
    expect(option.getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(screen.getByRole("button", { name: "Answer" }));
    await waitFor(() => expect(resumeRun).toHaveBeenCalledWith({ run: "r1", choose: "do both" }));
  });

  it("marks the recommended option instead of repeating the recommendation as text", async () => {
    vi.mocked(fetchGate).mockResolvedValue(ESCALATION);
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    await waitFor(() => expect(screen.getByText("recommended")).toBeTruthy());
    expect(screen.queryByText(/^Recommended:/)).toBeNull();
  });

  it("a non-string question/recommendation renders as text instead of crashing the viewer (#720)", async () => {
    // The shape an unresolved trace blob ref has on the wire. The server resolves these; the panel
    // must still never hand a raw object to React (that throws and blanks the whole viewer).
    const ref = { $pflow_blob: "7fabd35f2de7c0b8a20fa3fc04684300" } as unknown as string;
    vi.mocked(fetchGate).mockResolvedValue({
      ...ESCALATION,
      gate_request: { ...ESCALATION.gate_request, question: ref, recommendation: ref },
    });
    const { container } = render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    await waitFor(() => expect(container.querySelector(".gate-question")?.textContent).toContain("$pflow_blob"));
    expect(container.querySelector(".gate-recommendation")?.textContent).toContain("$pflow_blob");
    expect(screen.getByRole("button", { name: "Answer" })).toBeTruthy(); // the panel stays answerable
  });

  it("free-text answers send the trimmed text; empty/whitespace is blocked client-side", async () => {
    vi.mocked(fetchGate).mockResolvedValue(ESCALATION);
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    const input = (await screen.findByLabelText("Free-text answer")) as HTMLInputElement;
    const answer = screen.getByRole("button", { name: "Answer" }) as HTMLButtonElement;

    expect(answer.disabled).toBe(true); // empty → blocked
    fireEvent.change(input, { target: { value: "   " } });
    expect(answer.disabled).toBe(true); // whitespace → still blocked

    fireEvent.change(input, { target: { value: "  do both, staged  " } });
    expect(answer.disabled).toBe(false);
    fireEvent.click(answer);
    await waitFor(() => expect(resumeRun).toHaveBeenCalledWith({ run: "r1", choose: "do both, staged" }));
  });
});

describe("GateCallout — refusal states (never silence)", () => {
  it("a superseded refusal offers the newer attempt (answered elsewhere, edge ledger #5)", async () => {
    vi.mocked(fetchGate).mockResolvedValue(APPROVAL);
    vi.mocked(resumeRun).mockRejectedValue(
      new ApiError(409, [{ message: "already answered" }], { refusal: "superseded", newer_execution_id: "run-9" }),
    );
    const onPinRun = vi.fn();
    render(<GateCallout run="r1" onPinRun={onPinRun} />);

    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));
    fireEvent.click(await screen.findByRole("button", { name: "View newer attempt" }));
    expect(onPinRun).toHaveBeenCalledWith("run-9");
  });

  it("a stale-workflow refusal shows the server's diagnostic, then retries the SAME answer with force: true", async () => {
    vi.mocked(fetchGate).mockResolvedValue(APPROVAL);
    vi.mocked(resumeRun)
      .mockRejectedValueOnce(
        new ApiError(
          409,
          [
            {
              severity: "error",
              title: "Workflow changed since the original run",
              message:
                "'deploy' was edited after it was approved — the approval covered the earlier version. Resuming " +
                "would run the edited 'deploy' under that earlier approval.",
              suggestions: [
                "Re-run the workflow from the start so 'deploy' asks for approval again.",
                "Pass --force to resume anyway: steps before 'deploy' keep their saved outputs and are not re-run, " +
                  "and the edited 'deploy' runs under the earlier approval.",
              ],
              source: "runtime",
              node_id: "deploy",
              context: {
                category: "execution_failure",
                changed_steps: ["deploy"],
                new_start: null,
                resume_point: "deploy",
                resume_point_missing: false,
              },
            },
          ],
          { refusal: "stale_workflow", hash_known: true },
        ),
      )
      .mockResolvedValueOnce("attempt-2");
    const onPinRun = vi.fn();
    render(<GateCallout run="r1" onPinRun={onPinRun} />);

    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));
    // The ack panel speaks the server's words (#721), not a UI paraphrase.
    expect(await screen.findByText(/'deploy' was edited after it was approved/)).toBeTruthy();
    expect(screen.getByText(/Pass --force to resume anyway: .* the edited 'deploy' runs under the earlier approval/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Resume anyway" }));

    await waitFor(() => expect(resumeRun).toHaveBeenLastCalledWith({ run: "r1", approve: "yes", force: true }));
    await waitFor(() => expect(onPinRun).toHaveBeenCalledWith("attempt-2"));
  });

  it("hash_known=false shows the server's cannot-verify diagnostic (pre-content-hash trace, edge ledger #3)", async () => {
    vi.mocked(fetchGate).mockResolvedValue(APPROVAL);
    vi.mocked(resumeRun).mockRejectedValue(
      new ApiError(
        409,
        [{ message: "Cannot verify the workflow is unchanged — this run predates workflow-hash tracking." }],
        { refusal: "stale_workflow", hash_known: false },
      ),
    );
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));
    expect(await screen.findByText(/predates workflow-hash tracking/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Resume anyway" })).toBeTruthy();
  });

  it("any other refusal renders the server's diagnostics inline (DR-6)", async () => {
    vi.mocked(fetchGate).mockResolvedValue(APPROVAL);
    vi.mocked(resumeRun).mockRejectedValue(
      new ApiError(409, [{ message: "the paused gate needs an answer flag" }], { refusal: "answer_required" }),
    );
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByText(/needs an answer flag/)).toBeTruthy();
    // The panel stays answerable — the buttons are back (submitting reset).
    expect((screen.getByRole("button", { name: "Approve" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("a gate-fetch failure renders inline errors, never a blank panel", async () => {
    vi.mocked(fetchGate).mockRejectedValue(new ApiError(404, [{ message: "run r1 is not paused" }]));
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByText(/not paused/)).toBeTruthy();
  });
});

// #714: whatever answers the gate lives in `.gate-foot`, pinned while the content above it
// scrolls. jsdom computes no layout, so this pins the two halves it CAN see — the DOM split
// (answer controls in the foot, preview/options above it) and the stylesheet's sticky rule;
// the measured "answer row inside the viewport" check is a real-browser screenshot pass.
describe("GateCallout — the answer never scrolls away (#714)", () => {
  const foot = (el: Element): Element | null => el.closest(".gate-foot");

  it("approval: Deny/Approve and their errors sit in the foot; the preview does not", async () => {
    vi.mocked(fetchGate).mockResolvedValue(APPROVAL);
    vi.mocked(resumeRun).mockRejectedValue(
      new ApiError(409, [{ message: "the paused gate needs an answer flag" }], { refusal: "answer_required" }),
    );
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    const approve = await screen.findByRole("button", { name: "Approve" });

    expect(foot(approve)).not.toBeNull();
    expect(foot(screen.getByRole("button", { name: "Deny" }))).not.toBeNull();
    expect(foot(screen.getByText("./deploy.sh --prod"))).toBeNull();

    fireEvent.click(approve);
    expect(foot(await screen.findByRole("alert"))).not.toBeNull();
  });

  it("escalation: the free-text row and Answer sit in the foot; the option cards scroll above it", async () => {
    vi.mocked(fetchGate).mockResolvedValue(ESCALATION);
    render(<GateCallout run="r1" onPinRun={vi.fn()} />);
    const option = await screen.findByRole("button", { name: /Expand-contract/ });

    expect(foot(screen.getByRole("button", { name: "Answer" }))).not.toBeNull();
    expect(foot(screen.getByLabelText("Free-text answer"))).not.toBeNull();
    expect(foot(option)).toBeNull();
  });

  // Read via fs (see cssOrder.test.ts for why not `?raw`); path-joined, because under jsdom
  // the global URL is jsdom's, which node's fileURLToPath rejects.
  const cssRule = (selector: string): string => {
    const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../index.css"), "utf8");
    const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const rule = new RegExp(`(?:^|\\n)${escaped}\\s*\\{([^}]*)\\}`).exec(css.replace(/\/\*[\s\S]*?\*\//g, ""));
    expect(rule, `the ${selector} rule is missing from index.css`).not.toBeNull();
    return rule![1]!;
  };

  it("the stylesheet pins the foot: sticky AND a bottom inset (sticky with no inset never sticks)", () => {
    const foot = cssRule(".gate-foot");
    expect(foot).toMatch(/position:\s*sticky/);
    expect(foot).toMatch(/(?:^|[;\s])bottom:\s*-?\d/);
  });

  it("errors in the foot scroll in their own capped box, so a long diagnostic never covers the step", () => {
    const errors = cssRule(".gate-foot .gate-errors");
    expect(errors).toMatch(/max-height:\s*\d/);
    expect(errors).toMatch(/overflow-y:\s*auto/);
  });

  it("a loop approval's three answers stack: Deny · Approve on one row, Approve all remaining spanning under them (Task 183)", () => {
    // Deny + Approve + "Approve all remaining" (~330px) do not fit the callout's ~296px row; one
    // flex row would push Deny out of the box. The grid keeps two columns right-aligned and the
    // bulk action on its own full-span row, on one line.
    const actions = cssRule(".gate-actions.gate-actions-loop");
    expect(actions).toMatch(/display:\s*grid/);
    expect(actions).toMatch(/grid-template-columns:\s*auto auto/);
    expect(actions).toMatch(/justify-content:\s*end/);
    const bulk = cssRule(".gate-approve-all");
    expect(bulk).toMatch(/grid-column:\s*1\s*\/\s*-1/);
    expect(bulk).toMatch(/white-space:\s*nowrap/);
  });

  it("the callout header's subtitle (the gated step id) ellipsizes on one line instead of pushing the ✕ out", () => {
    const subtitle = cssRule(".node-callout-subtitle");
    expect(subtitle).toMatch(/min-width:\s*0/);
    expect(subtitle).toMatch(/overflow:\s*hidden/);
    expect(subtitle).toMatch(/text-overflow:\s*ellipsis/);
    expect(subtitle).toMatch(/white-space:\s*nowrap/);
  });
});
