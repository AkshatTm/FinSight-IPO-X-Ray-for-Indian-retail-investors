import type { Schemas } from "@/lib/api/client";

export type XField = Schemas["XRayField"];
export type XValue = NonNullable<XField["value"]>;

export interface Resolved {
  /** The value to show: the RHP value, or the Prospectus value when the RHP leaves it blank. */
  value: XValue | null;
  doc: "rhp" | "prospectus";
  page: number;
  /** True when the RHP has `[●]` and the value comes from the final prospectus. */
  filledInProspectus: boolean;
  /** True when the RHP value is blank and no prospectus value exists. */
  blank: boolean;
  /** True when the field is not in the document at all (e.g. no fresh issue). */
  notInDocument: boolean;
}

/** Spec section 12: placeholder rows prefer the prospectus value, with a note. */
export function resolveField(f: XField): Resolved {
  const notInDocument = f.reason_code === "not_in_document" || (f.value == null && f.reason_code !== "placeholder");
  if (f.value?.kind === "placeholder") {
    if (f.companion?.value && f.companion.value.kind !== "placeholder") {
      return { value: f.companion.value, doc: f.companion.doc, page: f.companion.page, filledInProspectus: true, blank: false, notInDocument: false };
    }
    return { value: f.value, doc: f.doc, page: f.page, filledInProspectus: false, blank: true, notInDocument: false };
  }
  return { value: f.value ?? null, doc: f.doc, page: f.page, filledInProspectus: false, blank: false, notInDocument };
}

export const fieldById = (fields: XField[], id: string) => fields.find((f) => f.field_id === id);
