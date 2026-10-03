// The sample report behind "Explore a sample report" (B05 §2): the Ather Energy RHP, whose doc_id
// is in configs/demo_ipos.yaml. With mocks on, the synthetic sample report from mocks/report.ts.
import { USE_MOCKS } from "@/lib/api/client";

export const ATHER_RHP_DOC_ID = "doc_b0bcc33896944ebd";
export const MOCK_SAMPLE_DOC_ID = "doc_5a3f1e2b9c7d4a60";
export const SAMPLE_REPORT_DOC_ID = USE_MOCKS ? MOCK_SAMPLE_DOC_ID : ATHER_RHP_DOC_ID;
