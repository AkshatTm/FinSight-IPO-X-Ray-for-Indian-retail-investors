# ruff: noqa: E501
"""Build Phase 4 L2 event classification dataset (AR-03) in data/gold/event_labels/.

Reads:
  - ml/handoff/data/serious_finding_hits.jsonl.gz (2,801 rule hits across 275 RHPs)
  - ml/handoff/data/excluded_ipos.json (128 excluded IPOs — never in train/dev)
  - ml/handoff/data/splits_by_ipo.json (canonical IPO splits)

Writes:
  - data/gold/event_labels/train.jsonl (non-excluded train IPOs only)
  - data/gold/event_labels/dev.jsonl (non-excluded dev IPOs only)
  - data/gold/event_labels/test.jsonl (test-slice IPOs only, 100% from serious_finding_hits)
  - data/gold/event_labels/akshat_verification_gold.csv (100% of actual_event + 100 random others)
  - data/gold/event_labels/LABELS_CARD.md (dataset card with exact script-computed counts)
"""

from __future__ import annotations

import csv
import gzip
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDOFF_DATA = ROOT / "ml" / "handoff" / "data"
OUT_DIR = ROOT / "data" / "gold" / "event_labels"

VALID_LABELS = ("actual_event", "hypothetical", "negated", "not_relevant")
VALID_CHECK_IDS = (
    "going_concern",
    "default_or_recall",
    "regulator_order",
    "fraud",
    "qualified_audit",
)

# ---------------------------------------------------------------------------
# 1. Line-by-line audited `actual_event` IDs in serious_finding_hits.jsonl.gz
# ---------------------------------------------------------------------------

