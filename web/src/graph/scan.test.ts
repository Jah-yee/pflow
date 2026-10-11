// Param-text read-scan tests (scan.ts): plain-param sibling reads correcting the
// quiet claim, exercised through buildFlow's observed-read merge, plus
// consumedReadPaths (the read panel's full-depth fact). Split from flow.test.ts
// beside their subject — architecture-review candidate 2, 2026-06-13.

import { describe, expect, it } from "vitest";

import { consumedReadPaths, templateTokens } from "./scan";
import { buildFlow } from "./flow";
import type { NodeRow, OutputRow } from "./rows";
import { paramHandle } from "./handles";
import { DETAILED, edge, group, node } from "./testFixtures";
import type { ParamMode, RFGraph } from "../types";


// The leaf's output rows, recovered from the unified body row list (LeafData.rows
// — the nodeRows model): the same OutputRow objects buildFlow composed, so the
// assertions below still pin the outputRowsFor → LeafData seam.
function leafOutputRows(leaf: { data: { rows: NodeRow[] } }): OutputRow[] {
  return leaf.data.rows.flatMap((r) => (r.kind === "output" ? [r.row] : []));
}

describe("buildFlow — plain-param reads correct the quiet claim (no edges, no lines)", () => {
  // `prompt: ${gen.result.ok}` forms NO data-flow edge, so edge-derived quiet
  // wrongly claimed "unconsumed" for prompt-fed keys (user decision 2026-06-10:
  // the param-text scan). The scan only ever flips quiet / extends key unions —
  // it must not create rows or lines.
  const shaped = {
    field: "result",
    data_type: "dict",
    keys: [
      { name: "ok", data_type: "bool" },
      { name: "n", data_type: "int" },
    ],
  };

  it("a sibling prompt ref un-quiets its key row — and still draws NO line (D5)", () => {
    const g: RFGraph = {
      nodes: [
        node("gen", { output_shape: shaped }),
        node("use", {
          kind: "llm",
          params: [{ name: "prompt", value: "Summarize ${gen.result.ok}", is_dynamic: true, source: null }],
        }),
      ],
      edges: [],
      groups: [],
    };
    const { nodes, edges } = buildFlow(g, DETAILED);
    const leaf = nodes.find((n) => n.id === "gen");
    if (leaf?.type !== "node") throw new Error("expected gen");
    expect(leafOutputRows(leaf)).toEqual([
      { field: "result.ok", label: "result.ok", dataType: "bool", quiet: false, nested: false },
      { field: "result.n", label: "result.n", dataType: "int", quiet: true, nested: false },
    ]);
    expect(edges.filter((e) => e.data?.kind === "data_flow")).toHaveLength(0);
  });

  it("never creates a new field row (no edge + no shape → no row = no claim)", () => {
    const g: RFGraph = {
      nodes: [
        node("gen"),
        node("use", { params: [{ name: "p", value: "${gen.stdout}", is_dynamic: true, source: null }] }),
      ],
      edges: [],
      groups: [],
    };
    const { nodes } = buildFlow(g, DETAILED);
    const leaf = nodes.find((n) => n.id === "gen");
    if (leaf?.type !== "node") throw new Error("expected gen");
    expect(leafOutputRows(leaf)).toEqual([]);
  });

  it("a ref inside a quoted COALESCE LITERAL is never a read (the row stays quiet)", () => {
    // `${cfg.text ?? "ask gen.result owner"}`: the quoted fallback contains a
    // space, and a space inside the literal satisfies the root prefix class —
    // without the operand split, `gen`'s result row read as ACTIVE with zero
    // real readers (the inverse of the lie quiet rows prevent; review-caught
    // 2026-06-11). Python's build is immune (scope.py splits operands); the
    // frontend scan must mirror it.
    const g: RFGraph = {
      nodes: [
        node("gen", { output_shape: shaped }),
        node("use", {
          params: [{ name: "note", value: '${cfg.text ?? "ask gen.result owner"}', is_dynamic: true, source: null }],
        }),
      ],
      edges: [],
      groups: [],
    };
    const { nodes } = buildFlow(g, DETAILED);
    const leaf = nodes.find((n) => n.id === "gen");
    if (leaf?.type !== "node") throw new Error("expected gen");
    expect(leafOutputRows(leaf).every((r) => r.quiet)).toBe(true);
  });

  it("an escaped template and a spaced operand are never reads (the grammar gate)", () => {
    // Runtime parity (mirrors scope.py): `$${gen.result.ok}` resolves to the
    // literal text `${gen.result.ok}`, and `${ gen.result.ok }` never resolves
    // at all — neither may un-quiet a row.
    const g: RFGraph = {
      nodes: [
        node("gen", { output_shape: shaped }),
        node("use", {
          params: [
            { name: "a", value: "$${gen.result.ok}", is_dynamic: false, source: null },
            { name: "b", value: "${ gen.result.ok }", is_dynamic: false, source: null },
          ],
        }),
      ],
      edges: [],
      groups: [],
    };
    const { nodes } = buildFlow(g, DETAILED);
    const leaf = nodes.find((n) => n.id === "gen");
    if (leaf?.type !== "node") throw new Error("expected gen");
    expect(leafOutputRows(leaf).every((r) => r.quiet)).toBe(true);
  });

  it("a ref in the NON-literal coalesce operand IS a read (positive control)", () => {
    const g: RFGraph = {
      nodes: [
        node("gen", { output_shape: shaped }),
        node("use", {
          params: [{ name: "note", value: '${gen.result.ok ?? "x"}', is_dynamic: true, source: null }],
        }),
      ],
      edges: [],
      groups: [],
    };
    const { nodes } = buildFlow(g, DETAILED);
    const leaf = nodes.find((n) => n.id === "gen");
    if (leaf?.type !== "node") throw new Error("expected gen");
    expect(leafOutputRows(leaf).find((r) => r.field === "result.ok")?.quiet).toBe(false);
  });

  it("scope-aware: a same-named node in ANOTHER scope is not marked", () => {
    const g: RFGraph = {
      nodes: [
        node("gen", { output_shape: shaped, parent: "g0" }),
        node("use", { params: [{ name: "p", value: "${gen.result.ok}", is_dynamic: true, source: null }] }),
      ],
      edges: [],
      groups: [group("g0", { kind: "workflow", members: ["gen"] })],
    };
    const { nodes } = buildFlow(g, DETAILED);
    const leaf = nodes.find((n) => n.id === "gen");
    if (leaf?.type !== "node") throw new Error("expected gen");
    expect(leafOutputRows(leaf).every((r) => r.quiet)).toBe(true);
  });

  it("consumedReadPaths: the panel's consumed list agrees with the canvas (edges + param reads, full depth)", () => {
    // Panel/canvas parity (review-caught 2026-06-11): a key consumed ONLY via a
    // prompt body must list in the panel's "consumed" fact; edge reads keep
    // their untruncated dotted paths; the no-new-claims gate still applies.
    const g: RFGraph = {
      nodes: [
        node("gen", { output_shape: shaped }),
        node("edge-reader", { params: [{ name: "p", value: "${gen.result.a.b}", is_dynamic: true, source: null }] }),
        node("prompt-reader", {
          kind: "llm",
          params: [{ name: "prompt", value: "Use ${gen.result.ok} and ${gen.nope.x}", is_dynamic: true, source: null }],
        }),
      ],
      edges: [
        edge("e0", "gen", "edge-reader", "data_flow", { output_field: "result", input_name: "p", output_path: ["a", "b"] }),
      ],
      groups: [],
    };
    const paths = consumedReadPaths(g);
    // Edge read full-depth; the prompt-only read listed too; `nope` gated out
    // (no edge read, not the authored shape's field — no row = no claim).
    expect(paths.get("gen")).toEqual(["result.a.b", "result.ok"]);
  });

  it("the reader's batch alias never reads a sibling that shares its name", () => {
    const g: RFGraph = {
      nodes: [
        node("item", { output_shape: shaped }),
        node("use", {
          batch: { parallel: false, dynamic: true, as_name: "item", source_ref: "${rows}", count: null, items: null },
          params: [{ name: "p", value: "${item.result.ok}", is_dynamic: true, source: null }],
        }),
      ],
      edges: [],
      groups: [],
    };
    const { nodes } = buildFlow(g, DETAILED);
    const leaf = nodes.find((n) => n.id === "item");
    if (leaf?.type !== "node") throw new Error("expected item");
    expect(leafOutputRows(leaf).every((r) => r.quiet)).toBe(true);
  });
});

