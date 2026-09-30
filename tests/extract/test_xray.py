from datetime import UTC, datetime

from finsight.core.schemas import Candidate, DocType, Money, Placeholder, TextValue, Value
from finsight.extract import DocInputs, build_xray, field_ids
from finsight.normalize import parse_amount

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def money(text: str) -> Money:
    value = parse_amount(text)
    assert isinstance(value, Money)
    return value


def cand(
    field_id: str,
    value: Value,
    doc: DocType = "rhp",
    extractor: str = "rules",
    page: int = 3,
    score: float = 0.9,
) -> Candidate:
    raw = getattr(value, "raw", getattr(value, "text", "x"))
    return Candidate(
        field_id=field_id, extractor=extractor, doc_type=doc, raw=raw, value=value, page=page,
        score=score,
    )  # fmt: skip


def docs(rhp: list[Candidate], pro: list[Candidate], **kw: object) -> dict[DocType, DocInputs]:
    def by_field(cands: list[Candidate]) -> dict[str, list[Candidate]]:
        out: dict[str, list[Candidate]] = {}
        for c in cands:
            out.setdefault(c.field_id, []).append(c)
        return out

    return {
        "rhp": DocInputs(candidates=by_field(rhp), **kw),  # type: ignore[arg-type]
        "prospectus": DocInputs(candidates=by_field(pro)),
    }


def field(xray, field_id):  # type: ignore[no-untyped-def]
    return next(f for f in xray.fields if f.field_id == field_id)


def test_one_result_per_field_in_registry_order() -> None:
    xray = build_xray("urban-company-2025", "Urban Company", docs([], []), NOW)
    assert [f.field_id for f in xray.fields] == field_ids()
    assert xray.ipo_id == "urban-company-2025"
    assert xray.company == "Urban Company"
    assert xray.built_at == NOW
    assert field(xray, "registrar").chosen is None


def test_consistent_offer_is_verified_with_derived_shares() -> None:
    rhp = [
        cand("fresh_issue_size", money("₹ 4,720 million")),
        cand("ofs_amount", money("₹ 14,280 million")),
    ]
    pro = [cand("total_issue_size", money("₹ 19,000 million"), "prospectus")]
    xray = build_xray("x", "X", docs(rhp, pro), NOW)
    assert xray.derived == {"fresh_share_pct": "24.84", "ofs_share_pct": "75.16"}
    for fid in ("fresh_issue_size", "ofs_amount", "total_issue_size"):
        (check,) = field(xray, fid).checks
        assert check.check == "total_equals_fresh_plus_ofs"
        assert check.status == "verified"
    assert field(xray, "registrar").checks == []
    assert field(xray, "total_issue_size").chosen is not None
    assert field(xray, "total_issue_size").chosen.doc_type == "prospectus"  # type: ignore[union-attr]


def test_blank_rhp_amount_uses_the_prospectus_value_for_the_check() -> None:
    rhp = [
        cand("fresh_issue_size", money("₹ 4,720 million")),
        cand("ofs_amount", Placeholder(raw="₹ [●] million")),
    ]
    pro = [
        cand("ofs_amount", money("₹ 14,280 million"), "prospectus"),
        cand("total_issue_size", money("₹ 19,000 million"), "prospectus"),
    ]
    xray = build_xray("x", "X", docs(rhp, pro), NOW)
    ofs = field(xray, "ofs_amount")
    assert ofs.reason_code == "placeholder"  # the RHP itself is still blank
    assert "Prospectus" in ofs.reason
    assert ofs.checks[0].status == "verified"
    assert {c.doc_type for c in ofs.candidates} == {"rhp", "prospectus"}  # companion visible


def test_mismatch_is_reported_in_checks_not_hidden() -> None:
    rhp = [
        cand("fresh_issue_size", money("₹ 4,720 million")),
        cand("ofs_amount", money("₹ 14,280 million")),
    ]
    pro = [cand("total_issue_size", money("₹ 20,000 million"), "prospectus")]
    xray = build_xray("x", "X", docs(rhp, pro), NOW)
    assert field(xray, "fresh_issue_size").checks[0].status == "contradicted"
    assert xray.derived["fresh_share_pct"] == "23.60"


def test_pure_offer_for_sale_document() -> None:
    rhp = [cand("ofs_amount", money("₹ 87,500 million"))]
    pro = [cand("total_issue_size", money("₹ 87,500 million"), "prospectus")]
    xray = build_xray("x", "X", docs(rhp, pro, pure_ofs=True), NOW)
    fresh = field(xray, "fresh_issue_size")
    assert fresh.chosen is None
    assert fresh.reason_code == "not_in_document"
    assert fresh.verdict == "verified"
    assert field(xray, "objects_of_offer").reason_code == "not_in_document"
    assert xray.derived["fresh_share_pct"] == "0.00"
    assert field(xray, "ofs_amount").checks[0].status == "verified"


def test_missing_section_is_named_in_the_reason() -> None:
    xray = build_xray("x", "X", docs([], [], missing_sections=["capital_structure"]), NOW)
    face = field(xray, "face_value")
    assert face.reason_code == "section_not_found"
    assert "capital_structure" in face.reason


def test_candidates_are_capped_but_keep_one_per_document() -> None:
    many = [cand("registrar", TextValue(text=f"R{i}"), score=0.9 - i / 100) for i in range(12)]
    pro = [cand("registrar", TextValue(text="Zed"), "prospectus", score=0.1)]
    xray = build_xray("x", "X", docs(many, pro), NOW)
    kept = field(xray, "registrar").candidates
    assert len(kept) == 8
    assert any(c.doc_type == "prospectus" for c in kept)
    assert kept[0].score >= kept[-1].score


def test_xray_round_trips_through_json() -> None:
    from finsight.core.schemas import XRay

    rhp = [cand("fresh_issue_size", money("₹ 4,720 million"))]
    xray = build_xray("x", "X", docs(rhp, []), NOW)
    assert XRay.model_validate_json(xray.model_dump_json()) == xray
