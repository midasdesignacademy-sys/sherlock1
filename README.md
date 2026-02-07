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

Endpoints: `GET /health`, `POST /investigate`, `GET /runs` (list), `GET /runs/{run_id}` (`?full=1` for full state), `POST /search` (hybrid search), `GET /events`, `GET /events/stream` (SSE), `GET /memory/patterns`, `GET /memory/episodes`, `GET /memory/history` (Fase 5), `WebSocket /ws`.

## UI (Fase 5)

```bash
 streamlit run ui/dashboard.py
```

Use "Run via API (monitored)" and the Activity tab when the API is running.

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
- `core/` – State, config, graph, monitors, graph_enhanced.
- `api/` – FastAPI app, WebSocket events.
- `rag/` – Embeddings, Chroma vector store, indexer.
- `knowledge_graph/` – Neo4j client, graph builder, pyvis visualizer.
- `cryptanalysis/` – Detectors, decoders, frequency, steganography.
- `pqms/` – ODOS, Guardian, Fidelity (rules-based).
- `core/memory/` – STM, LTM, Episodic, consolidation (Fase 3); MemoryManager + semantic query (Fase 5).
- `rag/hybrid_search.py` – Vector + graph hybrid search (Fase 2).

## Limitações conhecidas

- **PQMS**: ODOS e Guardian usam regras (evidência por entidade, contradições, variância de confidence); não há modelo de ética externo.
- **Contradições**: Detecção por regras (datas/números diferentes entre docs ligados); NLI opcional não incluído por padrão.
- **OCR**: Requer Tesseract instalado no sistema; sem Tesseract, PDFs escaneados não são convertidos em texto.
- **Checkpointing**: Requer `langgraph-checkpoint-sqlite` ou similar para persistência em disco; caso contrário usa MemorySaver em memória.
- **Esteganografia**: Suporte a LSB em PNG via biblioteca `stegano`; outros formatos não são analisados.
