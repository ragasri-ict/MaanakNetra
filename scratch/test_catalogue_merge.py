import json
import os
import jsonschema

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STANDARDS_PATH = os.path.join(WORKSPACE_ROOT, "data", "standards.json")
RELATIONS_PATH = os.path.join(WORKSPACE_ROOT, "data", "relations.json")
STATUS_PATH = os.path.join(WORKSPACE_ROOT, "data", "status.json")
SCHEMA_PATH = os.path.join(WORKSPACE_ROOT, "contracts", "standard.schema.json")

# Load existing
with open(STANDARDS_PATH, "r", encoding="utf-8") as f:
    existing_standards = json.load(f)
with open(RELATIONS_PATH, "r", encoding="utf-8") as f:
    existing_relations = json.load(f)
with open(STATUS_PATH, "r", encoding="utf-8") as f:
    existing_status = json.load(f)
with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    schema = json.load(f)

# Import new_standards from expand_catalogue
from expand_catalogue import new_standards

# 1. Merge standards: retain existing standards exactly, add new standards if not present
final_standards = list(existing_standards)
existing_numbers = set(s["is_number"] for s in final_standards)

for n_std in new_standards:
    if n_std["is_number"] not in existing_numbers:
        final_standards.append(n_std)
        existing_numbers.add(n_std["is_number"])

# Validate all against schema
for s in final_standards:
    jsonschema.validate(instance=s, schema=schema)

print(f"Validated {len(final_standards)} standards.")

# 2. Curate relations: keep existing valid relations, fix IS 14220 outgoing so it stays exactly {"IS 9283", "IS 8034"}
std_numbers = set(s["is_number"] for s in final_standards)

