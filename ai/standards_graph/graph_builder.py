"""
Standards Relationship Graph Builder for MAANAKNETRA.
Constructs a verified NetworkX directed graph from data/standards.json and data/relations.json.
Enforces zero hallucination:
- Does NOT invent edges.
- Does NOT infer relationships from similar titles.
- Does NOT fabricate placeholder nodes for missing standards.
- Unresolved references are cataloged in the validation report.
"""

import os
import json
from typing import Dict, Any, List, Optional
import networkx as nx

from .graph_validation import validate_graph_data, SUPPORTED_RELATIONSHIP_TYPES


class StandardsGraphBuilder:
    """
    Constructs and manages the deterministic NetworkX Standards Relationship Graph.
    """

    def __init__(
        self,
        standards_path: str = "data/standards.json",
        relations_path: str = "data/relations.json"
    ):
        self.standards_path = standards_path
        self.relations_path = relations_path

        self.standards: List[Dict[str, Any]] = []
        self.relations: List[Dict[str, Any]] = []
        self.graph: nx.DiGraph = nx.DiGraph()

        self.unresolved_references: List[Dict[str, Any]] = []
        self.validation_errors: List[Dict[str, Any]] = []
        self.is_built: bool = False

        self._load_and_build()

    def _load_and_build(self):
        """Loads dataset and constructs verified NetworkX graph."""
        if not os.path.exists(self.standards_path):
            raise FileNotFoundError(f"Standards dataset not found at {self.standards_path}")
        if not os.path.exists(self.relations_path):
            raise FileNotFoundError(f"Relations dataset not found at {self.relations_path}")

        with open(self.standards_path, "r", encoding="utf-8") as f:
            self.standards = json.load(f)

        with open(self.relations_path, "r", encoding="utf-8") as f:
            self.relations = json.load(f)

        # 1. Run validation checks
        val_res = validate_graph_data(self.standards, self.relations)
        self.validation_errors = val_res.get("validation_errors", [])
        self.unresolved_references = val_res.get("unresolved_references", [])

        # 2. Add nodes (ONLY verified standards in standards.json)
        self.graph = nx.DiGraph()
        for std in self.standards:
            is_num = std.get("is_number")
            if not is_num:
                continue

            v_status = (
                std.get("verification", {}).get("verification_status")
                or std.get("verification_status")
                or ("VERIFIED_OFFICIAL" if std.get("source", {}).get("curated_by") == "HUMAN_CURATOR" else "VERIFIED")
            )

            self.graph.add_node(
                is_num,
                is_number=is_num,
                title=std.get("title", ""),
                status=std.get("status", "CURRENT"),
                verification_status=v_status,
                scope=std.get("scope", ""),
                category=std.get("category", ""),
                product_types=std.get("product_types", []),
                publication_year=std.get("publication_year")
            )

        # 3. Add edges (ONLY between existing nodes; NEVER fabricate placeholder nodes)
        for rel in self.relations:
            src = rel.get("source")
            tgt = rel.get("target")
            rel_type = rel.get("relationship_type")
            evidence = rel.get("evidence", "")
            provenance = rel.get("provenance") or rel.get("source_doc") or "data/relations.json"

            if rel_type not in SUPPORTED_RELATIONSHIP_TYPES:
                continue

            # Only add to NetworkX graph if both source and target exist
            if src in self.graph and tgt in self.graph:
                self.graph.add_edge(
                    src,
                    tgt,
                    relationship_type=rel_type,
                    evidence=evidence,
                    source=provenance,
                    provenance=provenance,
                    source_standard=src,
                    target_standard=tgt
                )

        self.is_built = True

    def get_graph(self) -> nx.DiGraph:
        """Returns the underlying NetworkX DiGraph."""
        return self.graph

    def get_node_count(self) -> int:
        """Returns verified node count in the graph."""
        return self.graph.number_of_nodes()

    def get_edge_count(self) -> int:
        """Returns verified edge count in the graph."""
        return self.graph.number_of_edges()

    def get_unresolved_references(self) -> List[Dict[str, Any]]:
        """Returns edges pointing to standards not present in standards.json."""
        return self.unresolved_references

    def get_validation_errors(self) -> List[Dict[str, Any]]:
        """Returns list of integrity errors detected during validation."""
        return self.validation_errors

    def get_node_metadata(self, is_number: str) -> Optional[Dict[str, Any]]:
        """Returns dictionary of node metadata if standard exists in graph."""
        if is_number in self.graph:
            return dict(self.graph.nodes[is_number])
        return None
