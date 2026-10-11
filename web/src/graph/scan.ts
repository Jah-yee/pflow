// The `${…}` walk every TS reader uses (`templateTokens`), and param-text read
// scanning: which output fields the graph actually READS, beyond
// what the contract edges carry. The extraction mirrors the runtime's template
// grammar (scope.py / TemplateResolver) so a "read" here is exactly something the
// runtime would resolve — never a guess. Consumed by the canvas rows (via
// buildFlow's observed-read merge) and the read panel (consumedReadPaths): ONE
// shared walk, so the two surfaces can't state contradictory facts about the same
// binding (review-caught 2026-06-11).

import type { ParamMode, RFGraph, RFNode } from "../types";

// What the graph's edges READ from one node, per output field: a bare read
// (`${n.result}`) and/or sub-key reads (`${n.result.ok}` → "ok" — the FIRST
// path segment only, D7; deeper structure is read-panel-only, matching where
// edges can form). Collected in buildFlow's edge scan, in first-read order.
export type FieldReads = { bare: boolean; subKeys: string[] };
// The read-only view outputRowsFor consumes — the edge scan needs mutation,
// the composition must not (a future refactor merging authored keys INTO
// subKeys would silently corrupt the frozen EMPTY_READS singleton otherwise).
export type FieldReadsView = { readonly bare: boolean; readonly subKeys: readonly string[] };

export const EMPTY_READS: FieldReadsView = Object.freeze({ bare: false, subKeys: Object.freeze([]) });

/** The type a producer's `field[.key]` carries, FAIL-CLOSED: the authored
 *  shape's field/key type, else the registry's kind interface — the same
 *  resolution order the output rows use (outputRowsFor). Deeper paths and
 *  anything unprovable return null; never a filler like "any". IoPanel uses
 *  this to type an undeclared workflow output from its producer's annotation. */
export function producedTypeOf(
  node: RFNode | undefined,
  field: string | null,
  path: readonly string[],
  kindTypes?: Readonly<Record<string, string>>,
): string | null {
  if (!node || !field) return null;
  const shape = node.output_shape;
  if (path.length === 0) {
    if (shape?.field === field && shape.data_type) return shape.data_type;
    return kindTypes?.[field] ?? null;
  }
  if (path.length === 1 && shape?.field === field) {
    return shape.keys?.find((k) => k.name === path[0])?.data_type ?? null;
  }
  return null;
}

// The template walk, `templateTokens` — every TS reader of `${…}` goes through it
// (web/src/graph/CLAUDE.md), and it mirrors `_tokenize` in src/pflow/core/templates.py.
// The regex strings are copies of that module's grammar (`_IDENT`,
// `_VAR_NAME_PATTERN`, `_SEGMENT`, `_LITERAL_PATTERN`, `_EXPRESSION`, `_JSON_INSERT`, `_SCAN`): keep
// them in step, so an expression here is exactly one the runtime would resolve.
// One left-to-right scan: an escape `$${…}` (brace-balanced body) is literal text; an
// unescaped `${` either opens an Expression (its non-literal operands are references,
// a dynamic index `a[${i}]` contributing its index source too) or is an Issue that
// runs to the next `}` and reads nothing. Literal operands are not references: a
// quoted fallback like `${cfg.text ?? "ask gen.result owner"}` is not a read of `gen`.
const IDENT = String.raw`[a-zA-Z_][\w-]*`;
const STATIC_PATH = String.raw`${IDENT}(?:(?:\[[0-9]+\])?(?:\.${IDENT}(?:\[[0-9]+\])?)*)?`;
const SEGMENT = String.raw`${IDENT}(?:\[(?:[0-9]+|\$\{${STATIC_PATH}\})\])?`;
const PATH = String.raw`${SEGMENT}(?:\.${SEGMENT})*`;
const LITERAL = String.raw`(?:"(?:[^"\\?\x00-\x1f]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4}|\?(?!\?))*"|\btrue\b|\bfalse\b|\bnull\b|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?|\[\]|\{\})`;
const OPERAND = `(?:${LITERAL}|${PATH})`;
const JSON_INSERT = String.raw`\s*\|\s*json`;
const EXPRESSION_AT = String.raw`\$\{(${OPERAND}(?:\s*\?\?\s*${OPERAND})*)(${JSON_INSERT})?\}`;
const SCAN = String.raw`(\$\$\{(?:[^{}]|\{[^{}]*\})*\}|\$\$\{)|(?<!\$)\$\{`;
const SEGMENT_AT = String.raw`(${IDENT})(?:\[(?:[0-9]+|\$\{(${STATIC_PATH})\})\])?`;
const LITERAL_FULL_RE = new RegExp(`^${LITERAL}$`);
const COALESCE_SPLIT_RE = /\s*\?\?\s*/;