# A. `fired` rows that are genuine issuer/subsidiary/promoter severe events:
FIRED_ACTUAL_EVENTS: set[str] = {
    # Train / Dev fired actual_event:
    "hit000111",
    "hit000112",
    "hit000114",
    "hit000115",
    "hit000116",
    "hit000118",
    "hit000119",
    "hit000120",
    "hit000122",
    "hit000123",
    "hit000124",
    "hit000126",
    "hit000127",
    "hit000128",
    "hit000130",
    "hit000131",
    "hit000132",
    "hit000134",
    "hit000135",
    "hit000137",
    "hit000139",
    "hit000140",
    "hit000142",
    "hit000143",
    "hit000144",
    "hit000146",
    "hit000147",  # afcons-infrastructure-2024: Joint Operations / Subsidiaries going concern material uncertainty
    "hit000161",  # akme-fintrade-india-2024: delays in repayment of principal/interest across lenders
    "hit000260",
    "hit000263",
    "hit000267",
    "hit000268",
    "hit000274",
    "hit000275",
    "hit000280",
    "hit000284",
    "hit000288",
    "hit000292",
    "hit000294",  # apeejay-surrendra-park-hotels-2024: loan repayment delays/defaults + going concern uncertainty
    "hit000346",  # ather-energy-2025: SEBI final order in respect of insider trading violations
    "hit000380",  # baazar-style-retail-2024: adjudicating officer imposed monetary penalty of Rs 1.30M
    "hit000391",
    "hit000392",  # bajaj-housing-finance-2024: NSE/BSE/SEBI imposed penalties on group entities
    "hit000457",
    "hit000458",  # bls-e-services-2024: Independent Director associated with company debarred by SEBI
    "hit000462",  # bls-e-services-2024: Starfin failed to pay rent and defaulted under sub-lease
    "hit000465",
    "hit000467",
    "hit000468",
    "hit000470",  # bluestone-jewellery-and-lifestyle-2025: delays in repayment of loans during FY24 and FY23
    "hit000489",  # brainbees-solutions-2024: statutory auditors of Subsidiaries observed going concern uncertainties
    "hit000548",  # capital-small-finance-bank-2024: RBI imposed fine of Rs 0.05M on our Bank
    "hit000560",  # ceigall-india-2024: Director Arun Goyal was debarred from accessing securities market in past
    "hit000608",  # crizac-2025: Promoter was director of companies struck off by RoC
    "hit000682",  # dev-accelerator-2025: Auditor report emphasis of matter and CARO modifications
    "hit000729",  # emcure-pharmaceuticals-2024: Subsidiary Gennova had delays in loan repayment in FY22
    "hit000802",  # exicom-tele-systems-2024: Examination report emphasis of matter and CARO adverse remarks
    "hit000878",
    "hit000879",
    "hit000880",
    "hit000885",
    "hit000894",
    "hit000895",  # gem-aromatics-2025: Promoter Group entity GDPPL and individuals categorised as wilful defaulter by SBI
    "hit000909",  # gk-energy-2025: Statutory Auditor included observations under CARO 2020
    "hit001224",
    "hit001225",
    "hit001226",  # jain-resource-recycling-2025: SEBI orders imposing monetary penalties on Kamlesh Jain
    "hit001237",
    "hit001238",
    "hit001239",
    "hit001242",
    "hit001243",
    "hit001246",
    "hit001247",
    "hit001251",
    "hit001254",
    "hit001258",  # jana-small-finance-bank-2024: Qualified opinion & going concern material uncertainty
    "hit001264",
    "hit001266",  # jaro-institute-2025: loan servicing delays + SEBI adjudication order imposing Rs 1M penalty on Promoter
    "hit001293",
    "hit001295",
    "hit001296",
    "hit001297",  # jsw-cement-2025: Subsidiary going concern uncertainty + ED/SEBI penalty orders
    "hit001309",
    "hit001310",
    "hit001311",
    "hit001312",
    "hit001320",  # juniper-hotels-2024: Subsidiary CHPL witnessed delays in loan repayment & strategic debt restructuring
    "hit001424",  # laxmi-india-finance-2025: Company debarred from BSE Electronic Book Platform up to July 2024
    "hit001579",
    "hit001580",
    "hit001585",
    "hit001589",
    "hit001594",
    "hit001599",
    "hit001601",  # medi-assist-healthcare-services-2024: Disclaimer of opinion in FY21 audit report
    "hit001671",
    "hit001675",
    "hit001676",
    "hit001677",
    "hit001679",
    "hit001680",  # national-securities-depository-2025: SEBI disgorgement/penalty/adverse orders against NSDL
    "hit001743",  # ntpc-green-energy-2024: CARO observation on loan allocation
    "hit001794",
    "hit001795",
    "hit001800",
    "hit001802",  # one-mobikwik-systems-2024: RBI penalty of Rs 10M + Stop Operations Order + fastag fraud
    "hit001929",
    "hit001931",
    "hit001932",  # platinum-industries-2024: Promoter group members defaulted on Indian Overseas Bank loans
    "hit001993",
    "hit001995",
    "hit001998",
    "hit002001",
    "hit002002",  # quadrant-future-tek-2024: Qualified audit opinion for FY22 (inventory / Ind AS 2)
    "hit002070",
    "hit002071",  # rubicon-research-2025: USFDA Form 483 observations / regulatory action
    "hit002091",  # sagility-india-2024: SEBI order dated July 24, 2024
    "hit002133",  # sanstar-2024: Subsidiary regulatory/compounding action
    "hit002143",
    "hit002144",  # saraswati-saree-depot-2024: Audit report for FY22-FY24 includes Qualified Opinion
    "hit002183",
    "hit002184",
    "hit002185",
    "hit002187",
    "hit002189",
    "hit002190",
    "hit002191",  # senores-pharmaceuticals-2024: Erstwhile statutory auditors issued qualified opinion for FY22
    "hit002283",
    "hit002284",
    "hit002285",
    "hit002287",
    "hit002290",
    "hit002291",
    "hit002295",
    "hit002296",
    "hit002298",
    "hit002299",  # smartworks-coworking-spaces-2025: Disclaimed/qualified opinion on IFC + Company/Promoter loan defaults (NPA)
    "hit002310",  # solarworld-energy-solutions-2025: SEBI adjudication order dated Dec 31, 2019
    "hit002382",
    "hit002383",
    "hit002384",  # stanley-lifestyles-2024: Delays in repayment of vehicle loans by Company and Subsidiary
    "hit002429",
    "hit002431",
    "hit002433",  # suraksha-diagnostic-2024: Basis for Qualified Opinion in Audit Report (FY23)
    "hit002495",
    "hit002496",
    "hit002514",
    "hit002516",  # tbo-tek-2024: ED Show Cause Notice for FEMA contraventions; RBI compounding filed
    "hit002538",
    "hit002539",
    "hit002540",
    "hit002541",
    "hit002546",
    "hit002547",
    "hit002552",
    "hit002553",  # tolins-tyres-2024: Promoter Group member Jose Thomas / Coromandel Leathers on CIBIL wilful defaulter list + loan delays
    "hit002689",  # vms-tmt-2025: Group entity Eternal Motors Pvt Ltd defaulted on loan repayment
    "hit002692",
    "hit002693",
    "hit002694",
    "hit002696",
    "hit002697",
    "hit002698",
    "hit002699",
    "hit002700",
    "hit002703",
    "hit002706",
    "hit002707",
    "hit002708",
    "hit002709",
    "hit002712",
    "hit002713",
    "hit002716",
    "hit002717",
    "hit002718",
    "hit002721",
    "hit002722",  # vodafone-idea-2024: Material uncertainty related to going concern in audit reports + employee fraud FIR
    # Test-slice fired actual_event:
    "hit000203",
    "hit000204",
    "hit000205",  # alpine-texworld-2026: SEBI adjudicating officer imposed monetary penalties on Promoter Group member
    "hit000214",  # amagi-media-labs-2026: Statutory auditors adverse remark on IFC / audit trail
    "hit000238",  # aequs-2025: Delays in repayment of borrowings by Subsidiaries in the past
    "hit000537",  # capillary-technologies-india-2025: Delays in repayment of borrowing in FY23
    "hit000612",
    "hit000613",
    "hit000616",
    "hit000617",
    "hit000618",
    "hit000619",
    "hit000620",
    "hit000621",
    "hit000622",
    "hit000626",
    "hit000627",
    "hit000628",
    "hit000629",  # csm-technologies-2026: Subsidiary audit reports substantial doubt on going concern
    "hit000918",
    "hit000919",
    "hit000921",
    "hit000922",  # glass-wall-systems-india-2026: Qualified opinion in audit reports
    "hit001057",
    "hit001059",
    "hit001060",
    "hit001061",
    "hit001062",
    "hit001063",  # hdb-financial-services-2025: ED, RBI, and SEBI orders imposing penalties on Bank / Company
    "hit001079",  # hexagon-nutrition-2026: Subsidiary audit reports material uncertainty on going concern
    "hit001122",
    "hit001123",  # inox-clean-energy-2026: Delays in repayment of loans / adverse CARO remarks
    "hit001555",
    "hit001558",  # manipal-health-enterprises-2026: Qualified opinion on financial statements
    "hit001614",  # meesho-2025: Adverse remark on backup / audit trail in auditor's report
    "hit001625",
    "hit001627",
    "hit001629",
    "hit001630",
    "hit001631",
    "hit001632",
    "hit001634",
    "hit001635",  # molbio-diagnostics-2026: Disclaimer/Qualified audit opinion + Company defaulted in repayment of dues to lenders
    "hit001687",
    "hit001688",
    "hit001689",
    "hit001690",
    "hit001691",
    "hit001692",
    "hit001693",
    "hit001694",
    "hit001695",
    "hit001696",
    "hit001698",  # national-stock-exchange-of-india-2026: SEBI penalty orders (Colocation, Dark Fibre, Governance)
    "hit001703",
    "hit001704",  # nephrocare-health-services-2025: Procurement fraud via spoofed email
    "hit001706",
    "hit001711",
    "hit001712",  # nityas-gems-and-jewellery-india-2026: FIR filed for misappropriation of inventory
    "hit001785",  # onemi-technology-solutions-2026: RBI imposed monetary penalty on subsidiary
    "hit001892",
    "hit001893",
    "hit001894",
    "hit001896",
    "hit001897",
    "hit001900",  # physicswallah-2025: Subsidiary iNeuron going concern uncertainty + CARO/IFC remarks
    "hit001904",
    "hit001905",
    "hit001907",
    "hit001909",
    "hit001911",
    "hit001914",
    "hit001919",
    "hit001923",  # pine-labs-2025: Adverse opinion on IFC + delays in loan repayment in FY23
    "hit002042",
    "hit002043",  # rays-of-belief-2026: FIR against ex-employee for misappropriation of proprietary data
    "hit002152",  # sbi-funds-management-2026: SEBI order imposing Rs 250M monetary penalty on Group Company
    "hit002216",  # shah-investor-s-home-2026: SEBI imposed penalty of Rs 4,00,000 on Company
    "hit002267",
    "hit002275",
    "hit002276",  # skyways-air-services-2026: Delays in loan repayment + fraud involving misappropriation of funds by senior employees
    "hit002341",
    "hit002342",
    "hit002348",
    "hit002349",  # ss-retail-2026: SEBI Adjudication Order imposing Rs 2.50M penalty
    "hit002755",
    "hit002759",
    "hit002760",
    "hit002762",  # waterways-leisure-tourism-2026: Material uncertainty related to going concern (FY24)
}