describe("consumedReadPaths — runtime parity (mirrors scope.py)", () => {
  // The shapes of `test_graph_build.py::test_refs_with_path_in_reads_the_template_parse`:
  // the scan must read exactly the References `core/templates.parse()` yields —
  // indices are not fields, a dynamic index reads its outer path AND its index source,
  // an escape consumes through its balanced `}`, an Issue reads nothing.
  const producers = [
    node("gen", { output_shape: { field: "result", data_type: "dict", keys: [] } }),
    node("idx", { output_shape: { field: "result", data_type: "int", keys: [] } }),
  ];
  const readsOf = (value: string): Record<string, string[]> => {
    const g: RFGraph = {
      nodes: [...producers, node("use", { params: [{ name: "p", value, is_dynamic: true, source: null }] })],
      edges: [],
      groups: [],
    };
    return Object.fromEntries(consumedReadPaths(g));
  };

  it.each<[string, string, Record<string, string[]>]>([
    ["a static index is not a field", "${gen.result[0].ok}", { gen: ["result.ok"] }],
    ["fields after an index are kept", "${gen.result[0].a.b}", { gen: ["result.a.b"] }],
    [
      "a dynamic index reads the outer path and its index source",
      "${gen.result[${idx.result}].ok}",
      { gen: ["result.ok"], idx: ["result"] },
    ],
    ["a dynamic index inside a coalesce", '${gen.result[${idx.result}] ?? "none"}', { gen: ["result"], idx: ["result"] }],
    ["an escape consumes through its balanced brace (delta 4)", "$${FOO:-${gen.result.ok}}", {}],
    ["a real ref after an escape still reads", "$${FOO:-${gen.result.ok}} ${gen.result.n}", { gen: ["result.n"] }],
    ["an escaped dynamic index reads nothing", "$${gen.result[${idx.result}]}", {}],
    ["multi-index is an Issue, not a read", "${gen.result[0][1]}", {}],
    ["an Issue runs through its first brace", "${gen.result[${idx.result ?? 0}]}", {}],
    ["a JSON insert reads its expression", "${gen.result.ok|json}", { gen: ["result.ok"] }],
    ["a JSON insert of a coalesce reads each reference", '${gen.result ?? idx.result | json}', { gen: ["result"], idx: ["result"] }],
    ["a misspelled insert word is an Issue", "${gen.result|jsn}", {}],
    ["a space before the brace is an Issue", "${gen.result|json }", {}],
  ])("%s: %s", (_label, value, expected) => {
    expect(readsOf(value)).toEqual(expected);
  });
});

