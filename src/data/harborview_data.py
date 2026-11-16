"""Seeded synthetic data for Harborview Mutual (fictional insurer)."""
import os, random, re, textwrap
from datetime import date, timedelta

FORMS = {
    "HV-HO-3": ("Homeowners Policy Form HO-3", [
        ("§1.1", "Coverage A — Dwelling", "We cover direct physical loss to the dwelling unless excluded."),
        ("§4.2", "Deductible", "The deductible shown in the Declarations applies per occurrence."),
        ("§7.1", "Exclusion — Water Backup", "We do not cover water that backs up through sewers or drains unless endorsement HV-END-WB is attached."),
        ("§7.3", "Exclusion — Mold", "We do not cover mold, fungi or wet rot unless caused by a covered sudden water discharge, limited to $5,000."),
        ("§9.1", "Duties After Loss", "Notify us within 60 days of the loss and protect the property from further damage."),
    ]),
    "HV-END-WB": ("Water Backup and Sump Discharge Endorsement", [
        ("§2.1", "Water Backup Coverage", "We cover direct physical loss caused by water backup through sewers or drains or sump pump overflow, up to the Water Backup limit in the Declarations."),
        ("§2.2", "Deductible", "The policy deductible applies to each water backup loss."),
    ]),
    "HV-END-EQ": ("Earthquake Endorsement", [
        ("§3.1", "Earthquake Coverage", "We cover earthquake loss subject to a deductible of 10% of Coverage A."),
    ]),
    "HV-AUTO-1": ("Personal Auto Policy", [
        ("§2.4", "Collision", "We pay for direct loss to your covered auto caused by collision, minus the deductible."),
        ("§5.1", "Rental Reimbursement", "If endorsement HV-END-RR is attached we pay up to $40 per day for 30 days."),
    ]),
    "HV-END-RR": ("Rental Reimbursement Endorsement", [
        ("§1.1", "Rental Reimbursement", "We reimburse rental car costs up to $40 per day, maximum 30 days, after a covered loss."),
    ]),
    "HV-END-SL": ("Service Line Endorsement", [
        ("§1.2", "Service Line Coverage", "We cover underground service line failure up to $10,000 with a $500 deductible."),
    ]),
}
LOSS_TYPES = {"HO": ["water_backup", "wind_hail", "fire", "theft", "mold", "service_line"],
              "AUTO": ["collision", "comprehensive", "rental"]}

HERO = {
    "question": "Is the water damage on claim C-1042 covered, and what is the payout after the deductible?",
    "expected_facts": ["Claim C-1042 is a water backup loss", "Covered under endorsement HV-END-WB §2.1",
                       "Deductible is $1,000", "Payout is $6,850"],
}

def ssn_like(s: str) -> bool:
    """Mirror of the block_ssn policy: digits masked to '#' via nested REPLACE, LIKE '%###-##-####%' (digits only, so form IDs
    like HV-HO-3 and ISO dates never match, and an SSN next to a date still does)."""
    return re.search(r"[0-9]{3}-[0-9]{2}-[0-9]{4}", s) is not None

def generate(seed: int = 7) -> dict:
    rng = random.Random(seed)
    policies, claims, payments, notes = [], [], [], []
    for i in range(120):
        line = "HO" if i % 3 else "AUTO"
        pid = f"P-{20300 + i}"
        ends = []
        if line == "HO":
            ends = sorted(rng.sample(["HV-END-WB", "HV-END-EQ", "HV-END-SL"], k=rng.randint(0, 2)))
        else:
            ends = ["HV-END-RR"] if rng.random() < 0.5 else []
        policies.append({
            "policy_id": pid, "line": line, "form_id": "HV-HO-3" if line == "HO" else "HV-AUTO-1",
            "insured_name": f"Insured {i:03d}", "state": rng.choice(["NY", "NJ", "CT", "MA"]),
            "coverage_a_limit": float(rng.choice([250000, 400000, 600000])) if line == "HO" else 0.0,
            "deductible": float(rng.choice([500, 1000, 2500])),
            "water_backup_limit": 10000.0 if "HV-END-WB" in ends else 0.0,
            "endorsements": ",".join(ends),
            "effective_date": str(date(2026, 1, 1) + timedelta(days=rng.randint(0, 200))),
        })
    # Hero policy is pinned.
    hero = {"policy_id": "P-20417", "line": "HO", "form_id": "HV-HO-3", "insured_name": "Insured 117",
            "state": "NY", "coverage_a_limit": 400000.0, "deductible": 1000.0, "water_backup_limit": 10000.0,
            "endorsements": "HV-END-WB", "effective_date": "2026-03-01"}
    policies = [p for p in policies if p["policy_id"] != "P-20417"] + [hero]
    for n in range(240):
        p = rng.choice(policies)
        cid = f"C-{1000 + n}"
        loss = rng.choice(LOSS_TYPES[p["line"]])
        amt = float(rng.randrange(400, 40000, 50))
        claims.append({"claim_id": cid, "policy_id": p["policy_id"], "loss_type": loss,
                       "loss_date": str(date(2026, 4, 1) + timedelta(days=rng.randint(0, 180))),
                       "claim_amount": amt, "status": rng.choice(["open", "in_review", "closed"]),
                       "adjuster": rng.choice(["J. Ortiz", "M. Chen", "A. Patel", "R. Kim"])})
    hero_claim = {"claim_id": "C-1042", "policy_id": "P-20417", "loss_type": "water_backup",
                  "loss_date": "2026-09-14", "claim_amount": 7850.0, "status": "in_review", "adjuster": "M. Chen"}
    claims = [c for c in claims if c["claim_id"] != "C-1042"] + [hero_claim]
    for c in claims:
        if c["status"] == "closed":
            payments.append({"claim_id": c["claim_id"], "amount": round(c["claim_amount"] * 0.8, 2),
                             "paid_date": c["loss_date"]})
        notes.append({"claim_id": c["claim_id"],
                      "note": f"Inspected {c['loss_type'].replace('_', ' ')} loss; insured cooperative."})
    claims.sort(key=lambda c: c["claim_id"])
    policies.sort(key=lambda p: p["policy_id"])
    return {"policies": policies, "claims": claims, "payments": payments, "adjuster_notes": notes}