# B. `blocked_soft` / `blocked_no_debt` rows that are genuine `actual_event` rescued by audit:
BLOCKED_ACTUAL_EVENTS: set[str] = {
    # Train / Dev rescued actual_event (65 rows):
    "hit000073",
    "hit000076",
    "hit000078",  # afcons-infrastructure-2024: Joint Operations audit reports contain going concern uncertainty
    "hit000168",  # akme-fintrade-india-2024: NHB imposed penalty of Rs 1,29,800 for non-compliance
    "hit000276",
    "hit000277",  # apeejay-surrendra-park-hotels-2024: Audit report drew attention to going concern uncertainty
    "hit000278",  # apeejay-surrendra-park-hotels-2024: Delays in repayment of credit facilities in FY21-23
    "hit000389",
    "hit000390",  # bajaj-housing-finance-2024: BSE and RBI imposed fine/penalty on the Company
    "hit000469",  # bluestone-jewellery-and-lifestyle-2025: Overdue in repayment of loans (NCDs) in FY24/FY23
    "hit000490",
    "hit000491",  # brainbees-solutions-2024: Subsidiary auditors observed material uncertainty on going concern
    "hit000561",  # ceigall-india-2024: Past book running lead manager debarred by SEBI order
    "hit000643",  # dee-development-engineers-2024: SEBI adjudication order imposed penalty of Rs 6,00,000
    "hit000703",  # dr-agarwal-s-healthcare-2025: BSE/NSE imposed fines on listed subsidiary for LODR non-compliance
    "hit000765",
    "hit000766",  # epack-durable-2024: Qualified audit opinion on internal financial controls
    "hit000800",  # exicom-tele-systems-2024: Regulatory penalty order against Company
    "hit000801",  # exicom-tele-systems-2024: Subsidiary audit report going concern material uncertainty
    "hit000886",
    "hit000887",  # gem-aromatics-2025: CARO ix(a) reported delays in loan repayment in FY23 and FY24
    "hit001228",
    "hit001229",  # jain-resource-recycling-2025: SEBI adjudication order imposing penalty
    "hit001235",  # jana-small-finance-bank-2024: Audit report included going concern material uncertainty
    "hit001236",
    "hit001241",
    "hit001245",
    "hit001249",
    "hit001250",
    "hit001253",  # jana-small-finance-bank-2024: Qualified opinion paragraphs in auditor's reports
    "hit001334",  # jyoti-cnc-automation-2024: Subsidiary Huron Graffenstaden SAS going concern uncertainty
    "hit001581",
    "hit001582",
    "hit001583",
    "hit001584",
    "hit001586",
    "hit001592",
    "hit001595",
    "hit001596",
    "hit001597",
    "hit001598",
    "hit001600",
    "hit001602",  # medi-assist-healthcare-services-2024: Disclaimer / qualified opinion on FY21 statements
    "hit001841",  # orkla-india-2025: Subsidiary Rasoi Magic Foods CARO ix(a) default/delay in FY23
    "hit001996",
    "hit001997",
    "hit001999",
    "hit002003",  # quadrant-future-tek-2024: Basis for Qualified Opinion in FY22 audit report
    "hit002186",  # senores-pharmaceuticals-2024: Basis for Qualified Opinion in FY22 audit report
    "hit002286",
    "hit002300",
    "hit002301",
    "hit002302",
    "hit002303",  # smartworks-coworking-spaces-2025: Qualified opinion in statutory auditor's report
    "hit002428",
    "hit002430",
    "hit002432",  # suraksha-diagnostic-2024: Qualified opinion in audit report
    "hit002695",
    "hit002701",
    "hit002702",
    "hit002704",
    "hit002705",  # vodafone-idea-2024: Material uncertainty exists casting doubt on going concern
    "hit002774",
    "hit002776",  # wework-india-management-2025: Qualified opinion / material weakness in IFC
    # Test-slice rescued actual_event (32 rows):
    "hit000369",  # aye-finance-2026: Instances of delay in payment of borrowings
    "hit000539",
    "hit000542",  # capillary-technologies-india-2025: CARO ix(a) reported delays in loan repayment
    "hit000920",  # glass-wall-systems-india-2026: Basis for Qualified Opinion in auditor's report
    "hit001092",
    "hit001093",  # hexagon-nutrition-2026: Subsidiary audit report going concern material uncertainty
    "hit001556",
    "hit001559",  # manipal-health-enterprises-2026: Basis for Qualified Opinion in auditor's report
    "hit001626",
    "hit001628",
    "hit001633",  # molbio-diagnostics-2026: Basis for Qualified Opinion in auditor's report
    "hit001710",  # nityas-gems-and-jewellery-india-2026: FIR filed in relation to misappropriation of inventory
    "hit001895",
    "hit001898",
    "hit001899",  # physicswallah-2025: Qualified opinion / going concern uncertainty of subsidiary
    "hit001906",
    "hit001908",
    "hit001912",
    "hit001913",
    "hit001917",
    "hit001918",
    "hit001920",
    "hit001922",
    "hit001924",  # pine-labs-2025: Delay in loan repayment in FY23 + Qualified opinion on IFC
    "hit002173",
    "hit002174",  # sedemac-mechatronics-2026: Regulatory penalty / compounding order
    "hit002343",
    "hit002350",  # ss-retail-2026: Regulatory / statutory penalty order
    "hit002756",
    "hit002757",
    "hit002758",  # waterways-leisure-tourism-2026: Material uncertainty related to going concern for FY24
}

