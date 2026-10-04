import json
import re
from pathlib import Path

raw_text = Path("data/standards.json").read_text(encoding="utf-8")
non_ascii = set(c for c in raw_text if ord(c) != (ord(c) & 0x7f))
print(f"Non-ASCII characters in standards.json: {[(hex(ord(c)), c) for c in non_ascii]}")

standards = json.loads(Path("data/standards.json").read_text(encoding="utf-8"))
status_entries = json.loads(Path("data/status.json").read_text(encoding="utf-8"))
relations = json.loads(Path("data/relations.json").read_text(encoding="utf-8"))

print("=== DEEP DATA VALIDATION ===")

std_map = {}
for i, s in enumerate(standards):
    code = s.get("is_number")
    std_map[code] = s
    title = s.get("title", "")
    pub_year = s.get("publication_year")
    curr_ver = s.get("current_version", "")
    status = s.get("status")
    supersedes = s.get("supersedes")
    superseded_by = s.get("superseded_by")
    norm_refs = s.get("normative_references", [])
    related_stds = s.get("related_standards", [])
    source = s.get("source", {})
    verification = s.get("verification", {})
    params = s.get("structured_parameters", [])
    
    # Check year
    if not isinstance(pub_year, int) or pub_year < 1900 or pub_year > 2026:
        print(f"[MALFORMED YEAR] Standard {code}: publication_year = {pub_year}")
        
    # Check version formatting
    if not re.search(r":\d{4}$", curr_ver):
        print(f"[SUSPICIOUS VERSION] Standard {code}: current_version = '{curr_ver}'")
    else:
        ver_year = int(curr_ver.split(":")[-1])
        if ver_year != pub_year:
            print(f"[VERSION/YEAR MISMATCH] Standard {code}: pub_year={pub_year} vs current_version='{curr_ver}'")

    # Check status & superseded_by
    if status == "SUPERSEDED":
        if not superseded_by:
            print(f"[LIFECYCLE ERROR] Standard {code} is SUPERSEDED but superseded_by is None")
    elif status == "CURRENT":
        if superseded_by is not None:
            print(f"[LIFECYCLE ERROR] Standard {code} is CURRENT but superseded_by = {superseded_by}")
            
    # Check URLs
    portal_url = source.get("portal_url", "")
    if not portal_url.startswith("https://"):
        print(f"[MALFORMED URL] Standard {code}: portal_url = '{portal_url}'")
        
    # Check source
    pub_ref = source.get("official_publication_ref", "")
    if not pub_ref:
        print(f"[MISSING PUB REF] Standard {code}")
        
    # Check parameters
    for p in params:
        p_name = p.get("parameter_name")
        clause = p.get("governing_clause")
        min_v = p.get("min_value")
        max_v = p.get("max_value")
        if min_v is not None and max_v is not None and min_v > max_v:
            print(f"[PARAM RANGE ERROR] Standard {code}, param '{p_name}': min={min_v} > max={max_v}")
        if not p.get("test_method_standard"):
            # Some parameters might not have test_method_standard
            pass

print(f"\nChecked {len(standards)} standards.")

print("\n--- STATUS ENTRIES CHECK ---")
status_map = {}
for i, st in enumerate(status_entries):
    code = st.get("standard_code")
    ver = st.get("version", "")
    stat = st.get("status")
    sup = st.get("superseded_by")
    eff_y = st.get("effective_year")
    verif = st.get("verification_status")
    
    if code in status_map:
        print(f"[DUPLICATE STATUS CODE] {code}")
    status_map[code] = st
    
    if not isinstance(eff_y, int) or eff_y < 1900 or eff_y > 2026:
        print(f"[MALFORMED EFF YEAR] Status {code}: effective_year = {eff_y}")
        
    if stat == "SUPERSEDED" and not sup:
        print(f"[STATUS ERROR] Status {code} is SUPERSEDED but superseded_by is None")
    if stat == "CURRENT" and sup:
        print(f"[STATUS ERROR] Status {code} is CURRENT but superseded_by = {sup}")
        
    # Check consistency with standards.json
    if code in std_map:
        std_obj = std_map[code]
        if std_obj.get("status") != stat:
            print(f"[STATUS MISMATCH] {code}: status.json has '{stat}' but standards.json has '{std_obj.get('status')}'")
        if std_obj.get("publication_year") != eff_y and stat == "CURRENT":
            print(f"[YEAR MISMATCH] {code}: status.json eff_year={eff_y} vs standards.json pub_year={std_obj.get('publication_year')}")

print(f"Checked {len(status_entries)} status entries.")

print("\n--- RELATIONS CHECK ---")
for i, r in enumerate(relations):
    src = r.get("source")
    tgt = r.get("target")
    rtype = r.get("relationship_type")
    ev = r.get("evidence", "")
    unres = r.get("unresolved", False)
    
    # Verify src exists in standards or status
    src_exists = (src in std_map) or (src in status_map) or any(s.get("current_version") == src for s in standards)
    tgt_exists = (tgt in std_map) or (tgt in status_map) or any(s.get("current_version") == tgt for s in standards)
    
    if not src_exists and not unres:
        print(f"[UNRESOLVED SOURCE] Relation [{i}]: src='{src}' not found and unres=False")
    if not tgt_exists and not unres:
        print(f"[UNRESOLVED TARGET] Relation [{i}]: tgt='{tgt}' not found and unres=False")
        
    if not ev or len(ev) < 10:
        print(f"[WEAK/MISSING EVIDENCE] Relation [{i}] {src} -> {tgt}: evidence='{ev}'")

print(f"Checked {len(relations)} relations.")