// One Reference: its root and the field names after it (indices are not fields —
// `${data[0].x}` → data, ["x"]).
export type TemplateRef = { root: string; fields: string[] };

/** One span of template text, `[start, end)` in the source. Text, escapes (`$${…}`,
 *  kept as written) and Issues are literal; an expression's `operands` are its
 *  coalesce operands as written (literals included), its `refs` the References
 *  among them, dynamic-index sources included. */
export type TemplateToken =
  | { kind: "text" | "escape" | "issue"; start: number; end: number }
  | { kind: "expression"; start: number; end: number; asJson: boolean; refs: TemplateRef[]; operands: string[] };

/** `pathRefs("a[${i.j}].x")` → a/["x"], then the index source i/["j"] (outer first). */
function pathRefs(path: string): TemplateRef[] {
  const segment = new RegExp(SEGMENT_AT, "y");
  const names: string[] = [];
  const inner: TemplateRef[] = [];
  for (let pos = 0; pos < path.length; pos = segment.lastIndex + 1) {
    segment.lastIndex = pos;
    const m = segment.exec(path);
    if (m == null) break; // unreachable: the expression grammar already matched
    names.push(m[1]!);
    if (m[2] != null) inner.push(...pathRefs(m[2]));
  }
  return [{ root: names[0]!, fields: names.slice(1) }, ...inner];
}

function expressionAt(text: string, start: number): TemplateToken | null {
  const expression = new RegExp(EXPRESSION_AT, "y");
  expression.lastIndex = start;
  const m = expression.exec(text);
  if (m == null) return null;
  const operands = m[1]!.split(COALESCE_SPLIT_RE);
  const refs = operands.filter((op) => !LITERAL_FULL_RE.test(op)).flatMap(pathRefs);
  return { kind: "expression", start, end: expression.lastIndex, asJson: m[2] != null, refs, operands };
}

/** An Issue: an unescaped `${` that opens no expression, through its first `}` (or the end). */
function issueAt(text: string, start: number): TemplateToken {
  const close = text.indexOf("}", start);
  return { kind: "issue", start, end: close === -1 ? text.length : close + 1 };
}

/** The tokens of `text` as a param of `mode` reads it (Python's `param_mode`):
 *  - "template" — the parse (`_tokenize`);
 *  - "embedded" — only JSON inserts (`${x|json}`) stay expressions, every other span
 *    is text (`embedded_code`): a bare `${…}` is the embedded language's own;
 *  - "body" — one text token: a code body's `${…}` is the shell's or Python's.
 *  Text without a param (the source pane) reads as "template". */
export function templateTokens(text: string, mode: ParamMode = "template"): TemplateToken[] {
  const tokens: TemplateToken[] = [];
  let pos = 0;
  const add = (token: TemplateToken): void => {
    if (token.start > pos) tokens.push({ kind: "text", start: pos, end: token.start });
    tokens.push(token);
    pos = token.end;
  };
  if (mode !== "body") {
    const scan = new RegExp(SCAN, "g");
    for (let m = scan.exec(text); m != null; m = scan.exec(text)) {
      const token =
        m[1] != null
          ? { kind: "escape" as const, start: m.index, end: scan.lastIndex }
          : (expressionAt(text, m.index) ?? issueAt(text, m.index));
      scan.lastIndex = token.end;
      if (mode === "template" || (token.kind === "expression" && token.asJson)) add(token);
    }
  }
  if (pos < text.length) tokens.push({ kind: "text", start: pos, end: text.length });
  return tokens;
}

/** Every Reference in `text` as a param of `mode` reads it (scope.py's `refs_with_path_in`). */
function templateRefs(text: string, mode?: ParamMode): TemplateRef[] {
  return templateTokens(text, mode).flatMap((t) => (t.kind === "expression" ? t.refs : []));
}

