// @vitest-environment jsdom
// A canvas param row's value: one chip per pflow reference, read in the param's mode —
// embedded code (an MCP tool's JavaScript) chips only its `${x|json}` inserts.

import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ParamMode } from "../../types";
import { ParamValue } from "./WorkflowNode";

afterEach(cleanup);

const chips = (value: string, mode?: ParamMode): string[] => {
  const { container } = render(<ParamValue param={{ name: "function", value, is_dynamic: true, source: null, mode }} />);
  const found = [...container.querySelectorAll(".ref-chip")].map((el) => el.textContent ?? "");
  cleanup();
  return found;
};

describe("ParamValue chips", () => {
  const fn = "() => [${up.stdout|json}, `${a + b}`, ${user.name}, `$${price}`]";

  it("embedded code chips only the insert; the same text as a Template chips the bare reference too", () => {
    expect(chips(fn, "embedded")).toEqual(["up.stdout|json"]);
    expect(chips(fn, "template")).toEqual(["up.stdout|json", "user.name"]);
  });

  it("an escape is never a chip (#683)", () => {
    expect(chips("$${x} and ${x}")).toEqual(["x"]);
  });

  // W2: the row tokenizes the value as written, then collapses the text it shows. A raw TAB
  // inside a quoted literal is not a pflow literal (an Issue); collapsed first, it would be.
  it("a raw whitespace control inside a quoted literal is no chip; the same text with a space is", () => {
    expect(chips('${up.stdout ?? "a\tb"}')).toEqual([]);
    expect(chips('${up.stdout ?? "a b"}')).toEqual(['up.stdout ?? "a b"']);
  });

  it("the text around a chip still collapses to one line", () => {
    const { container } = render(<ParamValue param={{ name: "prompt", value: "\n Say\n\n  hi to ${user.name}\tnow\n", is_dynamic: true, source: null }} />);
    expect([...container.querySelectorAll(".lit")].map((el) => el.textContent)).toEqual(["Say hi to ", " now"]);
  });
});
