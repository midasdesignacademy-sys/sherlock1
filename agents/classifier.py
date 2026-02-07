"""
SHERLOCK - Document Classifier Agent (Agent 2)
Soul: docs/agents/agent_2_soul.md
Classifies documents by type, domain, language, priority; outputs Soul contract.
"""

import re
from typing import Any, Dict, List, Tuple
from loguru import logger

from core.state import InvestigationState, DocumentClassification

DOMAIN_KEYWORDS = {
    "finance": ["offshore", "transação", "valor", "pagamento", "orçamento", "cnpj", "cpf", "payment", "budget", "invoice", "transaction"],
    "legal": ["contrato", "cláusula", "juiz", "tribunal", "lei", "contract", "clause", "court", "law"],
    "technical": ["api", "software", "sistema", "desenvolvimento", "code", "implementation"],
    "corporate": ["reunião", "diretor", "empresa", "meeting", "ceo", "board"],
    "administrative": ["nota fiscal", "nota fiscal", "memorando", "memo", "relatório interno"],
}
DOC_TYPE_KEYWORDS = {
    "contract": ["contrato", "contract", "termo", "agreement", "cláusula", "parte"],
    "invoice": ["nota fiscal", "invoice", "nf-", "valor total", "valor r$"],
    "report": ["relatório", "report", "análise", "analysis", "conclusão"],
    "email": ["from:", "to:", "subject:", "re:", "assunto", "enviado por"],
    "technical": ["especificação", "spec", "requisito", "requirement"],
    "legal": ["petição", "sentença", "autos"],
}
PRIORITY_BOOST_KEYWORDS = ["confidencial", "restricted", "secret", "confidential", "urgente", "urgent"]
REFERENCE_PATTERN = re.compile(r"conforme\s+(anexo|doc\.?|documento)\s*[x\d]", re.I)


def _detect_language(text: str) -> Tuple[str, float]:
    if not text or len(text.strip()) < 20:
        return "unknown", 0.0
    try:
        import langdetect
        lang = langdetect.detect(text)
        return lang, 0.9
    except Exception:
        pass
    sample = (text or "")[:2000].lower()
    pt = sum(1 for w in [" de ", " da ", " do ", " que ", " e ", " o ", " a ", " em ", " para ", " com ", " não "] if w in sample)
    en = sum(1 for w in [" the ", " and ", " of ", " to ", " in ", " is ", " for ", " on ", " with "] if w in sample)
    if pt > en:
        return "pt", 0.7
    if en > pt:
        return "en", 0.7
    return "other", 0.5


def _suspicious_patterns(text: str) -> List[str]:
    found = []
    if re.search(r"[\█\*]{3,}", text):
        found.append("redaction_blocks")
    if re.search(r"\.\.\.\s*\.\.\.", text):
        found.append("repeated_ellipsis")
    if re.search(r"\[.*?\]{2,}", text):
        found.append("bracket_gaps")
    return found


def _estimated_relevance(priority_score: float) -> str:
    if priority_score >= 0.8:
        return "critical"
    if priority_score >= 0.6:
        return "high"
    if priority_score >= 0.4:
        return "medium"
    return "low"


