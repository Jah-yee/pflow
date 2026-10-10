// The gate panel (Task 176): renders a paused run's GateRequest and delivers the human's
// answer — the ADR-0009 loop (read the gate → render the payload → answer via `pflow resume`,
// spawned server-side by POST /api/resume). Kind-switched (spec ledger #1): an approval shows
// the masked action preview + Approve/Deny; an escalation shows the agent's question, its
// options as SELECTABLE cards plus a free-text field, with ONE Answer button submitting
// whichever is active (owner decision 2026-07-12, after the first real mis-click: an answer
// consumes the gate token irreversibly, so option cards select — they never fire — and
// selecting clears the text, typing clears the selection). Lives INSIDE a NodeCallout GraphView
// anchors at the ⏸ frontier node; on a delivered answer the parent PINS the overlay to the
// new attempt (onPinRun), which clears the paused banner and unmounts this panel.
//
// Layout (#714): whatever ANSWERS the gate (+ its errors) goes in `.gate-foot`, which stays
// pinned while everything above it scrolls (index.css). Escalation option cards stay above it:
// they only select, and a long option list must be able to scroll.
//
// A LOOP approval gate (Task 183) also offers "Approve all remaining" — the browser's
// `pflow resume <token> --approve yes --auto-approve <paused step>` (the server maps
// `auto_approve: true` to that argv). Approve stays the one accent fill; the label never names a
// count (the engine promises a ceiling, not a count); escalations never get it (`--auto-approve`
// pre-answers approval gates only).
//
// The answer delivery + refusal machine (superseded / ack-then-force / inline diagnostics —
// "refusals are the UX, never silence") is the shared useResumeAnswer/RefusalNotice seam in
// resumeAnswer.tsx; this file owns only the gate CONTENT.

import { useEffect, useState } from "react";

import { ApiError, fetchGate } from "../api/client";
import { GateErrors, RefusalNotice, useResumeAnswer } from "./resumeAnswer";
import type { ApiErrorEntry, GateInfo } from "../types";

// An escalation option's display label — the falsy `option N` fallback mirrors
// core/gate.py::option_labels (THE numbering rule), so this panel, the TTY prompt and the
// pause output can never disagree. Answers send the LABEL text, never the number (the
// loader's numeric mapping is a terminal convenience; labels are unambiguous).
function optionLabel(option: Record<string, unknown>, index: number): string {
  return option.label ? String(option.label) : `option ${index + 1}`;
}

// The cap a loop gate SHOWS: a number the iteration has not passed (a back edge into the loop
// continues the per-run count past it — "iteration 4 of up to 3" is never shown), else null.
function shownCap(iteration: number, maxIterations: unknown): number | null {
  return typeof maxIterations === "number" && iteration <= maxIterations ? maxIterations : null;
}

// A loop gate's position — the TS twin of core/gate.py::loop_position; both are pinned by
// test/fixtures/loop-position.json, so the eyebrow and every Python pause surface agree.
export function loopPosition(iteration: unknown, maxIterations: unknown): string | null {
  if (typeof iteration !== "number") return null;
  const cap = shownCap(iteration, maxIterations);
  return cap === null ? `iteration ${iteration}` : `iteration ${iteration} of up to ${cap}`;
}

// "Approve all remaining"'s tooltip: the TRUE scope of `--auto-approve <step>` — it matches by
// step id across the whole run, sub-workflows and later visits included — then the loop's bound
// exactly as the eyebrow shows it.
function approveAllTitle(nodeId: string, iteration: number, maxIterations: unknown): string {
  const scope = `Approve this and every later approval of a step named '${nodeId}' in this run, including inside sub-workflows.`;
  const cap = shownCap(iteration, maxIterations);
  return cap === null
    ? `${scope} No limit is known for this loop — it runs until its condition stops it.`
    : `${scope} This loop runs at most ${cap} iterations.`;
}

