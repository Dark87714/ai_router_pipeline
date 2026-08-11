# AI Router Pipeline Microservice

A 3-tier FastAPI microservice for codebase compression, vector-based semantic intent routing, and sandboxed AST code execution.

## Pipeline Architecture
* **Model 1 (Compressor - `/compress`):** Crawls codebase directories, extracts AST code fragments, and builds vector embeddings in ChromaDB.
* **Model 2 (Router - `/route`):** Vector-searches natural language intent or code snippets against indexed logic rules using distance confidence thresholds.
* **Model 3 (Executor - `/execute`):** Inspects AST function signatures, validates code syntax, binds parameters, and executes logic in a sandboxed scope.

## Quickstart (Docker Container)
```bash
docker compose up --build -d