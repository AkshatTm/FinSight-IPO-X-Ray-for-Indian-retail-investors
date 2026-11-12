import { beforeEach, describe, expect, it } from "vitest";

import { getItemMigrating, legacyKey } from "./legacyStorage";

describe("legacyStorage", () => {
  beforeEach(() => localStorage.clear());

  it("maps vd_ keys to their old fs_ names", () => {
    expect(legacyKey("vd_ui")).toBe("fs_ui");
    expect(legacyKey("other")).toBe("other");
  });

  it("migrates a value saved under the old key", () => {
    localStorage.setItem("fs_ui", '{"state":{"theme":"dark"}}');
    expect(getItemMigrating(localStorage, "vd_ui")).toBe('{"state":{"theme":"dark"}}');
    expect(localStorage.getItem("vd_ui")).toBe('{"state":{"theme":"dark"}}');
    expect(localStorage.getItem("fs_ui")).toBeNull();
  });

  it("prefers the new key and returns null when neither exists", () => {
    localStorage.setItem("fs_ui", "old");
    localStorage.setItem("vd_ui", "new");
    expect(getItemMigrating(localStorage, "vd_ui")).toBe("new");
    expect(getItemMigrating(localStorage, "vd_missing")).toBeNull();
  });
});