describe("templateTokens — the one walk, a mirror of `_tokenize` (test_templates.py SHAPES)", () => {
  // Each token as `kind:written`; a JSON insert shows as `insert:`. Python folds an
  // escape into its Text; the walk keeps it a token of its own, so a reader can show it
  // as written.
  const show = (source: string, mode?: ParamMode): string[] =>
    templateTokens(source, mode).map((t) => {
      const kind = t.kind === "expression" && t.asJson ? "insert" : t.kind;
      return `${kind}:${source.slice(t.start, t.end)}`;
    });

  const SHAPES: Array<[string, string[]]> = [
    ["", []],
    ["plain", ["text:plain"]],
    ["${a}", ["expression:${a}"]],
    ["${node.items[0].n}", ["expression:${node.items[0].n}"]],
    ['${a[${i.j}].x ?? "d"}', ['expression:${a[${i.j}].x ?? "d"}']],
    ["[${a}]", ["text:[", "expression:${a}", "text:]"]],
    ["${a}${b}", ["expression:${a}", "expression:${b}"]],
    ["Hi $${x} ${y}!", ["text:Hi ", "escape:$${x}", "text: ", "expression:${y}", "text:!"]],
    ["$$${x}", ["text:$", "escape:$${x}"]],
    ["$${a[${i}]}", ["escape:$${a[${i}]}"]],
    ["$${unclosed ${b}", ["escape:$${", "text:unclosed ", "expression:${b}"]],
    ["${c.result.0} tail", ["issue:${c.result.0}", "text: tail"]],
    ["${a", ["issue:${a"]],
    ["${a[${i ?? 0}]}", ["issue:${a[${i ?? 0}", "text:]}"]],
    ['${a ?? "\\q"}', ['issue:${a ?? "\\q"}']],
    ["${a ?? 007}", ["issue:${a ?? 007}"]],
    ["${0}", ["expression:${0}"]],
    ["${true}", ["expression:${true}"]],
    ["${x|json}", ["insert:${x|json}"]],
    ["${x | json}", ["insert:${x | json}"]],
    ['${a ?? "d" | json}!', ['insert:${a ?? "d" | json}', "text:!"]],
    ['${a ?? "x|json"}', ['expression:${a ?? "x|json"}']],
    ["${x|JSON}", ["issue:${x|JSON}"]],
    ["${x|json }", ["issue:${x|json }"]],
    ["${ x|json}", ["issue:${ x|json}"]],
    ["${x||json}", ["issue:${x||json}"]],
    ["$${x|json}", ["escape:$${x|json}"]],
  ];

  it.each(SHAPES)("%s", (source, tokens) => {
    expect(show(source)).toEqual(tokens);
  });

  it("tokens tile the source: contiguous, non-empty, from 0 to its length", () => {
    for (const [source] of SHAPES) {
      for (const mode of ["template", "embedded", "body"] as const) {
        const tokens = templateTokens(source, mode);
        let pos = 0;
        for (const t of tokens) {
          expect([t.start, t.end > t.start]).toEqual([pos, true]);
          pos = t.end;
        }
        expect(pos).toBe(source.length);
      }
    }
  });

  it("an expression carries its operands as written and the References among them", () => {
    const [expr] = templateTokens('${a[${i.j}].x ?? "d"|json}');
    expect(expr).toEqual({
      kind: "expression",
      start: 0,
      end: 26,
      asJson: true,
      operands: ["a[${i.j}].x", '"d"'],
      refs: [
        { root: "a", fields: ["x"] },
        { root: "i", fields: ["j"] },
      ],
    });
  });

  // PA's view row (test_templates.py): only the JSON insert is pflow's.
  const VIEW_SOURCE = "`${a + b}` $${p} ${user.name} ${t|json} '${x}'";

  it("embedded: only the JSON insert is an expression — the rest is text, cut verbatim", () => {
    expect(show(VIEW_SOURCE, "embedded")).toEqual(["text:`${a + b}` $${p} ${user.name} ", "insert:${t|json}", "text: '${x}'"]);
    // The same source as a Template: the bare `${user.name}` and `${x}` are expressions.
    expect(show(VIEW_SOURCE)).toEqual([
      "text:`",
      "issue:${a + b}",
      "text:` ",
      "escape:$${p}",
      "text: ",
      "expression:${user.name}",
      "text: ",
      "insert:${t|json}",
      "text: '",
      "expression:${x}",
      "text:'",
    ]);
  });

  it("embedded: an insert an escape or an Issue swallows stays text, as in `embedded_code`", () => {
    expect(show("$${foo ${x|json}} ${${y|json} + 1} ${z|json}", "embedded")).toEqual([
      "text:$${foo ${x|json}} ${${y|json} + 1} ",
      "insert:${z|json}",
    ]);
  });

  it("body: one text token, whatever the text holds", () => {
    expect(show('echo "${a.out}" ${b|json}', "body")).toEqual(['text:echo "${a.out}" ${b|json}']);
  });
});

