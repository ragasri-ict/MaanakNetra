import json
from pathlib import Path

standards_path = Path("data/standards.json")
status_path = Path("data/status.json")
relations_path = Path("data/relations.json")

standards = json.loads(standards_path.read_text(encoding="utf-8"))
status = json.loads(status_path.read_text(encoding="utf-8"))
relations_raw = json.loads(relations_path.read_text(encoding="utf-8"))
relations = relations_raw if isinstance(relations_raw, list) else relations_raw.get("relations", [])

import json
from pathlib import Path

standards_path = Path("data/standards.json")
status_path = Path("data/status.json")
relations_path = Path("data/relations.json")

standards = json.loads(standards_path.read_text(encoding="utf-8"))
status = json.loads(status_path.read_text(encoding="utf-8"))
relations = json.loads(relations_path.read_text(encoding="utf-8"))

print(f"=== STANDARDS ({len(standards)}) ===")
std_by_is = {}
for idx, s in enumerate(standards):
    code = s.get("is_number")
    cur_v = s.get("current_version")
    pub_y = s.get("publication_year")
    title = s.get("title")
    source = s.get("source") or {}
    pub_ref = source.get("official_publication_ref")
    portal_url = source.get("portal_url")
    supersedes = s.get("supersedes", [])
    superseded_by = s.get("superseded_by")
    
    if code in std_by_is:
        print(f"DUPLICATE STANDARD CODE: {code}")
    std_by_is[code] = s
    
    anomalies = []
    if not code:
        anomalies.append("Missing is_number")
    if not cur_v:
        anomalies.append("Missing current_version")
    if not isinstance(pub_y, int) or pub_y < 1900 or pub_y > 2030:
        anomalies.append(f"Suspicious publication_year: {pub_y}")
    if pub_ref and str(pub_y) not in pub_ref:
        anomalies.append(f"pub_y {pub_y} not in pub_ref {pub_ref}")
    if not portal_url or not portal_url.startswith("https://www.services.bis.gov.in"):
        anomalies.append(f"Suspicious portal_url: {portal_url}")
    if not source.get("curated_by"):
        anomalies.append("Missing source.curated_by")
    if not source.get("curator_notes"):
        anomalies.append("Missing source.curator_notes")
        
    print(f"[{idx:2d}] {code:20} | {cur_v:24} | yr: {pub_y} | ref: {pub_ref} | anomalies: {anomalies}")

print(f"\n=== STATUS ENTRIES ({len(status)}) ===")
status_by_code = {}
for idx, st in enumerate(status):
    code = st.get("standard_code")
    ver = st.get("version")
    stat = st.get("status")
    sup = st.get("superseded_by")
    eff_y = st.get("effective_year")
    verif = st.get("verification_status")
    
    if code in status_by_code:
        print(f"DUPLICATE STATUS CODE: {code}")
    status_by_code[code] = st
    
    anomalies = []
    if not isinstance(eff_y, int) or eff_y < 1900 or eff_y > 2030:
        anomalies.append(f"Suspicious effective_year: {eff_y}")
    if stat == "SUPERSEDED" and not sup:
        anomalies.append("SUPERSEDED but superseded_by is None")
    if stat == "CURRENT" and sup:
        anomalies.append(f"CURRENT but superseded_by={sup}")
    if not verif:
        anomalies.append("Missing verification_status")
    
    # Cross-reference with standards.json
    matching_std = std_by_is.get(code)
    if matching_std:
        std_pub_y = matching_std.get("publication_year")
        std_cur_v = matching_std.get("current_version")
        if std_pub_y != eff_y and stat == "CURRENT":
            anomalies.append(f"Status eff_year {eff_y} != Standards pub_year {std_pub_y}")
        if std_cur_v != ver:
            anomalies.append(f"Status version {ver} != Standards cur_version {std_cur_v}")

    print(f"[{idx:2d}] {code:20} | {ver:24} | stat: {stat:10} | eff_yr: {eff_y} | sup: {sup} | anom: {anomalies}")

print(f"\n=== RELATIONS ENTRIES ({len(relations)}) ===")
for idx, r in enumerate(relations):
    src = r.get("source")
    tgt = r.get("target")
    rel_type = r.get("relationship_type")
    evidence = r.get("evidence")
    unres = r.get("unresolved", False)
    
    src_valid = (src in std_by_is) or (src in status_by_code)
    tgt_valid = (tgt in std_by_is) or (tgt in status_by_code)
    
    anomalies = []
    if not src_valid and not unres:
        anomalies.append(f"Unknown source '{src}'")
    if not tgt_valid and not unres:
        anomalies.append(f"Unknown target '{tgt}'")
    if not evidence:
        anomalies.append("Missing evidence")
    if not rel_type:
        anomalies.append("Missing relationship_type")
        
    if anomalies:
        print(f"[{idx:2d}] {src} -> {tgt} ({rel_type}) | ANOMALIES: {anomalies}")
    else:
        print(f"[{idx:2d}] OK: {src} -> {tgt} ({rel_type})")

