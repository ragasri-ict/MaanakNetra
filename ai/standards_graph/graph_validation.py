"""
Standards Relationship Graph Validation Engine for MAANAKNETRA.
Provides strict, deterministic validation checks for Indian Standards graph edges:
1. Duplicate edges
2. Self-referencing edges
3. Invalid relationship types
4. Source/target standards missing from dataset (unresolved references)
5. Edges without evidence
6. Edges without source/provenance
7. Conflicting reverse relationships

Does not silently repair invalid data; reports all discrepancies explicitly.
"""

from typing import Dict, Any, List, Set, Tuple

SUPPORTED_RELATIONSHIP_TYPES = {
    "NORMATIVE_REFERENCE",
    "TEST_METHOD",
    "SAFETY_STANDARD",
    "INSTALLATION_PRACTICE",
    "ALLIED_STANDARD",
    "SUPERSEDES",
    "SUPERSEDED_BY"
}


class GraphValidationError(Exception):
    """Raised when critical validation errors prevent graph generation."""
    pass


def validate_graph_data(
    standards: List[Dict[str, Any]],
    relations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Validates standards records and relationship edges against strict integrity rules.
    Returns:
        is_valid: bool
        validation_errors: List[Dict[str, Any]]
        unresolved_references: List[Dict[str, Any]]
        summary: Dict[str, int]
    """
    errors: List[Dict[str, Any]] = []
    unresolved_references: List[Dict[str, Any]] = []

    # Map available standard identifiers
    standard_ids: Set[str] = {
        s.get("is_number") for s in standards if s.get("is_number")
    }

    seen_edges: Set[Tuple[str, str, str]] = set()

    for idx, rel in enumerate(relations):
        source = rel.get("source")
        target = rel.get("target")
        rel_type = rel.get("relationship_type")
        evidence = rel.get("evidence")
        provenance = rel.get("provenance") or rel.get("source_doc") or "data/relations.json"

        # Check 1: Duplicate edges
        edge_key = (source, target, rel_type)
        if edge_key in seen_edges:
            errors.append({
                "error_type": "DUPLICATE_EDGE",
                "index": idx,
                "source": source,
                "target": target,
                "relationship_type": rel_type,
                "message": f"Duplicate edge detected between '{source}' and '{target}' with type '{rel_type}'."
            })
        seen_edges.add(edge_key)

        # Check 2: Self-referencing edges
        if source and target and source == target:
            errors.append({
                "error_type": "SELF_REFERENCING_EDGE",
                "index": idx,
                "source": source,
                "target": target,
                "relationship_type": rel_type,
                "message": f"Self-referencing relationship: standard '{source}' cannot link to itself."
            })

        # Check 3: Invalid relationship types
        if rel_type not in SUPPORTED_RELATIONSHIP_TYPES:
            errors.append({
                "error_type": "INVALID_RELATIONSHIP_TYPE",
                "index": idx,
                "source": source,
                "target": target,
                "relationship_type": rel_type,
                "message": f"Unsupported relationship type '{rel_type}'. Allowed types: {sorted(list(SUPPORTED_RELATIONSHIP_TYPES))}."
            })

        # Check 4: Source / Target standards missing from dataset (Unresolved References)
        source_missing = source not in standard_ids
        target_missing = target not in standard_ids
        if source_missing or target_missing:
            unresolved = {
                "source": source,
                "target": target,
                "relationship_type": rel_type,
                "evidence": evidence,
                "provenance": provenance,
                "missing_source": source_missing,
                "missing_target": target_missing,
                "unresolved_standard": target if target_missing else source,
                "reason": f"Standard '{target if target_missing else source}' is not present in data/standards.json."
            }
            unresolved_references.append(unresolved)

        # Check 5: Edges without evidence
        if not evidence or not str(evidence).strip():
            errors.append({
                "error_type": "MISSING_EVIDENCE",
                "index": idx,
                "source": source,
                "target": target,
                "relationship_type": rel_type,
                "message": f"Edge ({source} -> {target}) does not contain mandatory verification evidence."
            })

        # Check 6: Edges without source / provenance
        if not provenance or not str(provenance).strip():
            errors.append({
                "error_type": "MISSING_PROVENANCE",
                "index": idx,
                "source": source,
                "target": target,
                "relationship_type": rel_type,
                "message": f"Edge ({source} -> {target}) does not specify source or provenance."
            })

    # Check 7: Conflicting reverse relationships (e.g. mutual SUPERSEDES or A SUPERSEDES B & A SUPERSEDED_BY B)
    lifecycle_map: Dict[Tuple[str, str], str] = {
        (r.get("source"), r.get("target")): r.get("relationship_type")
        for r in relations if r.get("relationship_type") in ["SUPERSEDES", "SUPERSEDED_BY"]
    }
    for (src, tgt), rel_t in lifecycle_map.items():
        reverse_rel = lifecycle_map.get((tgt, src))
        if reverse_rel and reverse_rel == rel_t:
            errors.append({
                "error_type": "CONFLICTING_REVERSE_RELATIONSHIP",
                "source": src,
                "target": tgt,
                "message": f"Mutual conflict: both '{src}' and '{tgt}' declare '{rel_t}' against each other."
            })

    return {
        "is_valid": len(errors) == 0,
        "validation_errors": errors,
        "unresolved_references": unresolved_references,
        "summary": {
            "total_relations_inspected": len(relations),
            "error_count": len(errors),
            "unresolved_count": len(unresolved_references)
        }
    }