// A gate value as display text: strings verbatim, everything else as readable JSON
// (the payload is JSON-native by GateRequest contract). Long values scroll in their row.
// Every gate field goes through here, never straight into JSX: an object as a React child
// throws and blanks the whole viewer (#720).
function formatValue(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

export function GateCallout({
  run,
  onPinRun,
}: {
  // The paused run's execution id — the resume token /api/gate and /api/resume key on.
  run: string;
  // A run id to pin the overlay to: the answered attempt (submit 200) or the newer attempt
  // (a superseded refusal). GraphView passes selectRun — the single pin path.
  onPinRun: (runId: string) => void;
}): JSX.Element {
  const [gate, setGate] = useState<GateInfo | null>(null);
  const [fetchErrors, setFetchErrors] = useState<ApiErrorEntry[]>([]);
  const [choice, setChoice] = useState("");
  // The selected option's index, or null. Mutually exclusive with `choice` by construction:
  // selecting clears the text, typing clears the selection — the Answer button always submits
  // exactly one unambiguous source.
  const [selected, setSelected] = useState<number | null>(null);
  const answer = useResumeAnswer(run, onPinRun);

  useEffect(() => {
    let cancelled = false;
    fetchGate(run)
      .then((info) => {
        if (cancelled) return;
        setFetchErrors([]);
        setGate(info);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setFetchErrors(e instanceof ApiError ? e.errors : [{ message: "Could not load the gate payload." }]);
      });
    return () => {
      cancelled = true;
    };
  }, [run]);

  // A refusal with an ACTION replaces the gate content (superseded / ack-then-force).
  if (answer.refusal !== null) {
    return (
      <div className="gate">
        <RefusalNotice answer={answer} context="gate" />
      </div>
    );
  }

  if (gate === null) {
    return (
      <div className="gate">
        {fetchErrors.length > 0 ? <GateErrors errors={fetchErrors} /> : <p className="gate-note">Loading gate…</p>}
      </div>
    );
  }

  const req = gate.gate_request;
  const previewEntries = Object.entries(req.preview ?? {});
  const labels = req.options.map(optionLabel);
  // A recommendation that IS one of the options marks that option instead of repeating as text.
  const recommendedIndex = req.recommendation !== null ? labels.indexOf(req.recommendation) : -1;
  const submitting = answer.submitting;
  const position = loopPosition(req.iteration, req.max_iterations);
  // "Approve all remaining" shows on any loop gate's APPROVAL branch below — capped or not (an
  // unknown cap still has a bound, the loop's condition; the tooltip says so).
  const loopIteration = typeof req.iteration === "number" ? req.iteration : null;

  return (
    <div className="gate">
      <p className="gate-eyebrow">
        {req.node_type} · {req.node_id}
        {position !== null && (
          <>
            {" "}
            <span className="gate-eyebrow-position">· {position}</span>
          </>
        )}
      </p>
      {req.kind === "action_approval" ? (
        <>
          <p className="gate-question">Run this step?</p>
          {previewEntries.length > 0 && (
            <dl className="gate-preview">
              {previewEntries.map(([key, value]) => (
                <div className="gate-preview-row" key={key}>
                  <dt className="gate-preview-key">{key}</dt>
                  <dd className="gate-preview-value">{formatValue(value)}</dd>
                </div>
              ))}
            </dl>
          )}
          {req.recommendation != null && <p className="gate-recommendation">{formatValue(req.recommendation)}</p>}
          <div className="gate-foot">
            <GateErrors errors={answer.errors} />
            <div className={loopIteration !== null ? "gate-actions gate-actions-loop" : "gate-actions"}>
              <button
                type="button"
                className="gate-btn gate-deny"
                disabled={submitting}
                onClick={() => answer.submit({ approve: "no" })}
              >
                Deny
              </button>
              <button
                type="button"
                className="gate-btn gate-approve"
                disabled={submitting}
                onClick={() => answer.submit({ approve: "yes" })}
              >
                Approve
              </button>
              {loopIteration !== null && (
                <button
                  type="button"
                  className="gate-btn gate-approve-all"
                  title={approveAllTitle(req.node_id, loopIteration, req.max_iterations)}
                  disabled={submitting}
                  onClick={() => answer.submit({ approve: "yes", auto_approve: true })}
                >
                  Approve all remaining
                </button>
              )}
            </div>
          </div>
        </>
      ) : (
        <>
          {req.question != null && <p className="gate-question">{formatValue(req.question)}</p>}
          {req.options.length > 0 && (
            <ol className="gate-options">
              {req.options.map((option, i) => (
                <li key={i}>
                  {/* SELECTS, never submits (owner decision 2026-07-12): the answer consumes the
                      gate token irreversibly, so the one deliberate submit is the Answer button. */}
                  <button
                    type="button"
                    className={`gate-option${i === recommendedIndex ? " gate-recommended" : ""}${i === selected ? " gate-selected" : ""}`}
                    aria-pressed={i === selected}
                    disabled={submitting}
                    onClick={() => {
                      setSelected(i);
                      setChoice("");
                    }}
                  >
                    <span className="gate-option-label">{labels[i]}</span>
                    {typeof option.description === "string" && (
                      <span className="gate-option-desc">{option.description}</span>
                    )}
                    {i === recommendedIndex && <span className="gate-option-mark">recommended</span>}
                  </button>
                </li>
              ))}
            </ol>
          )}
          {req.recommendation != null && recommendedIndex === -1 && (
            <p className="gate-recommendation">Recommended: {formatValue(req.recommendation)}</p>
          )}
          <div className="gate-foot">
            <GateErrors errors={answer.errors} />
            <form
              className="gate-freeform"
              onSubmit={(e) => {
                e.preventDefault();
                // One submit path for both sources. Empty/whitespace text never posts — the
                // server would 400 it (its shape guard); blocking client-side keeps the refusal
                // out of the wire entirely.
                if (selected !== null) {
                  answer.submit({ choose: labels[selected]! });
                  return;
                }
                const text = choice.trim();
                if (text !== "") answer.submit({ choose: text });
              }}
            >
              <input
                className="gate-freeform-input"
                value={choice}
                onChange={(e) => {
                  setChoice(e.target.value);
                  setSelected(null); // typing moves the intent to free text
                }}
                placeholder={req.options.length > 0 ? "Or answer in your own words…" : "Type an answer…"}
                aria-label="Free-text answer"
              />
              {/* Static label, beside the input (owner-preferred layout 2026-07-12): a dynamic
                  "Answer with X" squeezed the input (clipped placeholder) and pushed the panel
                  past the callout's 320px max-height (scrollbar). The highlighted card names the
                  selection; the tooltip carries the full "Answer with X" for hover confirmation. */}
              <button
                type="submit"
                className="gate-btn gate-primary"
                title={selected !== null ? `Answer with “${labels[selected]}”` : undefined}
                disabled={submitting || (selected === null && choice.trim() === "")}
              >
                Answer
              </button>
            </form>
          </div>
        </>
      )}
    </div>
  );
}