describe("param reads follow the param's mode — parity with Python's param_mode", () => {
  // A code body (shell `command`, code `code`) reads nothing: its `${a.out}` is the
  // shell's or Python's own text (Task 118). Embedded code (an MCP tool's JavaScript)
  // reads only its `${x|json}` inserts. Python decides the mode; the payload carries it.
  const producer = node("a", { output_shape: { field: "out", data_type: "str", keys: [] } });
  const readsOf = (mode: ParamMode | undefined, value: unknown): Record<string, string[]> => {
    const g: RFGraph = {
      nodes: [producer, node("b", { params: [{ name: "p", value, is_dynamic: true, source: null, mode }] })],
      edges: [],
      groups: [],
    };
    return Object.fromEntries(consumedReadPaths(g));
  };

  it.each<[ParamMode | undefined, unknown, Record<string, string[]>]>([
    ["body", 'echo "${a.out}"', {}],
    ["template", 'echo "${a.out}"', { a: ["out"] }],
    [undefined, 'echo "${a.out}"', { a: ["out"] }], // absent on a hand-built param: a Template
    ["body", { DATA: "${a.out}" }, {}],
    ["template", { DATA: "${a.out}" }, { a: ["out"] }],
    ["embedded", "() => ${a.out}", {}],
    ["embedded", "() => ${a.out|json}", { a: ["out"] }],
    // Distinct paths: a nested leaf read as a Template would add `out.bare`.
    ["embedded", { x: "${a.out.inserted|json}", y: "${a.out.bare}" }, { a: ["out.inserted"] }],
    ["template", "() => ${a.out|json}", { a: ["out"] }], // an insert reads anywhere (the validator refuses it)
  ])("%s: %j", (mode, value, expected) => {
    expect(readsOf(mode, value)).toEqual(expected);
  });

  it("an env Reference's edge lands on the env row, labelled by its key", () => {
    const g: RFGraph = {
      nodes: [
        producer,
        node("b", {
          params: [
            { name: "command", value: 'echo "$DATA" ${HOME}', is_dynamic: false, source: null },
            { name: "env", value: { DATA: "${a.out}" }, is_dynamic: true, source: null },
          ],
        }),
      ],
      // Python's edge for an env leaf carries the env KEY as input_name (build.py:_params_strings).
      edges: [edge("e0", "a", "b", "data_flow", { output_field: "out", input_name: "DATA" })],
      groups: [],
    };
    const { edges } = buildFlow(g, DETAILED);
    expect(edges.find((e) => e.id === "e0")?.targetHandle).toBe(paramHandle("env"));
  });
});