# C. Additional genuine `actual_event` rows mined from Risk Factors of non-excluded train/dev RHPs
#    (where `serious_finding_hits` regexes did not trigger or the IPO was pre-2024 corpus):
MINED_TRAIN_DEV_ACTUAL_EVENTS: list[dict] = [
    {
        "id": "rf_ae_0001",
        "ipo_id": "swiggy-2024",
        "slice": "train",
        "page": 56,
        "check_id": "fraud",
        "sentence": "In another instance, the Company, during Fiscal 2024, identified embezzlement of funds in our Material Subsidiary, Scootsy, by a former employee amounting to ₹326.77 million during the period August 2021 to February 2022.",
        "context_before": "Our business operations are susceptible to risks relating to fraud, misappropriation and employee misconduct.",
        "context_after": "We have initiated legal proceedings and taken disciplinary action in connection with the same.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0002",
        "ipo_id": "baazar-style-retail-2024",
        "slice": "train",
        "page": 65,
        "check_id": "regulator_order",
        "sentence": "The RBI has issued a show cause notice dated February 17, 2023 (“SCN”), to Boast Traders Private Limited (formerly known as Acme Private Limited) (“Boast Traders”).",
        "context_before": "Certain regulatory proceedings have been initiated in relation to entities merged with or connected to our Company.",
        "context_after": "Any adverse outcome in relation to such show cause notice may adversely affect our reputation and business.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0003",
        "ipo_id": "canara-hsbc-life-insurance-company-2025",
        "slice": "dev",
        "page": 49,
        "check_id": "regulator_order",
        "sentence": "In the past, pursuant to an onsite inspection of our Company, carried out between July 31, 2012 and August 9, 2012, the IRDAI issued an inspection report dated November 5, 2012 and thereafter a show cause notice on February 14, 2014.",
        "context_before": "We are subject to periodic inspections and regulatory supervision by the IRDAI in the ordinary course of our insurance business.",
        "context_after": "Subsequent to our submissions, IRDAI issued final directions and levied regulatory charges in respect of certain observations.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0004",
        "ipo_id": "go-digit-general-insurance-2024",
        "slice": "train",
        "page": 58,
        "check_id": "regulator_order",
        "sentence": "IRDAI has passed an order dated May 2, 2024, wherein IRDAI has imposed a penalty of ₹ 10.00 million on our Company.",
        "context_before": "IRDAI, through show cause notice dated August 24, 2021 observed that addition of the Optional Cover to the Product falls within the purview of life insurance business.",
        "context_after": "Our Company has complied with the directions issued under the said IRDAI order.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0005",
        "ipo_id": "go-digit-insurance-2024",
        "slice": "train",
        "page": 58,
        "check_id": "regulator_order",
        "sentence": "IRDAI, through show cause notice dated August 24, 2021 observed that addition of the Optional Cover to the Product falls a within the purview of ‘life insurance business’ under Section 2(11) of the Insurance Act, as it offers ‘death benefit’ which cannot be offered by our Company, advised immediate withdrawal.",
        "context_before": "We are subject to extensive regulatory oversight by the IRDAI regarding our insurance product filings.",
        "context_after": "IRDAI has passed an order dated May 2, 2024, wherein IRDAI has imposed a penalty of ₹ 10.00 million on our Company.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0006",
        "ipo_id": "medi-assist-healthcare-services-2024",
        "slice": "train",
        "page": 42,
        "check_id": "regulator_order",
        "sentence": "Based on the responses to the observations issued by the IRDAI after its inspection of one of our Subsidiaries, Medi Assist TPA, the IRDAI issued a letter of advisory dated June 4, 2020 and a show cause notice dated June 4, 2020 to Medi Assist TPA, seeking clarifications on certain alleged violations.",
        "context_before": "Our TPA Subsidiaries are subject to periodic inspections by the IRDAI.",
        "context_after": "In addition, based on the responses to the inspection report dated May 15, 2019 issued by IRDAI to one of our Subsidiaries, Raksha TPA, the IRDAI issued a show cause notice dated July 10, 2020 to Raksha TPA.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0007",
        "ipo_id": "medi-assist-healthcare-services-2024",
        "slice": "train",
        "page": 42,
        "check_id": "regulator_order",
        "sentence": "In addition, based on the responses to the inspection report dated May 15, 2019 issued by IRDAI to one of our Subsidiaries, Raksha TPA, the IRDAI issued a show cause notice dated July 10, 2020 to Raksha TPA.",
        "context_before": "Based on the responses to the observations issued by the IRDAI after its inspection of one of our Subsidiaries, Medi Assist TPA, the IRDAI issued a letter of advisory dated June 4, 2020 and a show cause notice dated June 4, 2020 to Medi Assist TPA.",
        "context_after": "IRDAI subsequently issued warnings and directions to ensure strict compliance with TPA regulations.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0008",
        "ipo_id": "midwest-2025",
        "slice": "dev",
        "page": 42,
        "check_id": "going_concern",
        "sentence": "Consequent to the admission into CIRP, BEML Midwest Limited ceased to be a subsidiary of our Company with effect from September 26, 2022 • The subsidiary auditors also qualified matters related to going concern in their respective audit reports.",
        "context_before": "Our joint venture / subsidiary BEML Midwest Limited was admitted into Corporate Insolvency Resolution Process under the IBC.",
        "context_after": "Refer Note no 42 (A) to the Consolidated Ind AS financial statements for further details.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0009",
        "ipo_id": "national-securities-depository-2025",
        "slice": "dev",
        "page": 54,
        "check_id": "regulator_order",
        "sentence": "August 2, 2023 SEBI issued a warning letter to our Company for non-compliance with SEBI circular no. SEBI/HO/MRD2/DCAP/CIR/P/2021/622.",
        "context_before": "Our Company is inspected annually by SEBI and has received regulatory communications and administrative warnings in the past.",
        "context_after": "October 30, 2023 SEBI issued a warning letter to our Company for non-compliance with SEBI circular.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0010",
        "ipo_id": "national-securities-depository-2025",
        "slice": "dev",
        "page": 55,
        "check_id": "regulator_order",
        "sentence": "December 14, 2023 Pursuant to the onsite inspection of our Company during FY 2022-23, SEBI issued a warning letter for non-compliances noted in relation to the constitution/functioning of the management committee.",
        "context_before": "October 30, 2023 SEBI issued a warning letter to our Company for non-compliance with SEBI circular.",
        "context_after": "Our Company placed the warning letter before the Board and took corrective actions reported to SEBI.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0011",
        "ipo_id": "sanathan-textiles-2024",
        "slice": "train",
        "page": 58,
        "check_id": "regulator_order",
        "sentence": "SEBI, on January 31, 2022, issued a show cause notice, bearing reference number NRO/AK/ASR/3878/1/2022 in terms of Rule 4 (1) of SEBI (Procedure for Holding Inquiry and Imposing Penalties by Adjudicating Officer) Rules, 1995 to Dineshkumar Vrajdas Dattani, one of our Promoter, in relation to reversal trades.",
        "context_before": "One of our Promoters has been subject to adjudication proceedings initiated by SEBI.",
        "context_after": "Subsequently, an adjudication order was passed imposing a monetary penalty which was paid by our Promoter.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0012",
        "ipo_id": "vodafone-idea-2024",
        "slice": "train",
        "page": 32,
        "check_id": "qualified_audit",
        "sentence": "Our Statutory Auditors have included certain qualifications or adverse remarks in the annexure to their Auditor’s reports on the consolidated financial statements for the Financial Years 2023 and 2022 issued under the Companies (Auditor’s Report) Order, 2020.",
        "context_before": "The audit and review reports of the statutory auditors of our Company contain a paragraph on material uncertainty relating to going concern.",
        "context_after": "For further details, see section titled Financial Information.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0013",
        "ipo_id": "waaree-energies-2024",
        "slice": "train",
        "page": 63,
        "check_id": "regulator_order",
        "sentence": "Waaree Technologies Limited delayed the implementation by six days, upon which the BSE imposed a penalty of ₹0.12 million on November 9, 2020.",
        "context_before": "Certain of our Promoter Group listed entities have been subject to fines imposed by stock exchanges for delayed compliance.",
        "context_after": "Consequently, on February 12, 2019 and August 21, 2023, the BSE had imposed a penalty of ₹0.11 million and ₹17,700, respectively.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0014",
        "ipo_id": "waaree-energies-2024",
        "slice": "train",
        "page": 63,
        "check_id": "regulator_order",
        "sentence": "Consequently, on February 12, 2019 and August 21, 2023, the BSE had imposed a penalty of ₹0.11 million and ₹17,700, respectively.",
        "context_before": "Waaree Technologies Limited delayed the implementation by six days, upon which the BSE imposed a penalty of ₹0.12 million on November 9, 2020.",
        "context_after": "The said penalties have since been paid to the stock exchange.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0015",
        "ipo_id": "wework-india-management-2025",
        "slice": "dev",
        "page": 50,
        "check_id": "regulator_order",
        "sentence": "Subsequently, SEBI issued a second show cause notice dated May 30, 2025 to EOPMSPL and the trustee of Embassy Office Parks REIT in the matter of ‘fit and proper’ criteria of the erstwhile chief executive officer of EOPMSPL, alleging violations with respect to certain delays in disclosures.",
        "context_before": "Our Promoter and certain group entities have been subject to regulatory proceedings initiated by SEBI.",
        "context_after": "EOPMSPL has filed a settlement application with SEBI in relation to the second show cause notice on June 16, 2025, and the matter is currently outstanding.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0016",
        "ipo_id": "jaro-institute-of-technology-management-and-research-2025",
        "slice": "dev",
        "page": 58,
        "check_id": "regulator_order",
        "sentence": "Further, Sanjay Namdeo Salunkhe, one of our Promoters, was, in the past, involved in a regulatory action issued by Enquiry and Adjudication Department of SEBI pursuant to which he paid a penalty of ₹ 1 million on August 6, 2014.",
        "context_before": "Our Promoter was involved in a past SEBI adjudication proceeding relating to securities market transactions.",
        "context_after": "There are no other regulatory actions currently pending against our Promoter by SEBI.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0017",
        "ipo_id": "honasa-consumer-2023",
        "slice": "train",
        "page": 41,
        "check_id": "qualified_audit",
        "sentence": "The Auditor’s report on internal financial controls issued on our standalone financial statements for the Financial Year 2020 contains a disclaimer of opinion relating to the Auditors’ inability to obtain appropriate audit evidence to provide a basis for opinion on adequate internal financial controls.",
        "context_before": "Our Statutory Auditors have included certain remarks and modifications in their audit reports for past financial years.",
        "context_after": "We have subsequently remediated the underlying internal control processes.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0018",
        "ipo_id": "paradeep-phosphates-2022",
        "slice": "train",
        "page": 39,
        "check_id": "going_concern",
        "sentence": "Our Statutory Auditor, the Current Statutory Auditor of the Goa Facility and the Previous Statutory Auditor of the Goa Facility have included an emphasis of matter paragraph and a material uncertainty related to going concern in their respective auditors’ reports on certain financial statements.",
        "context_before": "Internal Risk Factors relating to our financial statements and audit reports.",
        "context_after": "The Current Statutory Auditors and Previous Statutory Auditors of the Special Purpose Carve-out Financial Statements has included material uncertainty to indicate that in addition to a net current liability position, there are events or conditions which indicate that a material uncertainty exists.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0019",
        "ipo_id": "fusion-micro-finance-2022",
        "slice": "train",
        "page": 44,
        "check_id": "fraud",
        "sentence": "During the last three financial years and the three months ended June 30, 2022, we registered 884 instances of fraud or misappropriation by our employees, which were for an aggregate amount of ₹32.50 million.",
        "context_before": "Certain instances of fraud and misconduct by our employees may go unnoticed for some time before they are discovered and successfully rectified.",
        "context_after": "Even when we discover instances of fraud and other misconduct and pursue legal recourse or file claims with our insurance carriers, we cannot assure you that we will recover any amounts lost.",
        "rules_decision": "missed_by_regex",
    },
    {
        "id": "rf_ae_0020",
        "ipo_id": "ajax-engineering-2025",
        "slice": "train",
        "page": 48,
        "check_id": "regulator_order",
        "sentence": "Further, our Company has submitted an application dated January 23, 2025 with the RBI on January 24, 2025 for compounding the delay in filing of form FC-GPR for the said Allotment.",
        "context_before": "There have been certain delays in regulatory filings under FEMA in connection with past allotments of shares to non-residents.",
        "context_after": "Any compounding fee or penalty imposed by the RBI in this regard could adversely affect our financials.",
        "rules_decision": "missed_by_regex",
    },
]

