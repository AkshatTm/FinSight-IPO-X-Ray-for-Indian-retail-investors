import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { SAMPLE_DOC_ID } from "@/mocks/report";
import { ATHER_RHP_DOC_ID, MOCK_SAMPLE_DOC_ID } from "./showcase";

describe("sample report link", () => {
  it("points at the Ather RHP in configs/demo_ipos.yaml and at the mock sample report", () => {
    const config = readFileSync(resolve(__dirname, "../../configs/demo_ipos.yaml"), "utf-8");
    const ather = config.split("- ipo_id: ").find((block) => block.startsWith("ather-energy-2025"));
    expect(ather).toMatch(new RegExp(`rhp: \\{doc_id: ${ATHER_RHP_DOC_ID},`));
    expect(MOCK_SAMPLE_DOC_ID).toBe(SAMPLE_DOC_ID);
  });
});
