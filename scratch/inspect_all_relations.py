import json
from pathlib import Path

relations = json.loads(Path("data/relations.json").read_text(encoding="utf-8"))
standards = json.loads(Path("data/standards.json").read_text(encoding="utf-8"))
status_list = json.loads(Path("data/status.json").read_text(encoding="utf-8"))

std_dict = {s["is_number"]: s for s in standards}
status_dict = {s["standard_code"]: s for s in status_list}

print(f"Total relations: {len(relations)}")
for idx, r in enumerate(relations):
    src = r.get("source")
    tgt = r.get("target")
    rtype = r.get("relationship_type")
    evidence = r.get("evidence")
    unres = r.get("unresolved", False)
    
    src_title = std_dict.get(src, {}).get("title") or status_dict.get(src, {}).get("lifecycle_evidence", "")[:40]
    tgt_title = std_dict.get(tgt, {}).get("title") or status_dict.get(tgt, {}).get("lifecycle_evidence", "")[:40]
    
    print(f"[{idx:02d}] {src:18} --({rtype})--> {tgt:18} | Unresolved: {unres}")
    print(f"     Source Info: {src_title}")
    print(f"     Target Info: {tgt_title}")
    print(f"     Evidence: {evidence}")
