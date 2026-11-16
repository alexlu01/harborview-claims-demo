import re
from data import harborview_data as hd

def test_deterministic():
    assert hd.generate(7) == hd.generate(7)

def test_hero_claim_present_and_consistent():
    d = hd.generate(7)
    c = next(x for x in d["claims"] if x["claim_id"] == "C-1042")
    p = next(x for x in d["policies"] if x["policy_id"] == c["policy_id"])
    assert c["loss_type"] == "water_backup" and c["claim_amount"] == 7850.0
    assert p["deductible"] == 1000.0 and p["water_backup_limit"] == 10000.0
    assert "HV-END-WB" in p["endorsements"]

def test_unique_ids_and_sizes():
    d = hd.generate(7)
    ids = [c["claim_id"] for c in d["claims"]]
    assert len(ids) == len(set(ids)) and len(ids) >= 200
    assert all(re.fullmatch(r"C-\d{4}", i) for i in ids)
    assert "C-9999" not in ids  # reserved for the not-found eval case

def test_eval_seeds_shape():
    rows = hd.eval_seed_rows()
    assert 25 <= len(rows) <= 40
    assert all(set(r) == {"inputs", "expectations"} and "question" in r["inputs"] for r in rows)
    assert any("C-9999" in r["inputs"]["question"] for r in rows)
    assert sum(r["expectations"].get("needs_docs", False) for r in rows) >= 8

def test_no_eval_input_trips_ssn_pattern():
    qs = [r["inputs"]["question"] for r in hd.eval_seed_rows()] + [hd.HERO["question"]]
    assert not any(hd.ssn_like(q) for q in qs)
    assert hd.ssn_like("my SSN is 123-45-6789")

def test_dates_do_not_trip():
    assert not hd.ssn_like("Loss date 2026-09-14 is within the policy period.")
    assert not hd.ssn_like("C-1042 on policy P-20417, HV-END-WB §2.1")

def test_pdfs_written(tmp_path):
    paths = hd.write_pdfs(str(tmp_path))
    assert len(paths) >= 40
    from pypdf import PdfReader
    wb = next(p for p in paths if p.endswith("HV-END-WB.pdf"))
    text = "".join(pg.extract_text() for pg in PdfReader(wb).pages)
    assert "§2.1" in text and "Water Backup" in text

def _wb_text(tmp_path):
    from pypdf import PdfReader
    wb = next(p for p in hd.write_pdfs(str(tmp_path)) if p.endswith("HV-END-WB.pdf"))
    return "".join(pg.extract_text() for pg in PdfReader(wb).pages)

def test_section_number_is_inline_with_body(tmp_path):
    # ai_prep_search moves standalone headers into metadata; inline numbers survive in chunk_to_retrieve
    assert "§2.1 Water Backup Coverage. We cover" in _wb_text(tmp_path)

def test_body_wraps_on_word_boundaries(tmp_path):
    assert "overflow" in _wb_text(tmp_path).replace("\n", " ").replace("  ", " ")
    assert "over\nflow" not in _wb_text(tmp_path)


def test_form_ids_do_not_trip_ssn_pattern():
    for s in ("Does the HV-HO-3 form cover mold?", "covered [HV-HO-3 §7.1] and [HV-END-WB §2.1]",
              "[HV-HO-3] §7.3 Concealed water"):
        assert not hd.ssn_like(s), s


def test_ssn_still_blocked_next_to_a_date():
    assert hd.ssn_like("Loss on 2026-09-14, insured SSN 123-45-6789")