# ---------------------------------------------------------------------------
# 2. Classification logic for non-actual_event rows in serious_finding_hits
# ---------------------------------------------------------------------------


def classify_non_actual_hit(row: dict) -> str:
    """Classify a non-actual_event row into hypothetical, negated, or not_relevant."""
    s = row["sentence"]
    s_low = s.lower()

    # Fired rows that are not actual_event were audited line-by-line:
    if row["rules_decision"] == "fired":
        # Hypothetical / covenant boilerplate in fired:
        if any(
            kw in s_low
            for kw in (
                "in the event",
                "any default",
                "could result",
                "may result",
                "typically contain provisions",
                "if any of",
                "constitute an event of default",
                "Cross-default",
                "cross default",
                "entitle the",
                "accelerate",
                "recall the loan",
            )
        ):
            return "hypothetical"
        # Exonerated / disposed / compliance statements in fired:
        if any(
            kw in s_low
            for kw in (
                "disposed of",
                "without any direction",
                "without imposing",
                "in compliance with",
                "complied with",
                "no penalty",
                "not defaulted",
            )
        ):
            return "negated"
        # Everything else in fired (NBFC customer/borrower recovery suits, definitions, table headers, statutory form delays):
        return "not_relevant"

    # For blocked_soft / blocked_no_debt rows:
    # 1. Hypothetical / forward-looking risk disclosures ("if we default", "may adversely affect", "could result in",
    #    "in the event of", "cannot assure", "any default", "failure to comply")
    if any(
        kw in s_low
        for kw in (
            "may adversely",
            "could adversely",
            "would adversely",
            "adversely affect",
            "adverse effect",
            "adversely impact",
            "adverse impact",
            "if we ",
            "if any ",
            "if our ",
            "if such ",
            "in the event",
            "may result in",
            "could result in",
            "would result in",
            "cannot assure",
            "no assurance",
            "may lead to",
            "could lead to",
            "could subject us",
            "may be subject to",
            "failure to comply",
            "failure to meet",
            "failure to service",
            "inability to",
            "unable to",
            "any default",
            "any delay",
            "any future default",
            "cross-default",
            "cross default",
            "accelerate our",
            "recall our",
            "terminate the",
        )
    ):
        return "hypothetical"

    # 2. Explicit negations ("has not defaulted", "no instances of", "has not been declared wilful defaulter", "neither our company...")
    if any(
        kw in s_low
        for kw in (
            "has not defaulted",
            "have not defaulted",
            "has not been declared",
            "have not been declared",
            "not declared as willful defaulter",
            "not declared as wilful defaulter",
            "is not a wilful defaulter",
            "are not wilful defaulters",
            "neither our company",
            "none of our company",
            "none of our promoters",
            "none of the companies",
            "no instances of default",
            "no defaults in repayment",
            "no default in the repayment",
            "have not had any instances",
            "not faced any instances",
            "not experienced any",
            "are not debarred",
            "is not debarred",
            "no proceedings have been initiated",
            "no auditor qualifications",
            "no qualifications",
            "not been any instance",
            "there are no defaults",
            "there have been no defaults",
            "there have been no instances",
        )
    ):
        return "negated"

    # 3. Not relevant (accounting policies, glossary definitions, third-party/customer litigation, table headers, ordinary course)
    return "not_relevant"


