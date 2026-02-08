# SHERLOCK - Semantic Heuristic Engine for Recursive Linking, Obfuscation & Cryptanalysis Knowledge

Multi-agent system for investigative document analysis: encryption detection, semantic linking, entity extraction, knowledge graph, timeline, and ethics validation (PQMS stubs).

## Setup

1. Python 3.11+, create venv and install:
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   python -m spacy download pt_core_news_lg
   python -m spacy download en_core_web_lg
   ```

2. Docker (Neo4j + Chroma + API optional):
   ```bash
   docker-compose up -d
   # API (Fase 5): docker-compose up -d && docker-compose up -d api
   # Build app: docker-compose build api
   ```

3. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`, `NEO4J_PASSWORD`, etc.

## CLI

- **Run investigation** (documents in `data/uploads/`):
  ```bash
  python main.py investigate
  python main.py investigate --docs path/to/folder
  ```
- **Health check**: `python main.py health`
- **Clear Neo4j**: `python main.py clear`

## API (real-time events)

Run the FastAPI backend for monitored investigations and activity feed:

```bash
 uvicorn api.main:app --host 0.0.0.0 --port 8001
```

Endpoints: `GET /health`, `POST /investigate`, `GET /runs` (list), `GET /runs/{run_id}` (`?full=1` for full state), `POST /search` (hybrid search; body may include `investigation_id`), `GET /events`, `GET /events/stream` (SSE), `GET /memory/patterns`, `GET /memory/episodes`, `GET /memory/history` (Fase 5), `WebSocket /ws`.

**Investigações incrementais (Sprint 1):** `POST /investigations` (body: `name?`, `uploads_path?` — cria investigação e opcionalmente roda pipeline e persiste estado), `GET /investigations`, `GET /investigations/{id}`, `GET /investigations/{id}/state` (`?full=0` para resumo).

## UI

**Dashboard legado (abas):**
```bash
 streamlit run ui/dashboard.py
```

**UI MVP multipágina (investigações, Dashboard, Entities, Search, Graph, Timeline, etc.):**
```bash
 streamlit run ui/streamlit/app.py
```
Requer API em execução (`uvicorn api.main:app --port 8001`). No Dashboard, crie uma investigação (nome + path para `data/uploads`) e use as páginas com a investigação selecionada na sidebar.

## Tests

```bash
 pytest tests/ -v
```

## Checkpointing and resume

Set `CHECKPOINT_DIR` in `.env` (e.g. `CHECKPOINT_DIR=./checkpoints`) to persist state between nodes. Resume a run with:

```bash
python main.py investigate --resume <thread_id>
```

## Workflow (LangGraph)

Ingest → Classify → Entity extraction → Cryptanalysis → Semantic linker → Timeline → Pattern recognition → Knowledge graph → Synthesis → ODOS Guardian → (report | refinement).

## Structure

- `agents/` – Agents 1–10 (ingestion, classifier, entity, crypto, semantic, timeline, pattern, knowledge graph, synthesis, ODOS).
- `core/` – State, config, graph, monitors, graph_enhanced, investigation_store (persistência de investigações).
- `api/` – FastAPI app, WebSocket events.
- `ui/streamlit/` – UI MVP multipágina (Dashboard, Entities, Documents, Graph, Timeline, Search, Hypotheses, PQMS, Reports).
- `rag/` – Embeddings, Chroma vector store, indexer.
- `knowledge_graph/` – Neo4j client, graph builder, pyvis visualizer.
- `cryptanalysis/` – Detectors, decoders, frequency, steganography.
- `pqms/` – ODOS, Guardian, Fidelity (rules-based).
- `core/memory/` – STM, LTM, Episodic, consolidation (Fase 3); MemoryManager + semantic query (Fase 5).
- `rag/hybrid_search.py` – Vector + graph hybrid search (Fase 2).

## Investigações incrementais (plano)

Sprint 1 concluído: estado evolutivo (version, conflicts, etc.), store em `data/investigations/`, APIs `POST/GET /investigations` e `GET /investigations/{id}/state`, UI Streamlit multipágina. Próximos sprints: Redis + 202 job_id, Entity Resolution, Graph Merger, DeltaTracker, conflitos e ConflictResolver. Ver plano em `.cursor/plans/` ou documento "Investigações incrementais e frontend" para checklists por sprint.

## Limitações conhecidas

- **PQMS**: ODOS e Guardian usam regras (evidência por entidade, contradições, variância de confidence); não há modelo de ética externo.
- **Contradições**: Detecção por regras (datas/números diferentes entre docs ligados); NLI opcional não incluído por padrão.
- **OCR**: Requer Tesseract instalado no sistema; sem Tesseract, PDFs escaneados não são convertidos em texto.
- **Checkpointing**: Requer `langgraph-checkpoint-sqlite` ou similar para persistência em disco; caso contrário usa MemorySaver em memória.
- **Esteganografia**: Suporte a LSB em PNG via biblioteca `stegano`; outros formatos não são analisados.
