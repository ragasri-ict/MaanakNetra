"""
MAANAKNETRA - Standards Graph Query Engine

Provides read-only queries over the NetworkX standards graph.

Important data-model rule:
- `source` = source STANDARD ID
- `target` = target STANDARD ID
- `provenance` = provenance/source of the relationship record

The previous implementation accidentally reused the key `source` twice
inside incoming relationships, causing values such as
"data/relations.json" to appear as if they were standards.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from .graph_builder import StandardsGraphBuilder


class StandardsGraphQueryEngine:
    """
    Read-only query interface over the standards relationship graph.
    """

    def __init__(self, builder: StandardsGraphBuilder):
        self.builder = builder
        self.graph = builder.get_graph()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _node_metadata(self, is_number: str) -> Dict[str, Any]:
        """Return safe metadata for a standard node."""
        if is_number not in self.graph:
            return {}

        node_data = dict(self.graph.nodes[is_number])

        return {
            "is_number": is_number,
            "title": node_data.get("title", ""),
            "status": node_data.get("status", "UNKNOWN"),
            "verification_status": node_data.get(
                "verification_status",
                node_data.get("verification", {}).get(
                    "verification_status",
                    "UNKNOWN",
                ),
            ),
            "scope": node_data.get("scope", ""),
            "category": node_data.get("category", ""),
            "publication_year": node_data.get(
                "publication_year",
                None,
            ),
        }

    def _edge_relationship(
        self,
        source_is: str,
        target_is: str,
        edge_data: Dict[str, Any],
        *,
        source_resolved: bool,
        target_resolved: bool,
    ) -> Dict[str, Any]:
        """
        Convert a graph edge into the public relationship representation.

        `source` and `target` ALWAYS refer to standard IDs.
        `provenance` refers to where the relationship record came from.
        """

        result: Dict[str, Any] = {
            "source": source_is,
            "source_title": (
                self.graph.nodes[source_is].get("title", "")
                if source_is in self.graph
                else "[UNRESOLVED REFERENCE]"
            ),
            "source_status": (
                self.graph.nodes[source_is].get("status", "UNKNOWN")
                if source_is in self.graph
                else "UNRESOLVED"
            ),
            "target": target_is,
            "target_title": (
                self.graph.nodes[target_is].get("title", "")
                if target_is in self.graph
                else "[UNRESOLVED REFERENCE]"
            ),
            "target_status": (
                self.graph.nodes[target_is].get("status", "UNKNOWN")
                if target_is in self.graph
                else "UNRESOLVED"
            ),
            "relationship_type": edge_data.get(
                "relationship_type",
                "OTHER",
            ),
            "evidence": edge_data.get("evidence", ""),
            "provenance": edge_data.get(
                "provenance",
                edge_data.get("source", "data/relations.json"),
            ),
            "source_resolved": source_resolved,
            "target_resolved": target_resolved,
        }

        if "notes" in edge_data:
            result["notes"] = edge_data["notes"]

        return result

    # ------------------------------------------------------------------
    # Outgoing relationships
    # ------------------------------------------------------------------

    def get_outgoing_relationships(
        self,
        is_number: str,
        include_unresolved: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Return relationships originating from `is_number`.

        Example:
            IS 14220 -> IS 9283
        """

        if is_number not in self.graph:
            return []

        results: List[Dict[str, Any]] = []

        for successor in self.graph.successors(is_number):
            edge_data = dict(self.graph.edges[is_number, successor])

            target_resolved = successor in self.graph

            if not include_unresolved and not target_resolved:
                continue

            results.append(
                self._edge_relationship(
                    source_is=is_number,
                    target_is=successor,
                    edge_data=edge_data,
                    source_resolved=True,
                    target_resolved=target_resolved,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Incoming relationships
    # ------------------------------------------------------------------

    def get_incoming_relationships(
        self,
        is_number: str,
    ) -> List[Dict[str, Any]]:
        """
        Return relationships pointing to `is_number`.

        Example:
            IS 14220:1994 -> IS 14220
        """

        if is_number not in self.graph:
            return []

        results: List[Dict[str, Any]] = []

        for predecessor in self.graph.predecessors(is_number):
            edge_data = dict(self.graph.edges[predecessor, is_number])

            source_resolved = predecessor in self.graph

            results.append(
                self._edge_relationship(
                    source_is=predecessor,
                    target_is=is_number,
                    edge_data=edge_data,
                    source_resolved=source_resolved,
                    target_resolved=True,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Related standards
    # ------------------------------------------------------------------

    def get_related_standards(
        self,
        is_number: str,
    ) -> Dict[str, Any]:
        """
        Return all adjacent standard IDs, both incoming and outgoing.

        IMPORTANT:
        The returned `related_standards` contains ONLY standard IDs.
        Provenance values such as "data/relations.json" are never included.
        """

        if is_number not in self.graph:
            return {
                "is_number": is_number,
                "found": False,
                "outgoing": [],
                "incoming": [],
                "related_standards": [],
            }

        outgoing = self.get_outgoing_relationships(
            is_number,
            include_unresolved=True,
        )
        incoming = self.get_incoming_relationships(is_number)

        related_ids: Set[str] = set()

        for relationship in outgoing:
            target = relationship.get("target")

            if (
                isinstance(target, str)
                and target
                and target != "data/relations.json"
            ):
                related_ids.add(target)

        for relationship in incoming:
            source = relationship.get("source")

            if (
                isinstance(source, str)
                and source
                and source != "data/relations.json"
            ):
                related_ids.add(source)

        related_ids.discard(is_number)

        return {
            "is_number": is_number,
            "found": True,
            "metadata": self._node_metadata(is_number),
            "outgoing": outgoing,
            "incoming": incoming,
            "related_standards": sorted(related_ids),
        }

    # ------------------------------------------------------------------
    # Relationship path
    # ------------------------------------------------------------------

    def get_relationship_path(
        self,
        source_is: str,
        target_is: str,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Return a shortest directed relationship path between two standards.

        Each item contains the source standard, target standard,
        relationship type and evidence.
        """

        if source_is not in self.graph:
            return None

        if target_is not in self.graph:
            return None

        try:
            path = self._shortest_path(source_is, target_is)
        except Exception:
            return None

        if not path or len(path) < 2:
            return []

        relationships: List[Dict[str, Any]] = []

        for source_node, target_node in zip(path, path[1:]):
            edge_data = dict(self.graph.edges[source_node, target_node])

            relationships.append(
                self._edge_relationship(
                    source_is=source_node,
                    target_is=target_node,
                    edge_data=edge_data,
                    source_resolved=True,
                    target_resolved=True,
                )
            )

        return relationships

    def _shortest_path(
        self,
        source_is: str,
        target_is: str,
    ) -> List[str]:
        """
        Internal BFS-style shortest path for a directed graph.

        NetworkX is already available, but keeping this helper simple
        makes behavior explicit and easy to test.
        """

        queue: List[str] = [source_is]
        visited: Set[str] = {source_is}
        parent: Dict[str, Optional[str]] = {
            source_is: None,
        }

        while queue:
            current = queue.pop(0)

            if current == target_is:
                break

            for neighbour in self.graph.successors(current):
                if neighbour in visited:
                    continue

                visited.add(neighbour)
                parent[neighbour] = current
                queue.append(neighbour)

        if target_is not in parent:
            return []

        path: List[str] = []
        current: Optional[str] = target_is

        while current is not None:
            path.append(current)
            current = parent[current]

        path.reverse()
        return path

    # ------------------------------------------------------------------
    # Dependency tree
    # ------------------------------------------------------------------

    def get_dependency_tree(
        self,
        is_number: str,
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """
        Build a recursive dependency tree from the supplied standard.

        Only outgoing relationships are traversed.
        """

        if is_number not in self.graph:
            return {
                "is_number": is_number,
                "found": False,
            }

        if max_depth < 0:
            max_depth = 0

        visited: Set[str] = set()

        return self._build_tree(
            is_number,
            current_depth=0,
            max_depth=max_depth,
            visited=visited,
        )

    def _build_tree(
        self,
        node_id: str,
        current_depth: int,
        max_depth: int,
        visited: Set[str],
    ) -> Dict[str, Any]:
        """
        Recursive dependency-tree builder.
        """

        node = self._node_metadata(node_id)

        tree: Dict[str, Any] = {
            "is_number": node_id,
            "title": node.get("title", ""),
            "status": node.get("status", "UNKNOWN"),
            "verification_status": node.get(
                "verification_status",
                "UNKNOWN",
            ),
            "normative_references": [],
            "test_methods": [],
            "safety_standards": [],
            "installation_practices": [],
            "allied_standards": [],
            "lifecycle_relationships": [],
            "other_relationships": [],
        }

        # Prevent cyclic expansion.
        if node_id in visited:
            return tree

        visited.add(node_id)

        if current_depth >= max_depth:
            return tree

        outgoing = self.get_outgoing_relationships(
            node_id,
            include_unresolved=True,
        )

        relationship_groups = {
            "NORMATIVE_REFERENCE": "normative_references",
            "TEST_METHOD": "test_methods",
            "SAFETY_STANDARD": "safety_standards",
            "INSTALLATION_PRACTICE": "installation_practices",
            "ALLIED_STANDARD": "allied_standards",
            "SUPERSEDES": "lifecycle_relationships",
            "SUPERSEDED_BY": "lifecycle_relationships",
        }

        for relationship in outgoing:
            relationship_type = relationship.get(
                "relationship_type",
                "OTHER",
            )

            target_id = relationship.get("target")

            # Ignore malformed/provenance-like IDs.
            if (
                not isinstance(target_id, str)
                or not target_id
                or target_id == "data/relations.json"
            ):
                continue

            item: Dict[str, Any] = {
                "target": target_id,
                "target_title": relationship.get(
                    "target_title",
                    "",
                ),
                "target_resolved": relationship.get(
                    "target_resolved",
                    target_id in self.graph,
                ),
                "relationship_type": relationship_type,
                "evidence": relationship.get(
                    "evidence",
                    "",
                ),
                "source": relationship.get(
                    "source",
                    node_id,
                ),
                "provenance": relationship.get(
                    "provenance",
                    "data/relations.json",
                ),
            }

            # Only recurse into standards that actually exist.
            if (
                relationship.get("target_resolved", False)
                and target_id in self.graph
            ):
                nested_tree = self._build_tree(
                    target_id,
                    current_depth=current_depth + 1,
                    max_depth=max_depth,
                    visited=set(visited),
                )

                item["dependencies"] = nested_tree

            destination = relationship_groups.get(
                relationship_type,
                "other_relationships",
            )

            tree[destination].append(item)

        return tree