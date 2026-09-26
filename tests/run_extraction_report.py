import os
import sys
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ingestion import ingest_document
from ai.requirement_extractor import extract_requirements
import jsonschema

doc = ingest_document("demo/sample_tender.pdf")
reqs_doc = extract_requirements(doc)

schema = json.load(open("contracts/requirements.schema.json", encoding="utf-8"))
jsonschema.validate(instance=reqs_doc, schema=schema)
print("VALIDATED_AGAINST_SCHEMA: TRUE")

print("\nEXTRACTED REQUIREMENTS TABLE")
print("----------------------------")
print(f"{'Category':<28} | {'Parameter':<38} | {'Value':<36} | {'Unit':<10} | {'Mandatory':<9} | {'Page':<4} | {'Conf':<4}")
print("-" * 140)
for r in reqs_doc["extracted_requirements"]:
    cat = r["category"]
    param = r["parameter_name"]
    val = r["value"][:34] + ".." if len(r["value"]) > 36 else r["value"]
    unit = r.get("unit") or "-"
    mand = str(r["is_mandatory"])
    page = str(r["source_location"]["source_page"])
    conf = str(r["extraction_confidence"])
    print(f"{cat:<28} | {param:<38} | {val:<36} | {unit:<10} | {mand:<9} | {page:<4} | {conf:<4}")

print("\nEXISTING IS REFERENCES TABLE")
print("----------------------------")
print(f"{'Raw Citation':<20} | {'Normalized Citation':<22} | {'Page':<4} | {'Confidence':<10}")
print("-" * 65)
for c in reqs_doc["already_cited_standards"]:
    raw = c["raw_citation"]
    norm = c["standard_code"]
    page = str(c["source_page"])
    conf = str(c["extraction_confidence"])
    print(f"{raw:<20} | {norm:<22} | {page:<4} | {conf:<10}")

print("\nEXTRACTED REQUIREMENTS (DEBUG DETAIL)")
print("-------------------------------------")
for r in reqs_doc["extracted_requirements"]:
    val_disp = r["value"]
    unit_disp = f" [{r['unit']}]" if r.get("unit") else ""
    print(f"[{r['category']}] {r['parameter_name']} = {val_disp}{unit_disp}")
    print(f'source: "{r["source_text"]}"')
    print(f"page: {r['source_location']['source_page']}")
    print(f"confidence: {r['extraction_confidence']}")
    print("")
