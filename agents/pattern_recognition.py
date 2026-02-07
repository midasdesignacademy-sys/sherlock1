"""
SHERLOCK - Pattern Recognition Agent (Agent 7)
Soul: docs/agents/agent_7_soul.md
Patterns (occurrences, confidence, evidence); anomalies (type, severity, entity, z_score).
"""

from collections import Counter
from typing import Dict, List, Any, Optional
from loguru import logger
import math

from core.state import InvestigationState, Pattern
from core.config import settings

try:
    import networkx as nx
except ImportError:
    nx = None


def _to_dict(obj) -> dict:
    return obj.model_dump() if hasattr(obj, "model_dump") else (obj if isinstance(obj, dict) else {})


def _build_network(entities: Any, relationships: List) -> "nx.Graph":
    G = nx.Graph()
    if isinstance(entities, dict):
        for eid, e in entities.items():
            G.add_node(eid, **(_to_dict(e) if not isinstance(e, dict) else e))
    for r in relationships:
        src = r.source_entity_id if hasattr(r, "source_entity_id") else r.get("source_entity_id")
        tgt = r.target_entity_id if hasattr(r, "target_entity_id") else r.get("target_entity_id")
        if src and tgt:
            w = r.weight if hasattr(r, "weight") else r.get("weight", 1)
            G.add_edge(src, tgt, weight=float(w))
    return G


def _z_score(value: float, mean: float, std: float) -> float:
    if std <= 0:
        return 0.0
    return (value - mean) / std


class PatternRecognitionAgent:
    """Agent 7: Patterns (temporal, network, frequency) and anomalies (statistical, contradictions). Soul-aligned."""

    def process(self, state: InvestigationState) -> InvestigationState:
        logger.info("[Agent 7] Pattern recognition...")
        try:
            patterns: List[Pattern] = list(state.get("patterns", []))
            outliers: List[str] = list(state.get("outliers", []))
            anomalies: List[Dict[str, Any]] = list(state.get("anomalies", []))
            entities = state.get("entities", {}) or {}
            relationships = state.get("relationships", [])
            timeline = state.get("timeline", [])
            extracted = state.get("extracted_text", {}) or {}

            if nx and entities and relationships:
                G = _build_network(entities, relationships)
                if G.number_of_nodes() > 0:
                    try:
                        degree = dict(nx.degree(G))
                        betweenness = nx.betweenness_centrality(G)
                        deg_values = list(degree.values())
                        mean_deg = sum(deg_values) / len(deg_values) if deg_values else 0
                        std_deg = math.sqrt(sum((x - mean_deg) ** 2 for x in deg_values) / len(deg_values)) if len(deg_values) > 1 else 0
                        for eid, d in sorted(degree.items(), key=lambda x: -x[1])[:10]:
                            z = _z_score(float(d), mean_deg, std_deg)
                            patterns.append(
                                Pattern(
                                    pattern_id=f"central_{eid}",
                                    pattern_type="high_degree",
                                    description=f"Entity degree {d}",
                                    entities_involved=[eid],
                                    severity="high" if z > 2 else "medium",
                                    metadata={"degree": d, "betweenness": betweenness.get(eid, 0)},
                                    occurrences=1,
                                    confidence=min(0.95, 0.5 + 0.1 * d),
                                    evidence=[eid],
                                )
                            )
                            if std_deg > 0 and z >= settings.OUTLIER_THRESHOLD:
                                anomalies.append({
                                    "type": "statistical_outlier",
                                    "description": f"Entity degree {d} (z={z:.2f})",
                                    "severity": "high" if z > 3 else "medium",
                                    "entity": eid,
                                    "z_score": round(z, 2),
                                })
                        try:
                            from networkx.algorithms.community import louvain_communities
                            communities = louvain_communities(G)
                            for i, comm in enumerate(communities):
                                if len(comm) >= getattr(settings, "MIN_CLUSTER_SIZE", 3):
                                    patterns.append(
                                        Pattern(
                                            pattern_id=f"cluster_{i}",
                                            pattern_type="community",
                                            description=f"Cluster with {len(comm)} entities",
                                            entities_involved=list(comm)[:20],
                                            severity="low",
                                            metadata={"size": len(comm)},
                                            occurrences=1,
                                            confidence=0.8,
                                            evidence=list(comm)[:5],
                                        )
                                    )
                        except Exception:
                            pass
                    except Exception as e:
                        logger.warning(f"Network analysis: {e}")

            timeline_events = [e for e in timeline if hasattr(e, "type") or isinstance(e, dict)]
            if timeline_events:
                type_sequence = []
                for e in timeline_events:
                    t = e.type if hasattr(e, "type") else (e.get("type") if isinstance(e, dict) else "EVENT")
                    type_sequence.append(t)
                seq_str = " -> ".join(type_sequence[:5])
                if len(type_sequence) >= 2:
                    patterns.append(
                        Pattern(
                            pattern_id="temporal_sequence_1",
                            pattern_type="temporal_sequence",
                            description=seq_str + (f" ({len(type_sequence)} events)" if len(type_sequence) > 5 else ""),
                            entities_involved=[],
                            doc_ids_involved=[],
                            severity="medium",
                            occurrences=1,
                            confidence=0.75,
                            evidence=type_sequence[:5],
                        )
                    )

            term_freq = Counter()
            for text in extracted.values():
                if text:
                    for w in text.lower().split():
                        if len(w) >= 4:
                            term_freq[w] += 1
            if term_freq:
                total = sum(term_freq.values())
                mean_c = total / len(term_freq)
                var_c = sum((c - mean_c) ** 2 for c in term_freq.values()) / len(term_freq) if term_freq else 0
                std_c = math.sqrt(var_c) if var_c > 0 else 0
                for term, c in term_freq.most_common(15):
                    if std_c > 0:
                        z = _z_score(float(c), mean_c, std_c)
                        if z >= settings.OUTLIER_THRESHOLD:
                            outliers.append(term)
                            anomalies.append({
                                "type": "statistical",
                                "description": f"Term '{term}' count {c} (z={z:.2f})",
                                "severity": "high" if z > 3 else "medium",
                                "entity": term,
                                "z_score": round(z, 2),
                            })
                    patterns.append(
                        Pattern(
                            pattern_id=f"freq_{term[:20]}",
                            pattern_type="frequency",
                            description=f"Term '{term}' count {c}",
                            severity="low",
                            metadata={"count": c},
                            occurrences=c,
                            confidence=min(0.9, 0.5 + c / 100),
                            evidence=[term],
                        )
                    )

            state["patterns"] = patterns
            state["outliers"] = outliers
            state["anomalies"] = anomalies
            state["current_step"] = "pattern_recognition_complete"
            logger.info(f"[Agent 7] Patterns: {len(patterns)}, Anomalies: {len(anomalies)}")
        except Exception as e:
            logger.error(f"[Agent 7] Error: {e}")
            state["error_log"] = state.get("error_log", []) + [f"Pattern recognition error: {str(e)}"]
        return state