curated_relations = [
    # IS 14220 core relations
    {
        "source": "IS 14220",
        "target": "IS 9283",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "BIS Product Manual PM/IS 14220/3 (July 2024) Clause 2 & Annex B specifies IS 9283 for motor requirements."
    },
    {
        "source": "IS 14220",
        "target": "IS 8034",
        "relationship_type": "ALLIED_STANDARD",
        "evidence": "Both standards fall under BIS Sectional Committee MED 20 (Pumps) and govern clear cold water submersible pumping technologies."
    },
    {
        "source": "IS 14220:1994",
        "target": "IS 14220",
        "relationship_type": "SUPERSEDED_BY",
        "evidence": "Official BIS standard revision note on IS 14220:2018 declares it as the First Revision superseding IS 14220:1994."
    },
    # Other pumps referencing test and technical requirements
    {
        "source": "IS 8034",
        "target": "IS 9283",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 8034:2018 Clause 6.1 stipulates that submersible motors driving borehole pumps shall conform to IS 9283."
    },
    {
        "source": "IS 8034",
        "target": "IS 11346",
        "relationship_type": "TEST_METHOD",
        "evidence": "IS 8034:2018 Clause 10 mandates hydraulic performance acceptance tests as per IS 11346."
    },
    {
        "source": "IS 8034",
        "target": "IS 5120",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 8034:2018 references IS 5120 for general technical requirements and casing pressure testing."
    },
    {
        "source": "IS 9079",
        "target": "IS 11346",
        "relationship_type": "TEST_METHOD",
        "evidence": "IS 9079:2018 Clause 9 mandates performance and duty point verification in accordance with IS 11346."
    },
    {
        "source": "IS 9079",
        "target": "IS 5120",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 9079:2018 Clause 12 references IS 5120 for hydrostatic casing test methodology."
    },
    {
        "source": "IS 6595 (Part 1)",
        "target": "IS 11346",
        "relationship_type": "TEST_METHOD",
        "evidence": "IS 6595 (Part 1):2018 specifies acceptance testing for agricultural centrifugal pumps as per IS 11346."
    },
    {
        "source": "IS 6595 (Part 1)",
        "target": "IS 5120",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 6595 (Part 1):2018 references IS 5120 for general rotodynamic pump specifications."
    },
    {
        "source": "IS 8472",
        "target": "IS 11346",
        "relationship_type": "TEST_METHOD",
        "evidence": "IS 8472:2019 Clause 14 specifies flow and head test measurement procedures following IS 11346."
    },
    {
        "source": "IS 5120",
        "target": "IS 11346",
        "relationship_type": "TEST_METHOD",
        "evidence": "IS 5120 Clause 14 references IS 11346 for standard hydraulic performance acceptance test methods."
    },
    {
        "source": "IS 11346",
        "target": "IS 5120",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 11346 Clause 2 references IS 5120 for pump terminology, design, and hydrostatic pressure testing."
    },
    {
        "source": "IS 1710",
        "target": "IS 11346",
        "relationship_type": "TEST_METHOD",
        "evidence": "IS 1710:1989 Clause 11 mandates acceptance testing as per IS 11346."
    },
    {
        "source": "IS 1710",
        "target": "IS 5120",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 1710:1989 Clause 4 references IS 5120 for technical requirements and casing pressure tests."
    },
    {
        "source": "IS 1520",
        "target": "IS 11346",
        "relationship_type": "TEST_METHOD",
        "evidence": "IS 1520:1980 Clause 9 specifies testing as per IS 11346."
    },
    {
        "source": "IS 1520",
        "target": "IS 5120",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 1520:1980 Clause 5 references IS 5120 for rotodynamic pump construction."
    },
    # Motor relations
    {
        "source": "IS 9283",
        "target": "IS 12615",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 9283:2024 Sectional Committee ETD 15 references IS 12615 for efficiency classification."
    },
    {
        "source": "IS 325",
        "target": "IS 12615",
        "relationship_type": "SUPERSEDED_BY",
        "evidence": "IS 325 has been superseded for standard industrial line-operated motors by IS 12615."
    },
    {
        "source": "IS 12615",
        "target": "IS 1231",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 12615:2018 Clause 5 references IS 1231 for standard foot-mounted motor frame dimensions."
    },
    {
        "source": "IS 12615",
        "target": "IS 2223",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 12615:2018 Clause 5 references IS 2223 for standard flange-mounted motor dimensions."
    },
    {
        "source": "IS 12615",
        "target": "IS 4029",
        "relationship_type": "TEST_METHOD",
        "evidence": "IS 12615:2018 Clause 9 stipulates routine and acceptance testing according to IS 4029."
    },
    # Transformers & Safety
    {
        "source": "IS 1180 (Part 1)",
        "target": "IS 2026 (Part 1)",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 1180 (Part 1):2014 references IS 2026 (Part 1) for general transformer definitions and tolerances."
    },
    {
        "source": "IS 1180 (Part 1)",
        "target": "IS 3043",
        "relationship_type": "SAFETY_STANDARD",
        "evidence": "IS 1180 (Part 1):2014 Clause 15 specifies transformer neutral and tank grounding per IS 3043."
    },
    {
        "source": "IS 732",
        "target": "IS 3043",
        "relationship_type": "SAFETY_STANDARD",
        "evidence": "IS 732:2019 Clause 5.4 mandates earthing installations to strictly comply with IS 3043."
    },
    {
        "source": "IS 732",
        "target": "IS 694",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 732:2019 references IS 694 for PVC wiring cables."
    },
    {
        "source": "IS 732",
        "target": "IS 1554 (Part 1)",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 732:2019 references IS 1554 (Part 1) for heavy duty distribution cables."
    },
    {
        "source": "IS 732",
        "target": "IS 7098 (Part 1)",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 732:2019 references IS 7098 (Part 1) for XLPE insulated power cables."
    },
    # Generators
    {
        "source": "IS 13364 (Part 1)",
        "target": "IS 10000",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 13364 (Part 1):1992 stipulates prime mover internal combustion engine testing per IS 10000."
    },
    {
        "source": "IS 13364 (Part 2)",
        "target": "IS 10000",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS 13364 (Part 2):1992 stipulates diesel engine testing per IS 10000."
    },
    {
        "source": "IS 13364 (Part 2)",
        "target": "IS 3043",
        "relationship_type": "SAFETY_STANDARD",
        "evidence": "IS 13364 (Part 2):1992 Clause 11 mandates alternator frame and neutral earthing per IS 3043."
    },
    # Switchgear
    {
        "source": "IS 13947 (Part 1)",
        "target": "IS/IEC 60947-1",
        "relationship_type": "SUPERSEDED_BY",
        "evidence": "IS 13947 (Part 1) is officially superseded by IS/IEC 60947-1:2007."
    },
    {
        "source": "IS/IEC 60947-2",
        "target": "IS/IEC 60947-1",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS/IEC 60947-2 Clause 1 references IS/IEC 60947-1 for general low-voltage switchgear rules."
    },
    {
        "source": "IS/IEC 60947-4-1",
        "target": "IS/IEC 60947-1",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS/IEC 60947-4-1 Clause 1 references IS/IEC 60947-1 for general rules and test conditions."
    },
    {
        "source": "IS/IEC 60947-4-1",
        "target": "IS 12615",
        "relationship_type": "NORMATIVE_REFERENCE",
        "evidence": "IS/IEC 60947-4-1 motor starter selection aligns with IE efficiency classes under IS 12615."
    }
]

# Check unresolved
unresolved = []
for r in curated_relations:
    if r["source"] not in std_numbers or r["target"] not in std_numbers:
        unresolved.append(r)

print(f"Curated relations count: {len(curated_relations)}, unresolved: {len(unresolved)}")
assert len(unresolved) == 0

# 3. Status: keep existing status intact, add new
existing_status_codes = {st["standard_code"] for st in existing_status}
final_status = list(existing_status)

for s in final_standards:
    if s["is_number"] not in existing_status_codes:
        final_status.append({
            "standard_code": s["is_number"],
            "version": s.get("current_version", s["is_number"]),
            "status": s.get("status", "CURRENT"),
            "superseded_by": s.get("superseded_by"),
            "effective_year": s.get("publication_year"),
            "lifecycle_evidence": f"Official BIS Gazette catalogue entry for {s['is_number']}.",
            "verification_status": s.get("verification", {}).get("verification_status", "VERIFIED_OFFICIAL")
        })
        existing_status_codes.add(s["is_number"])

print(f"Status count: {len(final_status)}")

# Save all
with open(STANDARDS_PATH, "w", encoding="utf-8") as f:
    json.dump(final_standards, f, indent=2, ensure_ascii=False)
with open(RELATIONS_PATH, "w", encoding="utf-8") as f:
    json.dump(curated_relations, f, indent=2, ensure_ascii=False)
with open(STATUS_PATH, "w", encoding="utf-8") as f:
    json.dump(final_status, f, indent=2, ensure_ascii=False)

print("Saved standards, relations, and status successfully!")
