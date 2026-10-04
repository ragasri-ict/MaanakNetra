import json
from pathlib import Path

for fname in ["data/standards.json", "data/status.json", "data/relations.json"]:
    raw_bytes = Path(fname).read_bytes()
    try:
        decoded = raw_bytes.decode("utf-8")
        rep_count = decoded.count('\ufffd')
        if rep_count > 0:
            print(f"WARNING: U+FFFD found in {fname}: count = {rep_count}")
        else:
            print(f"{fname}: Valid UTF-8, no U+FFFD")
    except UnicodeDecodeError as e:
        print(f"ERROR: {fname} is not valid UTF-8: {e}")

standards = json.loads(Path("data/standards.json").read_text(encoding="utf-8"))
status_entries = json.loads(Path("data/status.json").read_text(encoding="utf-8"))
relations = json.loads(Path("data/relations.json").read_text(encoding="utf-8"))

print(f"\nTotal standards: {len(standards)}")
print(f"Total status: {len(status_entries)}")
print(f"Total relations: {len(relations)}")

status_map = {s["standard_code"]: s for s in status_entries}

print("\n--- STANDARDS AUDIT ---")
for i, s in enumerate(standards):
    code = s.get("is_number")
    title = s.get("title")
    scope = s.get("scope")
    curr_ver = s.get("current_version")
    pub_yr = s.get("publication_year")
    supersedes = s.get("supersedes")
    superseded_by = s.get("superseded_by")
    norm_refs = s.get("normative_references")
    source = s.get("source") or {}
    provenance = s.get("provenance") or {}
    params = s.get("parameters") or []
    
    issues = []
    
    # 1. Version and publication year consistency
    if not curr_ver.startswith(code):
        # Note: some like IS 14220:1994 has is_number="IS 14220:1994", current_version="IS 14220:1994"
        pass
    if str(pub_yr) not in curr_ver:
        issues.append(f"pub_yr {pub_yr} not in current_version '{curr_ver}'")
        
    # 2. Source / Provenance check
    pub_ref = source.get("official_publication_ref")
    if not pub_ref:
        issues.append("Missing source.official_publication_ref")
    elif str(pub_yr) not in pub_ref:
        issues.append(f"pub_yr {pub_yr} not in source.official_publication_ref '{pub_ref}'")
        
    portal_url = source.get("portal_url", "")
    if not portal_url:
        issues.append("Missing portal_url")
        
    if not source.get("curated_by"):
        issues.append("Missing source.curated_by")
    if not source.get("curator_notes"):
        issues.append("Missing source.curator_notes")
        
    # Check provenance
    if not provenance.get("issuing_body"):
        issues.append("Missing provenance.issuing_body")
    if not provenance.get("verification_method"):
        issues.append("Missing provenance.verification_method")
        
    # 3. Cross check with status.json
    st = status_map.get(code)
    if not st:
        issues.append(f"No entry in status.json for code '{code}'")
    else:
        st_ver = st.get("version")
        st_stat = st.get("status")
        st_eff_yr = st.get("effective_year")
        st_sup = st.get("superseded_by")
        
        if st_eff_yr != pub_yr:
            issues.append(f"status effective_year ({st_eff_yr}) != standards pub_year ({pub_yr})")
        if st_ver != curr_ver:
            issues.append(f"status version ({st_ver}) != standards current_version ({curr_ver})")
        if superseded_by != st_sup:
            issues.append(f"standards superseded_by ({superseded_by}) != status superseded_by ({st_sup})")
            
    # 4. Parameters check
    for p_idx, p in enumerate(params):
        if not p.get("parameter_name"):
            issues.append(f"param {p_idx} missing parameter_name")
        if not p.get("clause"):
            issues.append(f"param {p_idx} missing clause")
        if "nominal_value" not in p:
            issues.append(f"param {p_idx} missing nominal_value")
            
    if issues:
        print(f"[{i:02d}] {code:20} -> ISSUES: {issues}")
    else:
        print(f"[{i:02d}] {code:20} -> OK (Params: {len(params)}, NormRefs: {len(norm_refs)})")

print("\n--- STATUS AUDIT ---")
standards_codes = {s["is_number"] for s in standards}
for i, st in enumerate(status_entries):
    code = st.get("standard_code")
    ver = st.get("version")
    stat = st.get("status")
    sup = st.get("superseded_by")
    eff_y = st.get("effective_year")
    verif = st.get("verification_status")
    
    issues = []
    if stat == "SUPERSEDED":
        if not sup:
            issues.append("SUPERSEDED but superseded_by is None")
        elif sup not in standards_codes and sup not in status_map:
            issues.append(f"superseded_by '{sup}' not found in catalogue or status")
    if stat == "CURRENT" and sup is not None:
        issues.append(f"CURRENT standard has superseded_by: {sup}")
        
    if not (1900 <= eff_y <= 2030):
        issues.append(f"effective_year out of valid range: {eff_y}")
        
    if issues:
        print(f"[{i:02d}] {code:20} -> ISSUES: {issues}")

print("\n--- RELATIONS AUDIT ---")
for i, r in enumerate(relations):
    src = r.get("source")
    tgt = r.get("target")
    rtype = r.get("relationship_type")
    ev = r.get("evidence")
    unres = r.get("unresolved", False)
    
    issues = []
    if not src:
        issues.append("Missing source")
    elif src not in standards_codes and src not in status_map and not unres:
        issues.append(f"Source '{src}' not recognized")
        
    if not tgt:
        issues.append("Missing target")
    elif tgt not in standards_codes and tgt not in status_map and not unres:
        issues.append(f"Target '{tgt}' not recognized")
        
    if not rtype:
        issues.append("Missing relationship_type")
    if not ev:
        issues.append("Missing evidence")
        
    if issues:
        print(f"[{i:02d}] {src} -> {tgt} -> ISSUES: {issues}")