function stringLeaves(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(stringLeaves);
  if (value !== null && typeof value === "object") return Object.values(value).flatMap(stringLeaves);
  return [];
}

// One plain-param `${sibling.field…}` read, resolved to its producer. The shared
// walk both consumers below derive from (canvas rows AND the read panel — split
// scans would drift; review-caught 2026-06-11): scope-aware (same-parent node_id
// only), batch-alias-skipping, coalesce-literal-skipping, mode-aware (a code body
// reads nothing; embedded code reads only its `${x|json}` inserts); a bare `${gen}`
// names no field and never counts.
//
// KEPT after the unified-edge model fix (2026-06-13, every authored ${ref} now
// draws a contract edge): build-time edge dedup still collapses two same-param
// sub-key refs (`Edge.output_path` is compare=False in the model) — this scan
// recovers the reads those lost edges would have carried.
type ParamRead = { producer: RFNode; segments: string[] };

function paramTextReads(graph: RFGraph): ParamRead[] {
  const byScopeName = new Map<string, RFNode>();
  for (const n of graph.nodes) {
    if (n.io === null && n.kind !== "end") byScopeName.set(`${n.parent ?? ""}|${n.ref.node_id}`, n);
  }
  const found: ParamRead[] = [];
  for (const reader of graph.nodes) {
    const alias = reader.batch?.as_name;
    for (const param of reader.params) {
      for (const leaf of stringLeaves(param.value)) {
        for (const { root, fields } of templateRefs(leaf, param.mode)) {
          if (root === alias) continue; // the per-item batch alias, never a sibling
          const producer = byScopeName.get(`${reader.parent ?? ""}|${root}`);
          if (!producer || producer.id === reader.id) continue;
          if (fields.length === 0) continue; // a bare `${gen}` names no field
          found.push({ producer, segments: fields });
        }
      }
    }
  }
  return found;
}

/** Merge plain-param `${sibling.field.key}` reads into the observed-read set
 *  (see the call site in buildFlow for the WHY + the deliberate bounds). */
export function scanParamReads(graph: RFGraph, observed: Map<string, Map<string, FieldReads>>): void {
  for (const { producer, segments } of paramTextReads(graph)) {
    const field = segments[0]!;
    const fields = observed.get(producer.id);
    const existing = fields?.get(field);
    // Only correct rows that EXIST (via edges or the authored shape) —
    // a param read must not grow new field rows.
    if (existing == null && field !== producer.output_shape?.field) continue;
    const reads = existing ?? { bare: false, subKeys: [] };
    const subKey = segments[1];
    if (subKey != null) {
      if (!reads.subKeys.includes(subKey)) reads.subKeys.push(subKey);
    } else {
      reads.bare = true;
    }
    const slot = fields ?? new Map<string, FieldReads>();
    slot.set(field, reads);
    observed.set(producer.id, slot);
  }
}

/** Full-depth dotted read paths per producer — the read panel's "consumed" fact.
 *  ONE truth with the canvas rows: contract data-flow edges PLUS the same
 *  param-text scan buildFlow merges — a key consumed only through a prompt body
 *  must list in the panel too, or panel and canvas state contradictory facts
 *  about the same binding (review-caught 2026-06-11). Param reads pass the same
 *  no-new-claims gate as the canvas (a field must exist via an edge read or the
 *  authored shape); unlike the canvas rows (first segment only, D7) the paths
 *  here are untruncated — the panel is the full-depth home. */
export function consumedReadPaths(graph: RFGraph): Map<string, string[]> {
  const paths = new Map<string, string[]>();
  const edgeFields = new Map<string, Set<string>>();
  const add = (producerId: string, path: string): void => {
    const list = paths.get(producerId) ?? [];
    if (!list.includes(path)) list.push(path);
    paths.set(producerId, list);
  };
  for (const e of graph.edges) {
    if (e.kind !== "data_flow" || e.output_field == null) continue;
    const fields = edgeFields.get(e.source) ?? new Set<string>();
    fields.add(e.output_field);
    edgeFields.set(e.source, fields);
    add(e.source, [e.output_field, ...e.output_path].join("."));
  }
  for (const { producer, segments } of paramTextReads(graph)) {
    const field = segments[0]!;
    if (!edgeFields.get(producer.id)?.has(field) && field !== producer.output_shape?.field) continue;
    add(producer.id, segments.join("."));
  }
  return paths;
}