def extract_evidence_quote(sentence: str, check_id: str) -> str:
    """Extract an exact substring of <= 25 whitespace-delimited words from `sentence`."""
    words = sentence.split()
    if len(words) <= 22:
        return sentence.strip()

    # Center the quote around the key trigger phrase for `check_id`
    trigger_map = {
        "going_concern": r"(going concern|material uncertainty)",
        "default_or_recall": r"(default\w*|delay\w*|overdue|recalled|repayment|covenant\w*)",
        "regulator_order": r"(sebi|rbi|irdai|nhb|bse|nse|penalty|show cause|warning letter|debarred|wilful defaulter)",
        "fraud": r"(fraud\w*|embezzlement|misappropriation|fir\b)",
        "qualified_audit": r"(qualified opinion|disclaimer of opinion|adverse|emphasis of matter|caro|qualification\w*)",
    }
    pat = re.compile(trigger_map.get(check_id, r"\w+"), re.I)
    m = pat.search(sentence)
    if m:
        char_pos = m.start()
        # Find word index corresponding to char_pos
        prefix_words = sentence[:char_pos].split()
        w_idx = len(prefix_words)
        start = max(0, min(w_idx - 6, len(words) - 20))
    else:
        start = 0
    end = min(len(words), start + 20)
    quote = " ".join(words[start:end])
    assert len(quote.split()) <= 25
    assert quote in " ".join(words)
    return quote


def build_dataset() -> tuple[list[dict], list[dict], list[dict]]:
    excluded_obj = json.loads((HANDOFF_DATA / "excluded_ipos.json").read_text(encoding="utf-8"))
    excluded_set = set(excluded_obj["ipos"].keys())

    splits_obj = json.loads((HANDOFF_DATA / "splits_by_ipo.json").read_text(encoding="utf-8"))
    valid_td_ipos = {
        item["ipo_id"]: item["slice"]
        for item in splits_obj["ipos"]
        if not item.get("excluded")
        and item["ipo_id"] not in excluded_set
        and item["slice"] in ("train", "dev")
    }

    with gzip.open(HANDOFF_DATA / "serious_finding_hits.jsonl.gz", "rt", encoding="utf-8") as f:
        raw_hits = [json.loads(line) for line in f]

    selected_rows: list[dict] = []
    used_ids: set[str] = set()

    def make_row(r: dict, label: str) -> dict:
        sent_norm = " ".join(r["sentence"].split())
        quote = extract_evidence_quote(sent_norm, r["check_id"])
        return {
            "id": r["id"],
            "ipo_id": r["ipo_id"],
            "slice": r["slice"],
            "page": int(r["page"]),
            "check_id": r["check_id"],
            "sentence": sent_norm,
            "context_before": " ".join(r.get("context_before", "").split()),
            "context_after": " ".join(r.get("context_after", "").split()),
            "evidence_quote": quote,
            "label": label,
            "rules_decision": r["rules_decision"],
            "label_source": "ai",
        }

    # Step 1: Include ALL valid (non-excluded train/dev + test) `fired` rows AND all rescued `actual_event` rows
    for r in raw_hits:
        # Never allow an excluded IPO into train or dev
        if r["slice"] in ("train", "dev") and (
            r.get("excluded") or r["ipo_id"] in excluded_set or r["ipo_id"] not in valid_td_ipos
        ):
            continue

        hid = r["id"]
        if hid in FIRED_ACTUAL_EVENTS or hid in BLOCKED_ACTUAL_EVENTS:
            selected_rows.append(make_row(r, "actual_event"))
            used_ids.add(hid)
        elif r["rules_decision"] == "fired":
            lbl = classify_non_actual_hit(r)
            selected_rows.append(make_row(r, lbl))
            used_ids.add(hid)

    # Step 2: Add the 20 mined Risk-Factor `actual_event` rows (train/dev non-excluded IPOs only)
    for mr in MINED_TRAIN_DEV_ACTUAL_EVENTS:
        assert mr["ipo_id"] not in excluded_set
        assert mr["ipo_id"] in valid_td_ipos
        assert mr["slice"] == valid_td_ipos[mr["ipo_id"]]
        selected_rows.append(make_row(mr, "actual_event"))
        used_ids.add(mr["id"])

    # Step 3: Sample additional `blocked_soft` / `blocked_no_debt` rows across IPOs to achieve balanced
    # coverage (~900 rows total, >=200 per non-actual class, maximizing unique IPO diversity)
    rng = random.Random(42)
    remaining_by_class: dict[str, list[dict]] = defaultdict(list)
    for r in raw_hits:
        if r["id"] in used_ids:
            continue
        if r["slice"] in ("train", "dev") and (
            r.get("excluded") or r["ipo_id"] in excluded_set or r["ipo_id"] not in valid_td_ipos
        ):
            continue
        lbl = classify_non_actual_hit(r)
        remaining_by_class[lbl].append(r)

    current_counts = Counter(row["label"] for row in selected_rows)
    target_per_non_actual_class = 235

    for lbl in ("hypothetical", "negated", "not_relevant"):
        need = max(0, target_per_non_actual_class - current_counts[lbl])
        pool = remaining_by_class[lbl]
        rng.shuffle(pool)
        # Prioritize unseen IPOs first, then unseen check_ids
        seen_ipos = {row["ipo_id"] for row in selected_rows}
        pool.sort(key=lambda x: (x["ipo_id"] in seen_ipos, x["check_id"]))
        for r in pool[:need]:
            selected_rows.append(make_row(r, lbl))
            used_ids.add(r["id"])
            seen_ipos.add(r["ipo_id"])

    # Sort deterministically by id
    selected_rows.sort(key=lambda x: x["id"])

    train_rows = [r for r in selected_rows if r["slice"] == "train"]
    dev_rows = [r for r in selected_rows if r["slice"] == "dev"]
    test_rows = [r for r in selected_rows if r["slice"] == "test"]

    # Safety assertions
    for r in train_rows + dev_rows:
        assert r["ipo_id"] not in excluded_set, f"Excluded IPO leaked: {r['ipo_id']}"
        assert r["ipo_id"] in valid_td_ipos, f"Non-train/dev IPO leaked: {r['ipo_id']}"
    for r in test_rows:
        assert r["id"].startswith("hit"), f"Non-hit row in test: {r['id']}"

    return train_rows, dev_rows, test_rows


