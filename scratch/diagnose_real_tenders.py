import os
import sys
import time
import json

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from backend.ingestion import ingest_document
from ai.requirement_extractor import extract_requirements
from ai.retrieval.retrieval_pipeline import RetrievalPipeline
from ai.standards_graph.graph_builder import StandardsGraphBuilder
from ai.standards_graph.graph_queries import StandardsGraphQueryEngine
from ai.parameter_engine.compatibility import ParameterCompatibilityEngine
from ai.regulatory_intelligence import RegulatoryIntelligenceService
from ai.tender_linter import TenderLinter

def instrument_and_run(file_path):
    print("=" * 60)
    print(f"INSTRUMENTING TENDER: {file_path}")
    print(f"File Size: {os.path.getsize(file_path):,} bytes")
    print("=" * 60)

    total_start = time.perf_counter()

    # Stage 1: Parse
    t0 = time.perf_counter()
    doc = ingest_document(file_path)
    t_parse = time.perf_counter() - t0
    raw_text = getattr(doc, "extracted_text", "") or ""
    page_count = getattr(doc, "page_count", 0)
    print(f"[STAGE 1 - PARSE]           Time: {t_parse:.4f}s | Pages: {page_count}, Chars: {len(raw_text):,}")

    # Stage 2: Extract Requirements
    t0 = time.perf_counter()
    reqs_doc = extract_requirements(doc)
    t_extract = time.perf_counter() - t0
    extracted_reqs = reqs_doc.get("extracted_requirements", [])
    already_cited = reqs_doc.get("already_cited_standards", [])
    product_ctx = reqs_doc.get("product_context", {})
    print(f"[STAGE 2 - EXTRACT]         Time: {t_extract:.4f}s | Reqs: {len(extracted_reqs)}, Cited: {len(already_cited)}, Category: {product_ctx.get('category')}")

    # Initialize services (one-time or cached)
    retrieval = RetrievalPipeline()
    graph_builder = StandardsGraphBuilder()
    graph_query = StandardsGraphQueryEngine(graph_builder)
    param_engine = ParameterCompatibilityEngine()
    reg_service = RegulatoryIntelligenceService()
    with open("data/standards.json", "r", encoding="utf-8") as f:
        standards_by_num = {s["is_number"]: s for s in json.load(f)}
    linter = TenderLinter(reg_service, standards_by_num, graph_query, param_engine)

    # Stage 3: Retrieve Standards
    t0 = time.perf_counter()
    retrieved = retrieval.retrieve(reqs_doc, top_k=5)
    t_retrieve = time.perf_counter() - t0
    primary_is = retrieved[0]["is_number"] if retrieved else None
    top_score = retrieved[0]["applicability_score"] if retrieved else 0.0
    print(f"[STAGE 3 - RETRIEVE]        Time: {t_retrieve:.4f}s | Primary: {primary_is}, Top Score: {top_score:.3f}")

    # Stage 4: Parameter Match
    t0 = time.perf_counter()
    primary_std_rec = standards_by_num.get(primary_is, {}) if primary_is else {}
    compat_eval = param_engine.evaluate_standard_compatibility(
        standard=primary_std_rec,
        extracted_requirements=extracted_reqs,
        product_context=product_ctx,
    )
    t_param = time.perf_counter() - t0
    print(f"[STAGE 4 - PARAM MATCH]     Time: {t_param:.4f}s | Conflicting: {len(compat_eval.get('conflicting_requirements', []))}, Compliant: {len(compat_eval.get('compliant_requirements', []))}")

    # Stage 5: Graph Queries
    t0 = time.perf_counter()
    related = []
    if primary_is:
        related = graph_query.get_outgoing_relationships(primary_is, include_unresolved=False)
    t_graph = time.perf_counter() - t0
    print(f"[STAGE 5 - GRAPH]           Time: {t_graph:.4f}s | Allied Standards: {len(related)}")

    # Stage 6: Regulatory Checks (QCO / Status)
    t0 = time.perf_counter()
    qco_res = reg_service.get_qco_applicability(
        product_or_category=product_ctx.get("primary_item_name", "") or product_ctx.get("category", ""),
        is_number=primary_is,
    )
    for c in already_cited:
        reg_service.get_standard_status(c.get("standard_code", ""))
    t_reg = time.perf_counter() - t0
    print(f"[STAGE 6 - REGULATORY]      Time: {t_reg:.4f}s | QCO State: {qco_res.get('applicability_state')}")

    # Stage 7 & 8: Linter and Corrections
    t0 = time.perf_counter()
    findings, corrected = linter.lint(
        extracted_requirements=extracted_reqs,
        already_cited_standards=already_cited,
        product_context=product_ctx,
        primary_standard_id=primary_is,
        raw_tender_text=raw_text,
    )
    t_lint = time.perf_counter() - t0
    # Note: in linter.lint(), findings and corrected clauses are produced together
    t_linter = t_lint / 2
    t_corrections = t_lint / 2
    print(f"[STAGE 7 - LINTER]          Time: {t_linter:.4f}s | Findings: {len(findings)}")
    print(f"[STAGE 8 - CORRECTIONS]     Time: {t_corrections:.4f}s | Corrected Clauses: {len(corrected)}")

    t_total = time.perf_counter() - total_start
    print(f"[TOTAL TIME]                Time: {t_total:.4f}s")
    
    stages = {
        "parse": t_parse,
        "extract": t_extract,
        "retrieve": t_retrieve,
        "parameter_match": t_param,
        "graph": t_graph,
        "regulatory": t_reg,
        "linter": t_linter,
        "corrections": t_corrections,
    }
    slowest_stage = max(stages, key=stages.get)
    print(f"\nSlowest Stage: {slowest_stage.upper()} ({stages[slowest_stage]:.4f}s, {stages[slowest_stage]/t_total*100:.1f}% of total)")
    print("=" * 60)
    return stages, t_total

if __name__ == "__main__":
    f1 = os.path.join(WORKSPACE_ROOT, "demo", "open_tender_enquiry_2025-12-02-13-49-39.pdf")
    f2 = os.path.join(WORKSPACE_ROOT, "demo", "Tender_Document_55_FS2G.pdf")
    
    print("TEST 1: UCIL REAL TENDER (107 KB)")
    s1, tot1 = instrument_and_run(f1)
    
    print("\nTEST 2: SUBSTANTIALLY LARGER REAL TENDER (1.8 MB)")
    s2, tot2 = instrument_and_run(f2)
