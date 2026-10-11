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
});
