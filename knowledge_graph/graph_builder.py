"""
SHERLOCK - Knowledge graph builder (writes state entities/relationships to Neo4j).
"""

from typing import Dict, Any, List
from loguru import logger

from core.state import InvestigationState
from knowledge_graph.neo4j_client import Neo4jClient


class KnowledgeGraphBuilder:
    """Builds Neo4j graph from state entities and relationships."""

    def __init__(self):
        self.client = Neo4jClient()

    def process(self, state: InvestigationState) -> InvestigationState:
        logger.info("[Agent 8] Building knowledge graph...")
        try:
            self.client.connect()
            entities = state.get("entities", {})
            relationships = state.get("relationships", [])

            for eid, ent in entities.items():
                self.client.create_entity_node(ent)
            for rel in relationships:
                self.client.create_relationship(rel)

            stats = self.client.get_graph_stats()
            state["graph_metadata"] = dict(stats)
            logger.info(f"Graph: {stats.get('node_count', 0)} nodes, {stats.get('relationship_count', 0)} edges")

            centrality = {}
            try:
                centrality = self.client.get_centrality_scores()
                state["centrality_scores"] = centrality
                state["graph_metadata"]["centrality"] = centrality
            except Exception as e:
                logger.warning(f"Centrality: {e}")
                state["centrality_scores"] = {}

            communities = {}
            try:
                communities = self.client.detect_communities()
                state["communities"] = communities
                state["graph_metadata"]["communities"] = communities
                state["graph_metadata"]["community_count"] = len(communities)
            except Exception as e:
                logger.warning(f"Communities: {e}")
                state["communities"] = {}

            top_entities = []
            if centrality and entities:
                sorted_eids = sorted(centrality.keys(), key=lambda x: centrality.get(x, 0), reverse=True)[:20]
                eid_to_community = {}
                for cid, eids in communities.items():
                    for eid in eids:
                        eid_to_community[eid] = cid
                for eid in sorted_eids:
                    ent = entities.get(eid) if isinstance(entities, dict) else None
                    text = ent.get("text", eid) if isinstance(ent, dict) else getattr(ent, "text", eid)
                    top_entities.append({
                        "entity": text,
                        "entity_id": eid,
                        "centrality": round(centrality.get(eid, 0), 4),
                        "community": eid_to_community.get(eid),
                    })
            state["graph_metadata"]["top_entities"] = top_entities

            bridges = []
            try:
                betweenness = self.client.get_betweenness()
                if betweenness:
                    sorted_b = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:15]
                    for eid, score in sorted_b:
                        ent = entities.get(eid) if isinstance(entities, dict) else None
                        text = ent.get("text", eid) if isinstance(ent, dict) else getattr(ent, "text", eid)
                        bridges.append({"entity": text, "entity_id": eid, "betweenness": round(score, 4)})
            except Exception as e:
                logger.warning(f"Betweenness: {e}")
            state["graph_metadata"]["bridges"] = bridges

            state["current_step"] = "knowledge_graph_complete"
        except Exception as e:
            logger.error(f"[Agent 8] Error: {e}")
            state["error_log"] = state.get("error_log", []) + [f"Knowledge graph error: {str(e)}"]
        finally:
            self.client.close()
        return state
