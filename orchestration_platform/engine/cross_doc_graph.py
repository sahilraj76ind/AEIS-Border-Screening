"""
Cross-Document Relational Consistency Graph Engine
===================================================
Builds an in-memory relational graph connecting demographic and biometric nodes
across multiple identity documents (Passport, Visa, Aadhaar, Selfie).
Detects cross-document relational fraud, name variations, DOB discrepancies,
and biometric inconsistencies.
"""

import re
import difflib
from typing import Dict, Any, List, Optional, Set, Tuple


def compute_token_overlap(name1: Optional[str], name2: Optional[str]) -> float:
    """Calculates token-level similarity between two name strings."""
    if not name1 or not name2:
        return 0.0
    t1 = set(re.findall(r'\w+', name1.upper()))
    t2 = set(re.findall(r'\w+', name2.upper()))
    if not t1 or not t2:
        return 0.0
    intersection = t1.intersection(t2)
    return len(intersection) / max(len(t1), len(t2))


def compute_string_similarity(str1: Optional[str], str2: Optional[str]) -> float:
    """Calculates Levenshtein similarity ratio between two strings."""
    if not str1 or not str2:
        return 0.0
    s1 = str1.strip().upper()
    s2 = str2.strip().upper()
    if s1 == s2:
        return 1.0
    return difflib.SequenceMatcher(None, s1, s2).ratio()


class IdentityRelationalGraph:
    """
    In-memory graph representing identity attributes and documents.
    Nodes: Documents (Passport, Visa, Aadhaar, Selfie) and Attributes (Name, DOB, Sex, Nationality, Face).
    Edges: Relationships and match scores between documents and shared attributes.
    """

    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self.discrepancy_conflicts: List[str] = []

    def add_node(self, node_id: str, label: str, node_type: str, metadata: Optional[Dict[str, Any]] = None):
        """Adds a node to the relational graph."""
        self.nodes[node_id] = {
            "id": node_id,
            "label": label,
            "type": node_type,  # 'document' or 'attribute'
            "metadata": metadata or {}
        }

    def add_edge(self, source: str, target: str, relationship: str, score: float = 1.0, is_conflict: bool = False):
        """Adds a directed edge connecting two nodes."""
        self.edges.append({
            "source": source,
            "target": target,
            "relationship": relationship,
            "score": round(score, 3),
            "is_conflict": is_conflict
        })