class DocumentClassifierAgent:
    """Agent 2: Classify by type, domain, language, priority. Soul-aligned."""

    def process(self, state: InvestigationState) -> InvestigationState:
        logger.info("[Agent 2] Classifying documents...")
        try:
            classifications = dict(state.get("classifications", {}))
            extracted_text = state.get("extracted_text", {})
            document_metadata = state.get("document_metadata", {})

            doc_ids_with_text = [
                (doc_id, text, document_metadata.get(doc_id))
                for doc_id, text in extracted_text.items()
                if text is not None
            ]
            if not doc_ids_with_text:
                state["classifications"] = classifications
                state["current_step"] = "classification_complete"
                return state

            for idx, (doc_id, text, meta) in enumerate(doc_ids_with_text):
                text_stripped = (text or "").strip()
                word_count = len(text_stripped.split()) if text_stripped else 0

                if word_count < 50:
                    doc_type = "fragment"
                    doc_type_conf = 0.8
                    domain = "other"
                    domain_conf = 0.5
                    language, lang_conf = "unknown", 0.5
                    priority = 0.3
                    reasons = ["short_document"]
                    keywords = []
                else:
                    domain, domain_conf = self._classify_domain(text)
                    doc_type, doc_type_conf = self._classify_doc_type(text)
                    language, lang_conf = _detect_language(text)
                    keywords = self._extract_keywords(text)
                    suspicious = _suspicious_patterns(text)
                    priority, reasons = self._priority_score(doc_type, domain, keywords, suspicious, text, meta)
                    if language == "unknown":
                        priority = max(0.0, priority - 0.2)
                        reasons.append("language_unknown")

                relevance = _estimated_relevance(priority)
                processing_order = idx + 1

                classifications[doc_id] = DocumentClassification(
                    doc_id=doc_id,
                    domain=domain,
                    document_type=doc_type,
                    language=language,
                    priority_score=round(min(1.0, max(0.0, priority)), 2),
                    suspicious_patterns=reasons,
                    doc_type_confidence=doc_type_conf,
                    domain_confidence=domain_conf,
                    language_confidence=lang_conf,
                    priority_reasons=reasons,
                    keywords_detected=keywords[:20],
                    estimated_relevance=relevance,
                    processing_order=processing_order,
                )

                if isinstance(meta, dict) and doc_id in document_metadata:
                    document_metadata[doc_id] = dict(meta)
                    document_metadata[doc_id]["priority_score"] = round(min(1.0, max(0.0, priority)), 2)

            state["classifications"] = classifications
            if document_metadata:
                state["document_metadata"] = document_metadata
            state["current_step"] = "classification_complete"
            logger.info(f"[Agent 2] Classified {len(classifications)} documents")
        except Exception as e:
            logger.error(f"[Agent 2] Error: {e}")
            state["error_log"] = state.get("error_log", []) + [f"Classification error: {str(e)}"]
        return state

    def _classify_domain(self, text: str) -> Tuple[str, float]:
        lower = (text or "")[:5000].lower()
        scores = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            hits = sum(1 for k in keywords if k in lower)
            if hits:
                scores[domain] = hits
        if not scores:
            return "other", 0.5
        best = max(scores, key=scores.get)
        total = sum(scores.values())
        conf = min(0.95, 0.5 + 0.1 * scores.get(best, 0))
        return best, round(conf, 2)

    def _classify_doc_type(self, text: str) -> Tuple[str, float]:
        lower = (text or "")[:3000].lower()
        scores = {}
        for dtype, keywords in DOC_TYPE_KEYWORDS.items():
            hits = sum(1 for k in keywords if k in lower)
            if hits:
                scores[dtype] = hits
        if not scores or max(scores.values()) == 0:
            return "other", 0.5
        best = max(scores, key=scores.get)
        conf = min(0.95, 0.5 + 0.1 * scores.get(best, 0))
        return best, round(conf, 2)

    def _extract_keywords(self, text: str) -> List[str]:
        lower = (text or "")[:3000].lower()
        found = []
        for kw in PRIORITY_BOOST_KEYWORDS + ["offshore", "transação", "contrato", "nota fiscal"]:
            if kw in lower:
                found.append(kw)
        for domain_kws in DOMAIN_KEYWORDS.values():
            for k in domain_kws:
                if k in lower and k not in found:
                    found.append(k)
        return list(dict.fromkeys(found))[:30]

    def _priority_score(
        self,
        doc_type: str,
        domain: str,
        keywords: List[str],
        suspicious: List[str],
        text: str,
        meta: Any,
    ) -> Tuple[float, List[str]]:
        base = 0.5
        reasons = []
        if doc_type in ("contract", "invoice", "report"):
            base += 0.2
            reasons.append(f"doc_type_{doc_type}")
        if domain in ("finance", "legal"):
            base += 0.2
            reasons.append(f"domain_{domain}")
        for kw in PRIORITY_BOOST_KEYWORDS:
            if kw in (text or "").lower():
                base += 0.3
                reasons.append("contains_keyword_confidencial")
                break
        if "offshore" in (text or "").lower() or "transação" in (text or "").lower():
            base += 0.15
            reasons.append("high_relevance_keywords")
        if suspicious:
            base += 0.1 * min(len(suspicious), 3)
            reasons.append("suspicious_patterns")
        if REFERENCE_PATTERN.search(text or ""):
            base += 0.15
            reasons.append("references_other_docs")
        return min(1.0, base), reasons
