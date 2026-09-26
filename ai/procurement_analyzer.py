"""
MAANAKNETRA - Procurement Analysis Orchestrator (Step 9B)

Integrates:
- Document Ingestion (backend/ingestion)
- Technical Requirement Extraction (ai/requirement_extractor)
- Hybrid Standard Retrieval (ai/retrieval)
- Standards Relationship Graph Expansion (ai/standards_graph)
- Parameter Compatibility Verification (ai/parameter_engine)
- Regulatory, Status, Amendment & QCO Intelligence (ai/regulatory_intelligence)

Generates complete, auditable TenderAnalysisResultDocument conforming to:
- contracts/analysis.schema.json
- contracts/finding.schema.json
"""

from __future__ import annotations

import os
import re
import time
import json
import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone

from backend.ingestion import ingest_document
from ai.requirement_extractor import extract_requirements
from ai.retrieval.retrieval_pipeline import RetrievalPipeline
from ai.standards_graph.graph_builder import StandardsGraphBuilder
from ai.standards_graph.graph_queries import StandardsGraphQueryEngine
from ai.parameter_engine.compatibility import ParameterCompatibilityEngine
from ai.regulatory_intelligence import (
    RegulatoryIntelligenceService,
    normalize_is_code,
    extract_base_is_code,
)
from ai.tender_linter import TenderLinter