def write_pdfs(out_dir: str) -> list[str]:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    def _doc(path, title, sections):
        c = canvas.Canvas(path, pagesize=letter)
        y = 740
        c.setFont("Helvetica-Bold", 14); c.drawString(72, y, f"Harborview Mutual — {title}"); y -= 30
        for sec, head, body in sections:
            # section number inline with the body, so it survives ai_prep_search into chunk_to_retrieve
            c.setFont("Helvetica", 10)
            for line in textwrap.wrap(f"{sec} {head}. {body}", 95):
                c.drawString(72, y, line); y -= 14
            y -= 10
            if y < 100: c.showPage(); y = 740
        c.save(); paths.append(path)
    for form_id, (title, sections) in FORMS.items():
        _doc(os.path.join(out_dir, f"{form_id}.pdf"), title, sections)
    for p in generate()["policies"][:40]:
        _doc(os.path.join(out_dir, f"DEC-{p['policy_id']}.pdf"), f"Declarations {p['policy_id']}", [
            ("§D.1", "Named Insured", p["insured_name"]),
            ("§D.2", "Form", p["form_id"]),
            ("§D.3", "Deductible", f"${p['deductible']:,.0f} per occurrence"),
            ("§D.4", "Endorsements", p["endorsements"] or "None"),
            ("§D.5", "Water Backup Limit", f"${p['water_backup_limit']:,.0f}"),
        ])
    return paths

def eval_seed_rows() -> list[dict]:
    rows = [{"inputs": {"question": HERO["question"]},
             "expectations": {"expected_facts": HERO["expected_facts"], "needs_docs": True}}]
    doc_qs = [
        ("Does a standard HO-3 policy cover sewer backup without an endorsement?", ["Not covered under HV-HO-3 §7.1 without HV-END-WB"]),
        ("What is the mold sublimit on the homeowners form?", ["Mold limited to $5,000 under HV-HO-3 §7.3"]),
        ("How long does an insured have to report a homeowners loss?", ["Within 60 days per HV-HO-3 §9.1"]),
        ("What does rental reimbursement pay per day?", ["$40 per day", "Maximum 30 days"]),
        ("What is the earthquake deductible?", ["10% of Coverage A per HV-END-EQ §3.1"]),
        ("What is the service line coverage limit and deductible?", ["$10,000 limit", "$500 deductible"]),
        ("Does the water backup endorsement have its own deductible?", ["Policy deductible applies per HV-END-WB §2.2"]),
        ("Is sump pump overflow covered with the water backup endorsement?", ["Covered under HV-END-WB §2.1"]),
        ("Is collision covered on the personal auto policy?", ["Covered under HV-AUTO-1 §2.4 minus deductible"]),
    ]
    rows += [{"inputs": {"question": q}, "expectations": {"expected_facts": f, "needs_docs": True}} for q, f in doc_qs]
    d = generate()
    pol = {p["policy_id"]: p for p in d["policies"]}
    for c in [c for c in d["claims"] if c["claim_id"] != "C-1042"][:18]:
        p = pol[c["policy_id"]]
        rows.append({"inputs": {"question": f"What is the status and amount of claim {c['claim_id']}?"},
                     "expectations": {"expected_facts": [f"Status is {c['status']}",
                                                          f"Claim amount is ${c['claim_amount']:,.0f}",
                                                          f"Policy {p['policy_id']}"], "needs_docs": False}})
    rows.append({"inputs": {"question": "What is the status of claim C-9999?"},
                 "expectations": {"expected_facts": ["Claim C-9999 was not found"], "needs_docs": False}})
    return rows
