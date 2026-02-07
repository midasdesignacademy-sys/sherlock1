"""
SHERLOCK - Neo4j client for knowledge graph.
"""

from typing import Dict, List, Any, Optional
from loguru import logger

from core.config import settings


def _entity_to_dict(entity: Any) -> Dict[str, Any]:
    if hasattr(entity, "model_dump"):
        d = entity.model_dump()
    elif isinstance(entity, dict):
        d = dict(entity)
    else:
        d = {
            "entity_id": getattr(entity, "entity_id", ""),
            "text": getattr(entity, "text", ""),
            "entity_type": getattr(entity, "entity_type", ""),
            "doc_id": getattr(entity, "doc_id", ""),
            "confidence": getattr(entity, "confidence", 1.0),
            "normalized_text": getattr(entity, "normalized_text", None),
        }
    if isinstance(d, dict):
        if "entity_type" not in d and "type" in d:
            d["entity_type"] = d["type"]
        docs = d.get("documents") or []
        if "doc_id" not in d and docs:
            d["doc_id"] = docs[0] if isinstance(docs[0], str) else str(docs[0])
        elif "doc_id" not in d:
            d["doc_id"] = ""
    return d


def _relationship_to_dict(rel: Any) -> Dict[str, Any]:
    if hasattr(rel, "model_dump"):
        return rel.model_dump()
    if isinstance(rel, dict):
        return rel
    return {
        "source_entity_id": getattr(rel, "source_entity_id", ""),
        "target_entity_id": getattr(rel, "target_entity_id", ""),
        "relationship_type": getattr(rel, "relationship_type", "RELATED"),
        "weight": getattr(rel, "weight", 1.0),
        "evidence_doc_ids": getattr(rel, "evidence_doc_ids", []),
    }


class Neo4jClient:
    """Neo4j client: connect, create Entity nodes and RELATED edges."""

    def __init__(self):
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self.database = settings.NEO4J_DATABASE
        self.driver = None

    def connect(self) -> None:
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        with self.driver.session(database=self.database) as session:
            session.run("RETURN 1 AS n").single()
        logger.info("Connected to Neo4j")

    def close(self) -> None:
        if self.driver:
            self.driver.close()
            self.driver = None

    def clear_database(self) -> None:
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.warning("Neo4j database cleared")

    def create_entity_node(self, entity: Any) -> None:
        d = _entity_to_dict(entity)
        q = """
        MERGE (e:Entity {entity_id: $entity_id})
        SET e.text = $text, e.entity_type = $entity_type, e.doc_id = $doc_id,
            e.confidence = $confidence, e.normalized_text = $normalized_text
        """
        with self.driver.session(database=self.database) as session:
            session.run(
                q,
                entity_id=d["entity_id"],
                text=d["text"],
                entity_type=d["entity_type"],
                doc_id=d["doc_id"],
                confidence=d.get("confidence", 1.0),
                normalized_text=d.get("normalized_text"),
            )

    def create_relationship(self, relationship: Any) -> None:
        r = _relationship_to_dict(relationship)
        # Ensure both nodes exist (we create nodes first)
        q = """
        MATCH (a:Entity {entity_id: $source_id})
        MATCH (b:Entity {entity_id: $target_id})
        MERGE (a)-[r:RELATED]->(b)
        SET r.type = $rel_type, r.weight = $weight, r.evidence_docs = $evidence_docs
        """
        with self.driver.session(database=self.database) as session:
            session.run(
                q,
                source_id=r["source_entity_id"],
                target_id=r["target_entity_id"],
                rel_type=r["relationship_type"],
                weight=r.get("weight", 1.0),
                evidence_docs=r.get("evidence_doc_ids", []),
            )

    def get_graph_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        with self.driver.session(database=self.database) as session:
            r = session.run("MATCH (n:Entity) RETURN count(n) AS c").single()
            stats["node_count"] = r["c"] if r else 0
            r = session.run("MATCH ()-[r:RELATED]->() RETURN count(r) AS c").single()
            rc = r["c"] if r else 0
            stats["relationship_count"] = rc
            stats["edge_count"] = rc
            result = session.run("MATCH (n:Entity) RETURN n.entity_type AS t, count(n) AS c")
            stats["entity_types"] = {rec["t"] or "": rec["c"] for rec in result}
        return stats

    def get_betweenness(self) -> Dict[str, float]:
        try:
            q = """
            CALL gds.betweenness.stream({
                nodeProjection: 'Entity',
                relationshipProjection: 'RELATED'
            })
            YIELD nodeId, score
            RETURN gds.util.asNode(nodeId).entity_id AS entity_id, score
            """
            out = {}
            with self.driver.session(database=self.database) as session:
                for rec in session.run(q):
                    out[rec["entity_id"]] = rec["score"]
            return out
        except Exception as e:
            logger.warning(f"Betweenness failed (GDS?): {e}")
            return {}

    def get_centrality_scores(self) -> Dict[str, float]:
        try:
            # GDS PageRank
            q = """
            CALL gds.pageRank.stream({
                nodeProjection: 'Entity',
                relationshipProjection: 'RELATED'
            })
            YIELD nodeId, score
            RETURN gds.util.asNode(nodeId).entity_id AS entity_id, score
            """
            out = {}
            with self.driver.session(database=self.database) as session:
                for rec in session.run(q):
                    out[rec["entity_id"]] = rec["score"]
            return out
        except Exception as e:
            logger.warning(f"Centrality failed (GDS?): {e}")
            return {}

    def detect_communities(self) -> Dict[int, List[str]]:
        try:
            q = """
            CALL gds.louvain.stream({
                nodeProjection: 'Entity',
                relationshipProjection: 'RELATED'
            })
            YIELD nodeId, communityId
            RETURN gds.util.asNode(nodeId).entity_id AS entity_id, communityId
            """
            comm: Dict[int, List[str]] = {}
            with self.driver.session(database=self.database) as session:
                for rec in session.run(q):
                    cid = rec["communityId"]
                    if cid not in comm:
                        comm[cid] = []
                    comm[cid].append(rec["entity_id"])
            return comm
        except Exception as e:
            logger.warning(f"Community detection failed: {e}")
            return {}

    def get_neighbors(self, entity_ids: List[str], limit_per_entity: int = 10) -> List[Dict[str, Any]]:
        """Return neighbors of given entities (for hybrid search expansion)."""
        if not entity_ids or not self.driver:
            return []
        out = []
        try:
            q = """
            MATCH (e:Entity)-[:RELATED]-(n:Entity)
            WHERE e.entity_id IN $ids
            RETURN DISTINCT n.entity_id AS entity_id, n.text AS text
            LIMIT $lim
            """
            with self.driver.session(database=self.database) as session:
                result = session.run(q, ids=entity_ids, lim=limit_per_entity * len(entity_ids))
                for rec in result:
                    out.append({"entity_id": rec["entity_id"], "text": rec["text"]})
        except Exception as e:
            logger.warning(f"get_neighbors failed: {e}")
        return out