def build_and_evaluate_cross_document_graph(
    doc_results: Dict[str, Dict[str, Any]],
    face_verification_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates cross-document relational consistency across processed documents.

    Args:
        doc_results: Mapping of document key -> document OCR/validation output dictionary.
                      e.g., {'passport': passport_res, 'visa': visa_res, 'aadhaar': aadhaar_res}
        face_verification_result: Optional DeepFace verification output between selfie and doc.

    Returns:
        Dict:
            is_relational_consistent: bool
            graph_consistency_score: float (0.0 to 1.0)
            nodes: list of graph nodes
            edges: list of graph edges
            discrepancy_conflicts: list of conflict strings
            document_count: int
    """
    graph = IdentityRelationalGraph()

    # Collect extracted demographic attributes per document
    docs_demographics: Dict[str, Dict[str, Any]] = {}
    blacklist_hits: List[str] = []

    for doc_key, doc_data in doc_results.items():
        if not doc_data:
            continue

        doc_type = doc_data.get("document_type", doc_key)
        fields = doc_data.get("extracted_fields", {})
        blacklist = doc_data.get("blacklist_status", {})
        status_code = doc_data.get("status", "SUCCESS")

        # Add document node
        doc_node_id = f"doc_{doc_key}"
        graph.add_node(
            node_id=doc_node_id,
            label=f"{doc_type.upper()} Document",
            node_type="document",
            metadata={
                "document_type": doc_type,
                "format": doc_data.get("format"),
                "doc_number": fields.get("document_number"),
                "status": status_code
            }
        )

        if status_code == "ERROR":
            err_msg = f"{doc_type.upper()} Document OCR extraction failed or unreadable."
            graph.discrepancy_conflicts.append(err_msg)

        docs_demographics[doc_key] = {
            "name": fields.get("name"),
            "dob": fields.get("date_of_birth"),
            "sex": fields.get("sex"),
            "nationality": fields.get("nationality"),
            "doc_number": fields.get("document_number")
        }

        # Check watchlist
        if blacklist.get("is_blacklisted"):
            hit_msg = f"{doc_type.upper()} Document Number '{fields.get('document_number')}' matches Watchlist: {blacklist.get('matched_list')}"
            blacklist_hits.append(hit_msg)
            graph.discrepancy_conflicts.append(hit_msg)

    doc_keys = list(docs_demographics.keys())

    # If 0 or 1 document provided, baseline consistency is high unless watchlist hit
    if len(doc_keys) <= 1:
        score = 0.0 if blacklist_hits else 1.0
        return {
            "is_relational_consistent": len(graph.discrepancy_conflicts) == 0,
            "graph_consistency_score": score,
            "nodes": list(graph.nodes.values()),
            "edges": graph.edges,
            "discrepancy_conflicts": graph.discrepancy_conflicts,
            "document_count": len(doc_keys)
        }

    # Evaluate pairwise cross-document relationships
    pair_scores: List[float] = []

    for i in range(len(doc_keys)):
        for j in range(i + 1, len(doc_keys)):
            k1, k2 = doc_keys[i], doc_keys[j]
            d1, d2 = docs_demographics[k1], docs_demographics[k2]

            # 1. Compare Names
            n1, n2 = d1.get("name"), d2.get("name")
            if n1 and n2:
                sim_str = compute_string_similarity(n1, n2)
                sim_tok = compute_token_overlap(n1, n2)
                name_sim = max(sim_str, sim_tok)

                is_conflict = name_sim < 0.75
                if is_conflict:
                    conflict_msg = f"Name Discrepancy between {k1.upper()} ('{n1}') and {k2.upper()} ('{n2}')"
                    graph.discrepancy_conflicts.append(conflict_msg)

                graph.add_edge(
                    source=f"doc_{k1}",
                    target=f"doc_{k2}",
                    relationship="NAME_MATCH",
                    score=name_sim,
                    is_conflict=is_conflict
                )
                pair_scores.append(name_sim)

            # 2. Compare Date of Birth
            dob1, dob2 = d1.get("dob"), d2.get("dob")
            if dob1 and dob2:
                dob_match = (dob1 == dob2)
                is_conflict = not dob_match
                if is_conflict:
                    conflict_msg = f"DOB Discrepancy between {k1.upper()} ('{dob1}') and {k2.upper()} ('{dob2}')"
                    graph.discrepancy_conflicts.append(conflict_msg)

                graph.add_edge(
                    source=f"doc_{k1}",
                    target=f"doc_{k2}",
                    relationship="DOB_MATCH",
                    score=1.0 if dob_match else 0.0,
                    is_conflict=is_conflict
                )
                pair_scores.append(1.0 if dob_match else 0.0)

            # 3. Compare Sex
            sex1, sex2 = d1.get("sex"), d2.get("sex")
            if sex1 and sex2 and sex1 != "UNSPECIFIED" and sex2 != "UNSPECIFIED":
                sex_match = (sex1.upper() == sex2.upper())
                is_conflict = not sex_match
                if is_conflict:
                    conflict_msg = f"Sex Discrepancy between {k1.upper()} ('{sex1}') and {k2.upper()} ('{sex2}')"
                    graph.discrepancy_conflicts.append(conflict_msg)

                graph.add_edge(
                    source=f"doc_{k1}",
                    target=f"doc_{k2}",
                    relationship="SEX_MATCH",
                    score=1.0 if sex_match else 0.0,
                    is_conflict=is_conflict
                )
                pair_scores.append(1.0 if sex_match else 0.0)

    # 4. Facial Biometrics Node Evaluation
    if face_verification_result:
        face_match = face_verification_result.get("face_match", False)
        sim_score = face_verification_result.get("similarity_score", 0.0)
        face_status = face_verification_result.get("status", "OK")

        graph.add_node(
            node_id="face_biometric",
            label="Face Biometric Verification",
            node_type="biometric",
            metadata=face_verification_result
        )

        is_conflict = (face_status == "OK" and not face_match)
        if is_conflict:
            graph.discrepancy_conflicts.append("Facial Biometric Mismatch: Selfie does not match Document photo.")

        for k in doc_keys:
            graph.add_edge(
                source="face_biometric",
                target=f"doc_{k}",
                relationship="FACE_VERIFIED",
                score=sim_score,
                is_conflict=is_conflict
            )

        if face_status == "OK":
            pair_scores.append(sim_score)

    graph_consistency_score = round(sum(pair_scores) / len(pair_scores), 3) if pair_scores else 1.0
    if blacklist_hits:
        graph_consistency_score = min(graph_consistency_score, 0.20)

    is_relational_consistent = (len(graph.discrepancy_conflicts) == 0) and (graph_consistency_score >= 0.80)

    return {
        "is_relational_consistent": is_relational_consistent,
        "graph_consistency_score": graph_consistency_score,
        "nodes": list(graph.nodes.values()),
        "edges": graph.edges,
        "discrepancy_conflicts": graph.discrepancy_conflicts,
        "document_count": len(doc_keys)
    }