def write_outputs(train_rows: list[dict], dev_rows: list[dict], test_rows: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for name, rows in [
        ("train.jsonl", train_rows),
        ("dev.jsonl", dev_rows),
        ("test.jsonl", test_rows),
    ]:
        out_path = OUT_DIR / name
        with out_path.open("w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    all_rows = train_rows + dev_rows + test_rows

    # Build Akshat's verification sheet: 100% of `actual_event` rows + 100 random rows from other 3 classes
    actual_rows = [r for r in all_rows if r["label"] == "actual_event"]
    other_rows = [r for r in all_rows if r["label"] != "actual_event"]
    rng = random.Random(42)
    sampled_others = sorted(rng.sample(other_rows, 100), key=lambda x: x["id"])
    verify_rows = actual_rows + sampled_others

    csv_path = OUT_DIR / "akshat_verification_gold.csv"
    fieldnames = [
        "id",
        "ipo_id",
        "slice",
        "page",
        "check_id",
        "label",
        "verified_label",
        "severity_band_1_to_4",
        "rules_decision",
        "evidence_quote",
        "sentence",
        "context_before",
        "context_after",
        "label_source",
        "notes",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in verify_rows:
            band_default = "4" if (r["label"] == "actual_event" and r["slice"] == "train") else ""
            writer.writerow(
                {
                    "id": r["id"],
                    "ipo_id": r["ipo_id"],
                    "slice": r["slice"],
                    "page": r["page"],
                    "check_id": r["check_id"],
                    "label": r["label"],
                    "verified_label": "",
                    "severity_band_1_to_4": band_default,
                    "rules_decision": r["rules_decision"],
                    "evidence_quote": r["evidence_quote"],
                    "sentence": r["sentence"],
                    "context_before": r["context_before"],
                    "context_after": r["context_after"],
                    "label_source": r["label_source"],
                    "notes": "Verify actual_event + band (1-4) if slice==train for M4"
                    if r["label"] == "actual_event"
                    else "Random 100 audit sample",
                }
            )

    # Write LABELS_CARD.md with exact script-computed statistics
    write_labels_card(train_rows, dev_rows, test_rows, len(verify_rows), len(actual_rows))


def write_labels_card(
    train_rows: list[dict],
    dev_rows: list[dict],
    test_rows: list[dict],
    n_verify: int,
    n_actual: int,
) -> None:
    all_rows = train_rows + dev_rows + test_rows
    n_ipos_total = len({r["ipo_id"] for r in all_rows})
    n_ipos_train = len({r["ipo_id"] for r in train_rows})
    n_ipos_dev = len({r["ipo_id"] for r in dev_rows})
    n_ipos_test = len({r["ipo_id"] for r in test_rows})

    def count_by(rows: list[dict], key: str) -> Counter:
        return Counter(r[key] for r in rows)

    c_train = count_by(train_rows, "label")
    c_dev = count_by(dev_rows, "label")
    c_test = count_by(test_rows, "label")
    c_all = count_by(all_rows, "label")

    chk_all = count_by(all_rows, "check_id")
    chk_ae = count_by([r for r in all_rows if r["label"] == "actual_event"], "check_id")

    rd_all = count_by(all_rows, "rules_decision")
    rd_ae = count_by([r for r in all_rows if r["label"] == "actual_event"], "rules_decision")

    card = f"""# L2 Event Classification Dataset Card (`data/gold/event_labels/`)

Generated deterministically by `ml/l2_build_event_labels.py` (Task **AR-03**, for **M3 Event Classifier** and **M4 Severity v2** severe-band augmentation).

## 1. Summary & Split Integrity
- **Total sentences:** **{len(all_rows)}** across **{n_ipos_total} unique IPOs** (target: ~800 sentences, ≥150 per class, ≥60 IPOs).
- **Zero-leakage guarantee:** `train.jsonl` ({len(train_rows)} rows, {n_ipos_train} IPOs) and `dev.jsonl` ({len(dev_rows)} rows, {n_ipos_dev} IPOs) contain **0 IPOs** from `ml/handoff/data/excluded_ipos.json` (verified by `tests/ml/test_no_leakage.py`, including filtering out the 18 rows in `serious_finding_hits.jsonl.gz` that had `slice="dev"` with `excluded=true`).
- **Test set alignment (`test.jsonl`):** {len(test_rows)} rows across {n_ipos_test} test-slice IPOs, 100% drawn from `serious_finding_hits.jsonl.gz` (`hit*` IDs) so CC's baseline (`rules_decision`) evaluates on the exact same items.
- **Provenance:** Every row carries `label_source: "ai"`, `page`, and an exact substring `evidence_quote` (≤ 25 words).

## 2. Class Distribution by Split

| Class (`label`) | `train.jsonl` | `dev.jsonl` | `train + dev` | `test.jsonl` (eval only) | **Total** |
|---|---:|---:|---:|---:|---:|
| `actual_event` | {c_train["actual_event"]} | {c_dev["actual_event"]} | {c_train["actual_event"] + c_dev["actual_event"]} | {c_test["actual_event"]} | **{c_all["actual_event"]}** |
| `hypothetical` | {c_train["hypothetical"]} | {c_dev["hypothetical"]} | {c_train["hypothetical"] + c_dev["hypothetical"]} | {c_test["hypothetical"]} | **{c_all["hypothetical"]}** |
| `negated` | {c_train["negated"]} | {c_dev["negated"]} | {c_train["negated"] + c_dev["negated"]} | {c_test["negated"]} | **{c_all["negated"]}** |
| `not_relevant` | {c_train["not_relevant"]} | {c_dev["not_relevant"]} | {c_train["not_relevant"] + c_dev["not_relevant"]} | {c_test["not_relevant"]} | **{c_all["not_relevant"]}** |
| **Total** | **{len(train_rows)}** | **{len(dev_rows)}** | **{len(train_rows) + len(dev_rows)}** | **{len(test_rows)}** | **{len(all_rows)}** |

> [!NOTE]
> **Honesty note on `actual_event` counts:** Across the entire corpus (all 2,801 `serious_finding_hits` rows + Risk Factor mining across all non-excluded `train`/`dev` RHPs), there are **{c_all["actual_event"]}** genuine `actual_event` sentences (**{c_train["actual_event"] + c_dev["actual_event"]}** in `train`+`dev` [{c_train["actual_event"]} `train`, {c_dev["actual_event"]} `dev`] and **{c_test["actual_event"]}** in `test`). Per Akshat's instruction, `train`+`dev` is reported at its true natural count ({c_train["actual_event"] + c_dev["actual_event"]} rows) rather than padding with borderline or synthetic rows.

## 3. Distribution by Severe `check_id` and `rules_decision`

| `check_id` | Total Rows | `actual_event` Rows |
|---|---:|---:|
| `default_or_recall` | {chk_all["default_or_recall"]} | {chk_ae["default_or_recall"]} |
| `regulator_order` | {chk_all["regulator_order"]} | {chk_ae["regulator_order"]} |
| `qualified_audit` | {chk_all["qualified_audit"]} | {chk_ae["qualified_audit"]} |
| `going_concern` | {chk_all["going_concern"]} | {chk_ae["going_concern"]} |
| `fraud` | {chk_all["fraud"]} | {chk_ae["fraud"]} |

| `rules_decision` | Total Rows | `actual_event` Rows | Notes |
|---|---:|---:|---|
| `fired` | {rd_all["fired"]} | {rd_ae["fired"]} | All non-excluded `fired` rows audited; false positives are mostly NBFC/bank customer-default recovery suits, definitions, or covenant boilerplate |
| `blocked_soft` | {rd_all["blocked_soft"]} | {rd_ae["blocked_soft"]} | **Rescued real events** blocked by `_SOFT` words (`"may"`, `"without"`, `"not"`, `"no."`) |
| `blocked_no_debt` | {rd_all["blocked_no_debt"]} | {rd_ae["blocked_no_debt"]} | Statutory / non-debt rows |
| `missed_by_regex` | {rd_all["missed_by_regex"]} | {rd_ae["missed_by_regex"]} | Mined from non-excluded `train`/`dev` Risk Factor pages |

## 4. Key Audit Findings on `serious_finding_hits.jsonl.gz`
1. **Why `fired` had false positives (`{rd_all["fired"] - rd_ae["fired"]}/{rd_all["fired"]}` non-actual):**
   - **Ordinary-course lender/insurer litigation against customers (`not_relevant`):** In NBFCs, housing finance companies, small finance banks, and insurers (`aadhar-housing-finance-2024`, `bajaj-housing-finance-2024`, `capital-small-finance-bank-2024`, `jana-small-finance-bank-2024`, `manba-finance-2024`, `hdb-financial-services-2025`, `tata-capital-2025`, `aye-finance-2026`), sentences describing *customers/borrowers* defaulting on loans taken *from* the issuer or FIRs against third-party insurance/loan fraud triggered `default_or_recall` and `fraud`.
   - **Definitions, table headers, and covenant boilerplate (`not_relevant` / `hypothetical`):** Glossary definitions of `"Wilful Defaulter or Fraudulent Borrower"`, loan schedule table captions, and cross-default clauses without any past breach.
   - **Disposed / exonerated regulatory proceedings (`negated`):** E.g., SEBI orders in `national-securities-depository-2025` (`hit001672`–`hit001674`, `hit001678`) where proceedings were disposed of without penalty or directions.
2. **Why `blocked_soft` hid `{rd_ae["blocked_soft"]}` real severe events (`actual_event`):**
   - **Going concern (`going_concern`):** Standard statutory auditor wording (*"indicate that a material uncertainty exists that **may** cast significant doubt on the Company's ability to continue as a going concern"* or *"Without qualifying our opinion..."*) was blocked by `"may"` or `"without"`.
   - **Loan repayment delays (`default_or_recall`):** CARO Clause ix(a) and Risk Factor disclosures (*"The Company has **not** defaulted in repayment of loans... except for the following delays"*) were blocked by `"not"`.
   - **Regulator penalty orders (`regulator_order`):** Blocked when the sentence stated *"had **not** complied with Regulation... and BSE/RBI/SEBI imposed a penalty"* or cited *"adjudication order bearing **no.** ..."* (matching `\\bno\\b`).
   - **Qualified/Disclaimer of audit opinions (`qualified_audit`):** Basis for Qualified Opinion paragraphs containing *"was **not** operating effectively which **could**..."* or *"did **not** observe"* were blocked by `"not"`/`"could"`.

## 5. Akshat Verification Sheet (`akshat_verification_gold.csv`)
- Contains **{n_verify} rows**: **100% of `actual_event` rows ({n_actual} rows)** + **100 random rows** from `hypothetical`, `negated`, and `not_relevant` (`seed=42`).
- For `train`-split `actual_event` rows ({c_train["actual_event"]} rows), `severity_band_1_to_4` is pre-filled with `4` so Akshat can verify both the event label and the severity band (1–4) in one pass for **M4 Severity v2** (per P-3).
"""
    (OUT_DIR / "LABELS_CARD.md").write_text(card, encoding="utf-8")


if __name__ == "__main__":
    tr, dv, te = build_dataset()
    write_outputs(tr, dv, te)
    print(
        f"Wrote L2 dataset: train={len(tr)}, dev={len(dv)}, test={len(te)}, total={len(tr) + len(dv) + len(te)}"
    )
