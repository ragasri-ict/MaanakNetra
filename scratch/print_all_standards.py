import json
from pathlib import Path

standards = json.loads(Path("data/standards.json").read_text(encoding="utf-8"))

print(f"Total standards: {len(standards)}")
for i, s in enumerate(standards):
    code = s.get("is_number")
    ver = s.get("current_version")
    title = s.get("title")
    status = s.get("status")
    qco = s.get("qco", {})
    source = s.get("source", {})
    verif = s.get("verification", {})
    params = s.get("structured_parameters", [])
    norm_refs = s.get("normative_references", [])
    
    print(f"\n[{i:02d}] {code} ({ver}) - Status: {status}")
    print(f"     Title: {title}")
    print(f"     Source URL: {source.get('portal_url')}")
    print(f"     Pub Ref: {source.get('official_publication_ref')}")
    print(f"     QCO: Covered={qco.get('is_covered_by_qco')} | Title={qco.get('qco_title')} | Order={qco.get('order_number')}")
    print(f"     Verification: Status={verif.get('verification_status')} | Method={verif.get('verification_method')}")
    print(f"     Normative Refs ({len(norm_refs)}): {norm_refs}")
    print(f"     Parameters ({len(params)}): {[p.get('parameter_name') for p in params]}")
