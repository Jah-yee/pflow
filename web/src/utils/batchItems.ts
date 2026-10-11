// Resolve a batch-host param value that references the batch alias (`${item.x}`)
// against the literal batch items — so the ReadPanel can EXPAND `${item.prompt}`
// into the actual per-item values. The items already ride the /api/graph payload
// inline (file-reference prompts are resolved into the IR before the graph is
// built, so `batch.items[i].prompt` is the file's CONTENT, not its path) — this
// is pure display logic over data already in hand: no fetch, no contract change.
//
// Only LITERAL batches expand: a dynamic batch's `${item.x}` has no static items
// (its source is a runtime ref), so there is nothing to resolve. Pure + node-env
// testable (no React, no DOM).

import { templateTokens, type TemplateToken } from "../graph/scan";
import type { ParamMode } from "../types";
import { fullValue } from "./format";

export interface ResolvedBatchItem {
  /** The item's discriminating scalar fields (those NOT read by the value's
   *  alias refs), e.g. `focus: emotional`; falls back to `item[N]`. */
  label: string;
  /** The param value with every `${alias.path}` ref substituted for THIS item;
   *  non-alias refs (`${content}`) stay verbatim — they are not per-item. A
   *  dict/list value arrives as its `fullValue` text (indented JSON). */
  value: string;
}

// The item path an expression substitutes: a single plain-path operand rooted at the
// alias (`${item.cfg.mode}` → ["cfg", "mode"]), else null — a coalesce, an index or a
// non-alias root is left as written: fail-open, never a wrong substitution. A JSON
// insert substitutes only in embedded code; elsewhere the run keeps it as written.
function aliasPath(token: TemplateToken, alias: string, mode: ParamMode | undefined): string[] | null {
  if (token.kind !== "expression" || token.operands.length !== 1) return null;
  if (token.asJson !== (mode === "embedded")) return null;
  const ref = token.refs[0];
  if (ref?.root !== alias || token.operands[0] !== [alias, ...ref.fields].join(".")) return null;
  return ref.fields;
}

function aliasPaths(leaf: string, alias: string, mode: ParamMode | undefined): string[][] {
  return templateTokens(leaf, mode).flatMap((t) => {
    const path = aliasPath(t, alias, mode);
    return path ? [path] : [];
  });
}

function resolvePath(obj: unknown, segs: string[]): unknown {
  let cur: unknown = obj;
  for (const seg of segs) {
    if (cur == null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[seg];
  }
  return cur;
}

function isScalar(v: unknown): v is string | number | boolean {
  return typeof v === "string" || typeof v === "number" || typeof v === "boolean";
}

// A dict/list param (`env: {GREETING: ${item.greeting}}`) holds its refs in string
// LEAVES; keys are names, never substituted.
function stringLeaves(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(stringLeaves);
  if (value !== null && typeof value === "object") return Object.values(value).flatMap(stringLeaves);
  return [];
}

function mapLeaves(value: unknown, fn: (leaf: string) => string): unknown {
  if (typeof value === "string") return fn(value);
  if (Array.isArray(value)) return value.map((v) => mapLeaves(v, fn));
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, mapLeaves(v, fn)]));
  }
  return value;
}

/** Whether `value` references `${alias…}` in any string leaf (so it resolves per item). */
export function refsBatchAlias(value: unknown, alias: string, mode?: ParamMode): boolean {
  return stringLeaves(value).some((leaf) => aliasPaths(leaf, alias, mode).length > 0);
}

/** The item fields the value reads via the alias (`${item.prompt}` → {"prompt"}). */
function aliasFields(value: unknown, alias: string, mode: ParamMode | undefined): Set<string> {
  const fields = stringLeaves(value).flatMap((leaf) => aliasPaths(leaf, alias, mode).flatMap((path) => path.slice(0, 1)));
  return new Set(fields);
}

/** Head an item by its OTHER short scalar fields — the part that says WHICH
 *  variant this is (the read field is the body, shown below). */
function itemLabel(item: unknown, index: number, readFields: Set<string>): string {
  if (item == null || typeof item !== "object" || Array.isArray(item)) return `item[${index}]`;
  const parts: string[] = [];
  for (const [k, v] of Object.entries(item as Record<string, unknown>)) {
    if (readFields.has(k) || !isScalar(v)) continue;
    const sv = String(v);
    if (sv.length > 60) continue; // a long scalar belongs in the body, not the header
    parts.push(`${k}: ${sv}`);
  }
  return parts.length ? parts.join(", ") : `item[${index}]`;
}

/** Substitute `${alias.path}` refs in `text` with this item's resolved data;
 *  a missing field or a non-alias ref is left verbatim. A JSON insert enters as a
 *  JSON literal (Python's `to_json`); `JSON.stringify` omits the spaces `json.dumps`
 *  writes (`{"a":1}`, not `{"a": 1}`) — a display-only difference. */
function substitute(text: string, alias: string, item: unknown, mode: ParamMode | undefined): string {
  return templateTokens(text, mode)
    .map((token) => {
      const written = text.slice(token.start, token.end);
      const path = aliasPath(token, alias, mode);
      const resolved = path == null ? undefined : resolvePath(item, path);
      if (resolved === undefined) return written;
      return token.kind === "expression" && token.asJson ? JSON.stringify(resolved) : fullValue(resolved);
    })
    .join("");
}

/** The per-item expansion of a batch-alias param value, or `null` when there is
 *  nothing to expand: no string leaf references an alias field, or there are no
 *  literal items (a dynamic batch). A dict/list value substitutes in its leaves and
 *  renders through `fullValue`, as the un-expanded param does. */
export function resolveBatchItems(
  value: unknown,
  alias: string,
  items: readonly unknown[] | null | undefined,
  mode?: ParamMode,
): ResolvedBatchItem[] | null {
  if (!items || items.length === 0) return null;
  if (!refsBatchAlias(value, alias, mode)) return null;
  const readFields = aliasFields(value, alias, mode);
  return items.map((item, i) => ({
    label: itemLabel(item, i, readFields),
    value: fullValue(mapLeaves(value, (leaf) => substitute(leaf, alias, item, mode))),
  }));
}