class ProcurementAnalysisEngine:
    """
    End-to-end procurement audit and compliance orchestrator.
    """

    def __init__(
        self,
        standards_path: str = "data/standards.json",
        status_path: str = "data/status.json",
        qco_path: str = "data/qco.json",
        relations_path: str = "data/relations.json",
    ):
        self.standards_path = standards_path
        self.status_path = status_path
        self.qco_path = qco_path
        self.relations_path = relations_path

        # Initialize sub-services
        self.retrieval_pipeline = RetrievalPipeline(standards_path=self.standards_path)
        self.graph_builder = StandardsGraphBuilder(
            standards_path=self.standards_path,
            relations_path=self.relations_path,
        )
        self.graph_query = StandardsGraphQueryEngine(self.graph_builder)
        self.param_engine = ParameterCompatibilityEngine()
        self.reg_service = RegulatoryIntelligenceService(
            standards_path=self.standards_path,
            status_path=self.status_path,
            qco_path=self.qco_path,
        )

        with open(self.standards_path, "r", encoding="utf-8") as f:
            self.standards: List[Dict[str, Any]] = json.load(f)
        self.standards_by_num: Dict[str, Dict[str, Any]] = {
            s["is_number"]: s for s in self.standards
        }
        self.linter = TenderLinter(
            regulatory_service=self.reg_service,
            standards_by_num=self.standards_by_num,
            graph_query=self.graph_query,
            parameter_engine=self.param_engine,
        )

    def analyze(
        self,
        tender_source: Union[str, Dict[str, Any]],
        top_k: int = 5,
        document_title: Optional[str] = None,
        procuring_department: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end procurement analysis and produces a TenderAnalysisResultDocument.
        """
        file_name = "tender_document"
        file_hash_sha256 = None
        page_count = 1

        # 1. Ingestion & Requirement Extraction
        raw_tender_text = ""
        if isinstance(tender_source, str):
            file_name = os.path.basename(tender_source)
            if os.path.exists(tender_source):
                with open(tender_source, "rb") as f:
                    file_hash_sha256 = hashlib.sha256(f.read()).hexdigest()

            ingested_doc = ingest_document(tender_source)
            raw_tender_text = getattr(ingested_doc, "extracted_text", "") or getattr(ingested_doc, "full_text", "")
            page_count = getattr(ingested_doc, "page_count", 1)
            reqs_doc = extract_requirements(ingested_doc)
        elif isinstance(tender_source, dict):
            reqs_doc = tender_source
            raw_tender_text = reqs_doc.get("raw_text", "")
            file_name = reqs_doc.get("tender_metadata", {}).get("file_name", "tender_input.json")
            page_count = reqs_doc.get("tender_metadata", {}).get("page_count", 1)
        else:
            raise TypeError("tender_source must be a file path string or requirements dictionary.")

        extracted_requirements = reqs_doc.get("extracted_requirements", [])
        already_cited_standards = reqs_doc.get("already_cited_standards", [])
        product_context = reqs_doc.get("product_context", {})
        doc_metadata = reqs_doc.get("tender_metadata", {})

        analysis_id = f"ANALYSIS_{int(time.time())}"
        doc_title = (
            document_title
            or doc_metadata.get("document_title")
            or file_name
        )
        proc_dept = procuring_department or doc_metadata.get("procuring_department")

        tender_metadata = {
            "analysis_id": analysis_id,
            "document_title": doc_title,
            "file_name": file_name,
            "file_hash_sha256": file_hash_sha256,
            "page_count": max(1, page_count),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "procuring_department": proc_dept,
        }

        # 2. Retrieval & Recommended Standards
        retrieved_raw = self.retrieval_pipeline.retrieve(reqs_doc, top_k=top_k)
        primary_recommended = retrieved_raw[0] if retrieved_raw else None
        primary_is = primary_recommended["is_number"] if primary_recommended else None

        recommended_standards: List[Dict[str, Any]] = []
        for r in retrieved_raw:
            is_num = r.get("is_number")
            std_obj = self.standards_by_num.get(is_num, {})
            current_status = std_obj.get("status", "CURRENT")
            pub_year = std_obj.get("publication_year")

            # Format parameter_fit items
            param_fit_items = []
            for m in r.get("matched_requirements", []):
                param_fit_items.append({
                    "parameter_name": m.get("parameter_name", ""),
                    "tender_value": str(m.get("tender_value", "")),
                    "standard_value": str(m.get("evidence_clause", "")),
                    "fit_status": "COMPLIANT",
                    "tolerance_evaluation": None,
                })

            for u in r.get("unmatched_requirements", []):
                param_fit_items.append({
                    "parameter_name": u.get("parameter_name", ""),
                    "tender_value": str(u.get("tender_value", "")),
                    "standard_value": "NOT_SPECIFIED_IN_STANDARD",
                    "fit_status": "NOT_SPECIFIED_IN_TENDER",
                    "tolerance_evaluation": None,
                })

            source_dict = std_obj.get("source", {})
            source_rec = {
                "portal_url": source_dict.get("portal_url") or "https://www.services.bis.gov.in/",
                "official_publication_ref": source_dict.get("official_publication_ref") or is_num,
                "curated_by": source_dict.get("curated_by") or "VERIFIED_REGISTRY",
            }

            rec_item = {
                "standard": {
                    "is_number": is_num,
                    "title": std_obj.get("title", r.get("title", "")),
                    "year": pub_year,
                    "current_status": current_status,
                },
                "applicability_score": r.get("applicability_score", 0.0),
                "evidence": r.get("evidence", []),
                "matched_requirements": [m.get("requirement_id") for m in r.get("matched_requirements", []) if m.get("requirement_id")],
                "parameter_fit": param_fit_items,
                "explanation": r.get("reason", ""),
                "source": source_rec,
                "status": current_status,
                "confidence": round(r.get("applicability_score", 0.9), 2),
            }
            recommended_standards.append(rec_item)

        # 3. Standards Graph Expansion
        related_standards: List[Dict[str, Any]] = []
        if primary_is:
            outgoing = self.graph_query.get_outgoing_relationships(primary_is, include_unresolved=False)
            for rel in outgoing:
                rel_type = rel.get("relationship_type", "NORMATIVE_REFERENCE")
                if rel_type not in ["NORMATIVE_REFERENCE", "TEST_METHOD", "SAFETY_STANDARD", "INSTALLATION_PRACTICE", "SUPERSEDED_REPLACEMENT"]:
                    rel_type = "NORMATIVE_REFERENCE"

                t_status = rel.get("target_status", "CURRENT")
                if t_status not in ["CURRENT", "SUPERSEDED", "WITHDRAWN", "UNDER_REVISION"]:
                    t_status = "CURRENT"

                t_is = rel.get("target")
                t_qco = self.reg_service.get_qco_applicability(is_number=t_is)
                is_statutory = (
                    t_qco.get("applicability_state") == "APPLICABLE"
                    and t_qco.get("isi_mark_mandatory", False)
                )

                related_standards.append({
                    "is_number": t_is,
                    "title": rel.get("target_title", ""),
                    "relationship_type": rel_type,
                    "governing_primary_standard": primary_is,
                    "status": t_status,
                    "importance": "MANDATORY" if is_statutory else "RECOMMENDED",
                    "relevance_notes": rel.get("evidence", ""),
                })

        graph_summary = {
            "total_nodes": len(self.graph_builder.graph.nodes),
            "total_edges": len(self.graph_builder.graph.edges),
            "primary_clusters": [primary_is] if primary_is else [],
            "expansion_depth": 1,
        }

        # 4. Tender Linter: Execute Rules 1 - 6
        findings, corrected_clauses = self.linter.lint(
            extracted_requirements=extracted_requirements,
            already_cited_standards=already_cited_standards,
            product_context=product_context,
            primary_standard_id=primary_is,
            raw_tender_text=raw_tender_text,
        )

        # 5. Status & Certification Flags Evaluation
        evaluated_standards: set[str] = set()
        superseded_count = 0
        withdrawn_count = 0

        for cited in already_cited_standards:
            raw_cite = cited.get("raw_citation")
            code = cited.get("standard_code", "")
            year_cited = cited.get("year_cited")
            full_code = raw_cite or (f"{code}:{year_cited}" if year_cited else code)
            if not full_code:
                continue

            evaluated_standards.add(full_code)
            status_res = self.reg_service.get_standard_status(full_code)
            if status_res["status"] == "SUPERSEDED":
                superseded_count += 1
            elif status_res["status"] == "WITHDRAWN":
                withdrawn_count += 1

        for rec in recommended_standards:
            is_num = rec["standard"]["is_number"]
            evaluated_standards.add(is_num)
            st_res = self.reg_service.get_standard_status(is_num)
            if st_res["status"] == "SUPERSEDED":
                superseded_count += 1
            elif st_res["status"] == "WITHDRAWN":
                withdrawn_count += 1

        total_evaluated_standards = len(evaluated_standards)
        if total_evaluated_standards == 0:
            all_standards_current = False
        else:
            all_standards_current = (superseded_count == 0 and withdrawn_count == 0)

        status_flags = {
            "has_superseded_standards": superseded_count > 0,
            "has_withdrawn_standards": withdrawn_count > 0,
            "all_standards_current": all_standards_current,
            "superseded_count": superseded_count,
            "withdrawn_count": withdrawn_count,
        }

        # QCO & Mandatory Certification Audit
        primary_item = product_context.get("primary_item_name", "")
        primary_cat = product_context.get("category", "")
        qco_res = self.reg_service.get_qco_applicability(
            product_or_category=primary_item or primary_cat,
            is_number=primary_is,
        )

        qco_mandate_applicable = (
            qco_res.get("applicability_state") == "APPLICABLE"
            and qco_res.get("is_covered_by_qco", False)
        )

        isi_patterns = [
            r"\bisi\b",
            r"\bbis\s+mark\b",
            r"\bstandard\s+mark\b",
            r"\bscheme\s+i\b",
            r"\bcompulsory\s+registration\b",
        ]
        tender_raw_snippets = [raw_tender_text] if raw_tender_text else []
        for req in extracted_requirements:
            tender_raw_snippets.append(req.get("source_text", ""))
        for c in already_cited_standards:
            tender_raw_snippets.append(c.get("verbatim_citation", ""))
        all_tender_text = " ".join(filter(None, tender_raw_snippets)).lower()

        mandatory_isi_clause_present = any(
            re.search(pat, all_tender_text) is not None for pat in isi_patterns
        )

        qco_violation_risk = bool(qco_mandate_applicable and not mandatory_isi_clause_present)

        governing_qco_orders = []
        if qco_mandate_applicable and qco_res.get("order_title"):
            governing_qco_orders.append({
                "order_name": qco_res.get("order_title", ""),
                "order_number": qco_res.get("order_number", ""),
                "issuing_ministry": qco_res.get("issuing_ministry", "Department for Promotion of Industry and Internal Trade"),
                "effective_date": qco_res.get("effective_date", ""),
            })

        certification_flags = {
            "qco_mandate_applicable": qco_mandate_applicable,
            "mandatory_isi_clause_present": mandatory_isi_clause_present,
            "qco_violation_risk": qco_violation_risk,
            "governing_qco_orders": governing_qco_orders,
        }

        # 6. Standards Bill of Materials (Standards BOM)
        standards_bom: List[Dict[str, Any]] = []
        bom_idx = 1

        if primary_is:
            primary_std_rec = self.standards_by_num.get(primary_is, {})
            # Determine compliance status
            primary_cited = [c for c in already_cited_standards if extract_base_is_code(c.get("standard_code", "")) == extract_base_is_code(primary_is)]
            if primary_cited:
                is_outdated = any(c.get("standard_code") != primary_std_rec.get("current_version") for c in primary_cited)
                comp_status = "CITED_BUT_OUTDATED" if is_outdated else "ALREADY_CITED_CORRECTLY"
            else:
                comp_status = "MISSING_FROM_TENDER"

            standards_bom.append({
                "item_number": bom_idx,
                "is_number": primary_is,
                "title": primary_std_rec.get("title", ""),
                "role": "PRIMARY_PRODUCT_STANDARD",
                "is_mandatory_qco": qco_mandate_applicable,
                "compliance_status": comp_status,
                "action_required": "Update tender citation to active edition and require ISI mark license." if comp_status != "ALREADY_CITED_CORRECTLY" else "Maintain citation.",
            })
            bom_idx += 1

        # Allied / Graph standards
        for rel in related_standards:
            r_num = rel["is_number"]
            r_std = self.standards_by_num.get(r_num, {})
            r_qco = self.reg_service.get_qco_applicability(is_number=r_num)
            r_mandatory = r_qco.get("isi_mark_mandatory", False) if r_qco.get("applicability_state") == "APPLICABLE" else False

            role = "TEST_METHOD" if rel["relationship_type"] == "TEST_METHOD" else "SAFETY_CODE" if rel["relationship_type"] == "SAFETY_STANDARD" else "MATERIAL_SPECIFICATION"

            standards_bom.append({
                "item_number": bom_idx,
                "is_number": r_num,
                "title": r_std.get("title", rel.get("title", "")),
                "role": role,
                "is_mandatory_qco": r_mandatory,
                "compliance_status": "RECOMMENDED_ALLIED",
                "action_required": f"Reference as {rel['relationship_type'].lower().replace('_', ' ')} in quality assurance section.",
            })
            bom_idx += 1

        # 7. Risk Indicator Scorecard
        critical_count = sum(1 for f in findings if f["severity"] == "CRITICAL")
        high_count = sum(1 for f in findings if f["severity"] == "HIGH")
        medium_count = sum(1 for f in findings if f["severity"] == "MEDIUM")

        if critical_count > 0:
            risk_level = "CRITICAL"
        elif high_count > 0:
            risk_level = "HIGH"
        elif medium_count > 0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Compliance score: 100 - (critical*30 + high*15 + medium*5)
        raw_score = 100.0 - (critical_count * 30.0 + high_count * 15.0 + medium_count * 5.0)
        compliance_score = round(max(0.0, min(100.0, raw_score)), 1)

        summary_parts = []
        if critical_count > 0:
            summary_parts.append(f"{critical_count} critical statutory violation(s) (e.g. mandatory QCO omission)")
        if high_count > 0:
            summary_parts.append(f"{high_count} high-severity issue(s) (e.g. superseded standard cited)")
        if not summary_parts:
            summary_parts.append("All cited and applicable standards are active with mandatory certifications aligned.")

        risk_indicator = {
            "risk_level": risk_level,
            "compliance_score": compliance_score,
            "critical_issues_count": critical_count,
            "high_issues_count": high_count,
            "medium_issues_count": medium_count,
            "summary": "; ".join(summary_parts),
        }

        # 8. Human Review Flag
        human_review_required = bool(
            status_flags["has_superseded_standards"]
            or certification_flags["qco_violation_risk"]
            or qco_res.get("review_required", False)
            or any(f.get("requires_human_review", False) for f in findings)
        )

        return {
            "tender_metadata": tender_metadata,
            "extracted_requirements": extracted_requirements,
            "already_cited_standards": already_cited_standards,
            "recommended_standards": recommended_standards,
            "related_standards": related_standards,
            "graph_summary": graph_summary,
            "status_flags": status_flags,
            "certification_flags": certification_flags,
            "findings": findings,
            "standards_bom": standards_bom,
            "corrected_clause": corrected_clauses,
            "risk_indicator": risk_indicator,
            "human_review_required": human_review_required,
        }


def analyze_procurement_document(
    tender_source: Union[str, Dict[str, Any]],
    top_k: int = 5,
    document_title: Optional[str] = None,
    procuring_department: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function for procurement analysis orchestration.
    """
    engine = ProcurementAnalysisEngine()
    return engine.analyze(
        tender_source=tender_source,
        top_k=top_k,
        document_title=document_title,
        procuring_department=procuring_department,
    )
