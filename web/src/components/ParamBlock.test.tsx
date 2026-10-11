// @vitest-environment jsdom
// ParamBlock's batch-alias expander: a `${item.x}` value on a LITERAL batch
// grows a per-item toggle that reveals the resolved values inline. ParamBlock is
// a plain component (no React Flow context), so it renders directly under jsdom.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { ParamBlock } from "./ReadPanel";
import { highlight } from "../utils/highlight";
import { fullValue } from "../utils/format";
import type { BatchSpec, RFParam } from "../types";

// Keep CodeBlock SYNCHRONOUS (highlight → null = legacy plain-text paint), so the
// resolved values are assertable as plain text without an async settle.
vi.mock("../utils/highlight", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../utils/highlight")>();
  return { ...actual, highlight: vi.fn().mockResolvedValue(null) };
});

afterEach(cleanup);

const param = (over: Partial<RFParam> = {}): RFParam => ({
  name: "prompt",
  value: "${item.prompt}",
  is_dynamic: true,
  source: null,
  ...over,
});

const literalBatch = (over: Partial<BatchSpec> = {}): BatchSpec => ({
  parallel: true,
  dynamic: false,
  as_name: "item",
  source_ref: null,
  count: 2,
  items: [
    { focus: "emotional", prompt: "EMOTIONAL prompt body" },
    { focus: "details", prompt: "DETAILS prompt body" },
  ],
  ...over,
});

describe("ParamBlock — batch-alias expansion", () => {
  it("expands ${item.prompt} into each item's resolved value on click", () => {
    render(<ParamBlock param={param()} kind="llm" batch={literalBatch()} />);
    const toggle = screen.getByRole("button", { name: /2 items/ });
    // collapsed
    expect(screen.queryByText("focus: emotional")).toBeNull();
    expect(screen.queryByText("EMOTIONAL prompt body")).toBeNull();
    // expanded: each item's discriminating-field header + resolved content
    fireEvent.click(toggle);
    expect(screen.getByText("focus: emotional")).toBeTruthy();
    expect(screen.getByText("EMOTIONAL prompt body")).toBeTruthy();
    expect(screen.getByText("focus: details")).toBeTruthy();
    expect(screen.getByText("DETAILS prompt body")).toBeTruthy();
  });

  it("a code body's ${item.x} is never expanded; the same read in a Template param is", () => {
    // Task 118: a shell `command` / code `code` is plain code (mode "body") — its
    // `${item.prompt}` is the shell's/Python's own text.
    render(<ParamBlock param={param({ name: "command", value: "echo ${item.prompt}", mode: "body" })} kind="shell" batch={literalBatch()} />);
    expect(screen.queryByRole("button", { name: /items/ })).toBeNull();
    cleanup();
    render(<ParamBlock param={param({ name: "stdin", value: "${item.prompt}", mode: "template" })} kind="shell" batch={literalBatch()} />);
    expect(screen.getByRole("button", { name: /2 items/ })).toBeTruthy();
  });

  it("expands a dict env per item, with the param's JSON rendering", () => {
    render(<ParamBlock param={param({ name: "env", value: { PROMPT: "${item.prompt}" } })} kind="shell" batch={literalBatch()} />);
    fireEvent.click(screen.getByRole("button", { name: /2 items/ }));
    expect(screen.getByText("focus: emotional")).toBeTruthy();
    const values = [...document.querySelectorAll(".batch-item .read-param-value")].map((el) => el.textContent);
    expect(values).toEqual([
      JSON.stringify({ PROMPT: "EMOTIONAL prompt body" }, null, 2),
      JSON.stringify({ PROMPT: "DETAILS prompt body" }, null, 2),
    ]);
    // colored as JSON, like the un-expanded dict (an item's value is text, so the
    // language must come from the param's value, not the item's)
    expect(highlight).toHaveBeenCalledWith(values[0], "json");
  });

  it("shows no expander when the value does not read the batch alias", () => {
    render(<ParamBlock param={param({ name: "timeout", value: "300", is_dynamic: false })} kind="llm" batch={literalBatch()} />);
    expect(screen.queryByRole("button", { name: /items/ })).toBeNull();
  });

  it("the param's file:line is a LINK carrying the PARAM's own ref when onOpenSource is wired; plain text otherwise", () => {
    const onOpenSource = vi.fn();
    const src = { file: "demo.pflow.md", line: 25 };
    render(<ParamBlock param={param({ name: "command", value: "ls", source: src })} kind="shell" onOpenSource={onOpenSource} />);
    const link = screen.getByText("demo.pflow.md:25");
    expect(link.tagName).toBe("BUTTON");
    fireEvent.click(link);
    expect(onOpenSource).toHaveBeenCalledWith(src);
    cleanup();
    render(<ParamBlock param={param({ name: "command", value: "ls", source: src })} kind="shell" />);
    expect(screen.getByText("demo.pflow.md:25").tagName).toBe("SPAN");
  });

  it("the param value carries the ⛶ expand titled by the PARAM's name (every value box has it)", () => {
    render(<ParamBlock param={param({ name: "code", value: "x = 1" })} kind="code" />);
    fireEvent.click(screen.getByLabelText("Expand code"));
    const dialog = screen.getByRole("dialog");
    expect(dialog.textContent).toContain("x = 1");
    expect(screen.getByText("code", { selector: ".value-modal-title" })).toBeTruthy();
  });

  it("shows no expander for a dynamic batch (no literal items to resolve)", () => {
    render(<ParamBlock param={param()} kind="llm" batch={literalBatch({ dynamic: true, items: null })} />);
    expect(screen.queryByRole("button", { name: /items/ })).toBeNull();
  });

  it("shows no expander when no batch is passed (the EdgePanel path)", () => {
    render(<ParamBlock param={param()} kind="llm" />);
    expect(screen.queryByRole("button", { name: /items/ })).toBeNull();
  });
});

