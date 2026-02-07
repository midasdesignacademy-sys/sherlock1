"""
SHERLOCK - Entity Extraction Agent (Agent 3)
Soul: docs/agents/agent_3_soul.md
NER, co-occurrence, frequency, contexts, variations; Soul output contract.
"""

import re
import uuid
from collections import defaultdict
from typing import List, Dict, Any, Tuple
from loguru import logger

from core.state import InvestigationState, Entity, Relationship
from core.config import settings


def _load_spacy():
    try:
        import spacy
        nlp = spacy.load(settings.SPACY_MODEL_PT)
        return nlp, settings.SPACY_MODEL_PT
    except Exception:
        try:
            import spacy
            nlp = spacy.load(settings.SPACY_MODEL_EN)
            return nlp, settings.SPACY_MODEL_EN
        except Exception as e:
            logger.error(f"spaCy models not found: {e}. Run: python -m spacy download pt_core_news_lg")
            raise


class EntityExtractionAgent:
    """Agent 3: NER + regex; merge by canonical form; co-occurrence relationships with evidence_count, confidence."""

    def __init__(self):
        self.nlp, self.model_name = _load_spacy()
        self.entity_types = set(settings.ENTITY_TYPES)
        self.email_re = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        self.phone_re = re.compile(r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?[\s-]?)?\d{4,5}[\s-]?\d{4}\b")
        self.cpf_re = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
        self.cnpj_re = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")

    def process(self, state: InvestigationState) -> InvestigationState:
        logger.info("[Agent 3] Extracting entities...")
        try:
            extracted_text = state.get("extracted_text", {})
            if not extracted_text:
                return state

            raw_entities: List[Tuple[str, Dict[str, Any]]] = []
            for doc_id, text in extracted_text.items():
                if not text or len(text.strip()) < 10:
                    continue
                text_limited = text[:1000000]
                for e in self._extract_entities_one_doc(doc_id, text_limited):
                    raw_entities.append((doc_id, e))

            merged = self._merge_entities(raw_entities)
            entities_list = list(merged.values())
            entity_registry: Dict[str, List[str]] = {}
            for e in entities_list:
                key = (e.get("normalized_text") or e.get("text", "")).strip()
                if not key:
                    continue
                eid = e.get("entity_id")
                if key not in entity_registry:
                    entity_registry[key] = []
                if eid and eid not in entity_registry[key]:
                    entity_registry[key].append(eid)

            relationships = self._build_relationships(entities_list, raw_entities)
            rel_objs = []
            for r in relationships:
                rel_objs.append(
                    Relationship(
                        source_entity_id=r["source"],
                        target_entity_id=r["target"],
                        relationship_type=r.get("type", "ASSOCIATED_WITH"),
                        weight=r.get("weight", 1.0),
                        evidence_doc_ids=r.get("evidence_doc_ids", []),
                        evidence_count=r.get("evidence_count", 0),
                        context=r.get("context"),
                        confidence=r.get("confidence", 0.8),
                    )
                )

            state["entities"] = {e["entity_id"]: e for e in entities_list}
            state["entity_registry"] = entity_registry
            state["relationships"] = rel_objs
            state["current_step"] = "entity_extraction_complete"
            logger.info(f"[Agent 3] Entities: {len(entities_list)}, Relationships: {len(rel_objs)}")
        except Exception as e:
            logger.exception(f"[Agent 3] Error: {e}")
            state["error_log"] = state.get("error_log", []) + [f"Entity extraction error: {str(e)}"]
        return state

    def _extract_entities_one_doc(self, doc_id: str, text: str) -> List[Dict[str, Any]]:
        result = []
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ not in self.entity_types:
                continue
            norm = self._normalize(ent.text, ent.label_)
            start, end = ent.start_char, ent.end_char
            context = text[max(0, start - 50) : end + 50].replace("\n", " ")
            result.append({
                "text": ent.text,
                "type": ent.label_,
                "doc_id": doc_id,
                "start_char": start,
                "end_char": end,
                "confidence": 0.9,
                "normalized_text": norm,
                "context": context,
            })
        for m in self.email_re.finditer(text):
            result.append({
                "text": m.group(),
                "type": "EMAIL",
                "doc_id": doc_id,
                "start_char": m.start(),
                "end_char": m.end(),
                "confidence": 1.0,
                "normalized_text": m.group().lower(),
                "context": text[max(0, m.start() - 30) : m.end() + 30].replace("\n", " "),
            })
        for m in self.phone_re.finditer(text):
            result.append({
                "text": m.group(),
                "type": "PHONE",
                "doc_id": doc_id,
                "start_char": m.start(),
                "end_char": m.end(),
                "confidence": 1.0,
                "normalized_text": re.sub(r"\D", "", m.group()),
                "context": text[max(0, m.start() - 30) : m.end() + 30].replace("\n", " "),
            })
        for m in self.cpf_re.finditer(text):
            result.append({
                "text": m.group(),
                "type": "CPF",
                "doc_id": doc_id,
                "start_char": m.start(),
                "end_char": m.end(),
                "confidence": 1.0,
                "normalized_text": re.sub(r"\D", "", m.group()),
                "context": "",
            })
        for m in self.cnpj_re.finditer(text):
            result.append({
                "text": m.group(),
                "type": "CNPJ",
                "doc_id": doc_id,
                "start_char": m.start(),
                "end_char": m.end(),
                "confidence": 1.0,
                "normalized_text": re.sub(r"\D", "", m.group()),
                "context": "",
            })
        return result

    def _merge_entities(self, raw_entities: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
        key_to_entity: Dict[str, Dict[str, Any]] = {}
        key_to_docs: Dict[str, set] = defaultdict(set)
        key_to_contexts: Dict[str, List[str]] = defaultdict(list)
        key_to_variations: Dict[str, set] = defaultdict(set)

        for doc_id, e in raw_entities:
            norm = (e.get("normalized_text") or e.get("text", "")).strip()
            text = (e.get("text") or "").strip()
            if not norm:
                norm = text
            key = (norm, e.get("type", "OTHER"))
            k = f"{key[0]}|{key[1]}"
            key_to_docs[k].add(doc_id)
            if e.get("context"):
                key_to_contexts[k].append(e["context"][:200])
            key_to_variations[k].add(text)
            if k not in key_to_entity:
                key_to_entity[k] = {
                    "entity_id": f"e_{uuid.uuid4().hex[:8]}",
                    "text": norm,
                    "type": e.get("type", "OTHER"),
                    "confidence": e.get("confidence", 0.9),
                    "documents": [],
                    "frequency": 0,
                    "contexts": [],
                    "variations": [],
                    "normalized_text": norm,
                }
            key_to_entity[k]["frequency"] = len(key_to_docs[k])
            key_to_entity[k]["documents"] = sorted(key_to_docs[k])
            key_to_entity[k]["contexts"] = list(key_to_contexts[k])[:10]
            key_to_entity[k]["variations"] = sorted(key_to_variations[k])
        return key_to_entity

    def _build_relationships(
        self,
        entities_list: List[Dict[str, Any]],
        raw_entities: List[Tuple[str, Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        doc_to_eids: Dict[str, List[str]] = defaultdict(list)
        eid_to_entity: Dict[str, Dict[str, Any]] = {e["entity_id"]: e for e in entities_list}
        text_to_eid: Dict[str, str] = {}
        for e in entities_list:
            key = (e.get("normalized_text") or e.get("text", ""), e.get("type", ""))
            text_to_eid[f"{key[0]}|{key[1]}"] = e["entity_id"]
        for doc_id, e in raw_entities:
            k = f"{(e.get('normalized_text') or e.get('text', ''))}|{e.get('type', '')}"
            eid = text_to_eid.get(k)
            if eid:
                doc_to_eids[doc_id].append(eid)

        pair_to_evidence: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        for doc_id, eids in doc_to_eids.items():
            for i, a in enumerate(eids):
                for b in eids[i + 1:]:
                    if a == b:
                        continue
                    pair = tuple(sorted([a, b]))
                    pair_to_evidence[pair].append(doc_id)

        relationships = []
        for (a, b), evidence_doc_ids in pair_to_evidence.items():
            evidence_doc_ids = list(dict.fromkeys(evidence_doc_ids))
            type_a = eid_to_entity.get(a, {}).get("type", "")
            type_b = eid_to_entity.get(b, {}).get("type", "")
            rel_type = "ASSOCIATED_WITH" if type_a != type_b else "CO_OCCURRENCE"
            evidence_count = len(evidence_doc_ids)
            relationships.append({
                "source": a,
                "target": b,
                "type": rel_type,
                "evidence_doc_ids": evidence_doc_ids,
                "evidence_count": evidence_count,
                "confidence": min(0.95, 0.7 + 0.05 * min(evidence_count, 5)),
                "weight": float(evidence_count),
                "context": f"Co-occurred in {evidence_count} document(s)",
            })
        return relationships

    def _normalize(self, text: str, entity_type: str) -> str:
        t = " ".join((text or "").split())
        if entity_type in ("PERSON", "ORG", "GPE", "LOC"):
            t = t.title()
        return t
