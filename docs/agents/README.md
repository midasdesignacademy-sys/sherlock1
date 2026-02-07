# SHERLOCK Agent Soul Architecture

Each agent has a `agent_N_soul.md` file defining identity, purpose, Zhi'Khora phase, reasoning, tools, I/O contract, and ethics.

| Agent | Soul File | Role | Zhi'Khora Phase |
|-------|-----------|------|-----------------|
| 1 | agent_1_soul.md | Document Ingestion Orchestrator | DISPERSÃO |
| 2 | agent_2_soul.md | Document Classifier | OBSERVAÇÃO |
| 3 | agent_3_soul.md | Entity Extractor | DISPERSÃO |
| 4 | agent_4_soul.md | Cryptanalysis Hunter | OBSERVAÇÃO |
| 5 | agent_5_soul.md | Semantic Linker | LIGAÇÃO (CORE) |
| 6 | agent_6_soul.md | Timeline Reconstructor | PADRÃO (Temporal) |
| 7 | agent_7_soul.md | Pattern Recognition Analyst | PADRÃO |
| 8 | agent_8_soul.md | Knowledge Graph Builder | PADRÃO (Network) |
| 9 | agent_9_soul.md | Intelligence Synthesis Coordinator | SÍNTESE |
| 10 | agent_10_soul.md | ODOS Guardian | VALIDAÇÃO |

Implementation follows the flat structure: `agents/<name>.py` with soul docs in `docs/agents/`.