describe("ParamBlock — embedded code (an MCP tool's JavaScript)", () => {
  // Only a `${x|json}` insert is pflow's: the JavaScript's own `${…}` and `$${…}` are
  // plain code — no teal, no substitution.
  const tealed = (root: ParentNode): string[] => [...root.querySelectorAll(".src-ref")].map((el) => el.textContent ?? "");
  const people = literalBatch({
    items: [
      { name: "Ann", id: 7 },
      { name: "Bo", id: 8 },
    ],
  });
  const fn = "() => [${item.name|json}, `${item.id}`, `$${price}`, ${up.stdout|json}]";

  it("the value teals only the inserts", () => {
    render(<ParamBlock param={param({ name: "function", value: fn, mode: "embedded" })} kind="mcp-chrome-devtools-evaluate_script" />);
    expect(tealed(document.querySelector(".read-param-value")!)).toEqual(["${item.name|json}", "${up.stdout|json}"]);
    cleanup();
    // Presence pair: the same text as a Template teals the bare `${item.id}` too.
    render(<ParamBlock param={param({ name: "function", value: fn, mode: "template" })} kind="mcp-chrome-devtools-evaluate_script" />);
    expect(tealed(document.querySelector(".read-param-value")!)).toEqual(["${item.name|json}", "${item.id}", "${up.stdout|json}"]);
  });

  it("the per-item preview substitutes the insert as JSON and leaves the JavaScript's `${item.id}` plain", () => {
    render(<ParamBlock param={param({ name: "function", value: fn, mode: "embedded" })} kind="mcp-chrome-devtools-evaluate_script" batch={people} />);
    fireEvent.click(screen.getByRole("button", { name: /2 items/ }));
    const blocks = [...document.querySelectorAll(".batch-item .read-param-value")];
    expect(blocks.map((el) => el.textContent)).toEqual([
      '() => ["Ann", `${item.id}`, `$${price}`, ${up.stdout|json}]',
      '() => ["Bo", `${item.id}`, `$${price}`, ${up.stdout|json}]',
    ]);
    expect(blocks.map(tealed)).toEqual([["${up.stdout|json}"], ["${up.stdout|json}"]]);
  });

  it("a Template param's preview still substitutes and teals as before", () => {
    const value = "Hi ${item.name} from ${up.stdout}";
    render(<ParamBlock param={param({ name: "prompt", value, mode: "template" })} kind="mcp-x-run" batch={people} />);
    fireEvent.click(screen.getByRole("button", { name: /2 items/ }));
    const blocks = [...document.querySelectorAll(".batch-item .read-param-value")];
    expect(blocks.map((el) => el.textContent)).toEqual(["Hi Ann from ${up.stdout}", "Hi Bo from ${up.stdout}"]);
    expect(blocks.map(tealed)).toEqual([["${up.stdout}"], ["${up.stdout}"]]);
  });

  it("the ⛶ modal reads the same mode", () => {
    render(<ParamBlock param={param({ name: "function", value: fn, mode: "embedded" })} kind="mcp-chrome-devtools-evaluate_script" />);
    fireEvent.click(screen.getByLabelText("Expand function"));
    expect(tealed(screen.getByRole("dialog"))).toEqual(["${item.name|json}", "${up.stdout|json}"]);
  });
});

describe("ParamBlock — a dict param's refs are read per leaf (a shell step's env)", () => {
  // The JSON shows `\"fallback\"`; read as text that is an Issue and the selected edge's
  // mark would vanish. The escape leaf is the shell's literal `${up.stdout}`, never a mark.
  const env = { X: '${up.stdout ?? "fallback"}', Y: "$${up.stdout}" };
  const marks = (root: ParentNode): string[] => [...root.querySelectorAll(".ref-mark")].map((el) => el.textContent ?? "");

  it("the selected edge marks the leaf's coalesce reference, and the box shows fullValue's text", () => {
    render(<ParamBlock param={param({ name: "env", value: env })} kind="shell" highlightRef="up.stdout" />);
    const box = document.querySelector(".read-param-value")!;
    expect(marks(box)).toEqual(['${up.stdout ?? \\"fallback\\"}']);
    expect(box.textContent).toBe(fullValue(env));
  });

  it("the ⛶ modal marks it too", () => {
    render(<ParamBlock param={param({ name: "env", value: env })} kind="shell" highlightRef="up.stdout" />);
    fireEvent.click(screen.getByLabelText("Expand env"));
    expect(marks(screen.getByRole("dialog"))).toEqual(['${up.stdout ?? \\"fallback\\"}']);
  });
});
