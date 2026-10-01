// MOCK DATA for development and component tests only (NEXT_PUBLIC_USE_MOCKS=1).
// Shapes come from the generated API types. Amounts here are placeholders chosen to exercise
// every display state; they are not read from any document and must never appear in the demo.
import type { Schemas } from "@/lib/api/client";

type Ipo = Schemas["IpoSummary"];
type Detail = Schemas["IpoDetail"];

const CR = (n: number) => (BigInt(n) * BigInt(10000000)).toString(); // crore -> full rupees

export const IPOS: Ipo[] = [
  { id: "ather-energy-2025", company: "Ather Energy Limited", sector: "Electric vehicles", listing_date: "2025-05-06", rhp_pages: 586, issue_size_inr: CR(2981), fresh_inr: CR(2626), ofs_inr: CR(355), xray_status: "ready" },
  { id: "groww-2025", company: "Billionbrains Garage Ventures Limited", sector: "Financial services", listing_date: "2025-11-12", rhp_pages: 568, issue_size_inr: CR(6632), fresh_inr: CR(1060), ofs_inr: CR(5572), xray_status: "ready" },
  { id: "hdb-financial-services-2025", company: "HDB Financial Services Limited", sector: "Financial services", listing_date: "2025-07-02", rhp_pages: 758, issue_size_inr: CR(12500), fresh_inr: CR(2500), ofs_inr: CR(10000), xray_status: "ready" },
  { id: "hexaware-technologies-2025", company: "Hexaware Technologies Limited", sector: "Information technology", listing_date: "2025-02-19", rhp_pages: 644, issue_size_inr: CR(8750), fresh_inr: null, ofs_inr: CR(8750), xray_status: "ready" },
  { id: "lenskart-2025", company: "Lenskart Solutions Limited", sector: "Retail", listing_date: "2025-11-10", rhp_pages: 1083, issue_size_inr: CR(7278), fresh_inr: CR(2150), ofs_inr: CR(5128), xray_status: "ready" },
  { id: "lg-electronics-india-2025", company: "LG Electronics India Limited", sector: "Consumer durables", listing_date: "2025-10-14", rhp_pages: 502, issue_size_inr: CR(11607), fresh_inr: null, ofs_inr: CR(11607), xray_status: "ready" },
  { id: "meesho-2025", company: "Meesho Limited", sector: "E-commerce", listing_date: "2025-12-10", rhp_pages: 689, issue_size_inr: CR(5421), fresh_inr: CR(4250), ofs_inr: CR(1171), xray_status: "ready" },
  { id: "physicswallah-2025", company: "PhysicsWallah Limited", sector: "Education", listing_date: "2025-11-18", rhp_pages: 669, issue_size_inr: CR(3480), fresh_inr: CR(3100), ofs_inr: CR(380), xray_status: "ready" },
  { id: "tata-capital-2025", company: "Tata Capital Limited", sector: "Financial services", listing_date: "2025-10-13", rhp_pages: 836, issue_size_inr: CR(15512), fresh_inr: CR(6846), ofs_inr: CR(8666), xray_status: "ready" },
  { id: "urban-company-2025", company: "Urban Company Limited", sector: "Consumer services", listing_date: "2025-09-17", rhp_pages: 577, issue_size_inr: CR(1900), fresh_inr: CR(472), ofs_inr: CR(1428), xray_status: "building" },
];

export const DETAILS: Record<string, Detail> = Object.fromEntries(
  IPOS.map((i) => [
    i.id,
    {
      id: i.id,
      company: i.company,
      rhp_pages: i.rhp_pages,
      prospectus_pages: i.rhp_pages,
      page_size: { width: 595, height: 842 },
      sections: [
        { id: "cover", doc: "rhp", title: "Cover page", start_page: 1, end_page: 6 },
        { id: "the_offer", doc: "rhp", title: "The offer", start_page: 60, end_page: 66 },
        { id: "capital_structure", doc: "rhp", title: "Share capital", start_page: 90, end_page: 110 },
        { id: "objects_of_the_offer", doc: "rhp", title: "Objects of the offer", start_page: 120, end_page: 140 },
      ],
    } satisfies Detail,
  ]),
);

export const HEALTH: Schemas["HealthResponse"] = {
  status: "ok",
  profile: "dev_light",
  demo_mode: false,
  models: {},
  version: "mock",
  git_sha: null,
};
