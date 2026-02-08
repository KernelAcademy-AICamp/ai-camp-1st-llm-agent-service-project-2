# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LawLaw is a legal document SaaS service for law firms and enterprises. It uses LLM agents to automate document summarization, Q&A, case comparison, document recommendations, and risk analysis for Korean criminal law.

## Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Copy and configure environment variables
cp .env.example .env

# Install dependencies + register libs/apps as packages (editable mode)
pip install -e .
pip install -r requirements.txt

# Or with dev tools (pytest, black, ruff)
pip install -e ".[dev]"
pip install -r requirements.txt
```

### Django Backend (Port 8000)
```bash
cd apps/backend_api
python manage.py migrate --fake-initial
python manage.py runserver
```

### AI Service - FastAPI (Port 8001)
```bash
cd apps/ai_service
python main.py
```

### Frontend - React (Port 3000)
```bash
cd apps/web-frontend
npm install
npm start
npm test
```

### Data Pipeline Scripts
```bash
# Initialize database
python scripts/init_db.py

# Build Vector DB with BM25 index
python scripts/build_vectordb.py --source db --max_docs 100 --build_bm25

# Build BM25 index only
python scripts/build_bm25_index.py
```

### Testing
```bash
# Integration tests
./scripts/test_integration.sh

# Backend unit tests
cd apps/backend_api && pytest

# Frontend tests
cd apps/web-frontend && npm test
```

### Linting
```bash
# Python (configured in pyproject.toml)
black .
ruff check .
```

## Architecture

### Monorepo Structure

```
apps/
├── backend_api/     # Django REST API (auth, CRUD, proxies to AI service)
├── ai_service/      # FastAPI AI Service (RAG, agents, document analysis)
├── web-frontend/    # React + TypeScript + Tailwind
└── data-pipeline/   # ETL pipelines

libs/
├── rag_core/        # Shared RAG library (embeddings, LLM clients, retrieval)
└── domain_model/    # Shared Pydantic models
```

### AI Service Architecture (apps/ai_service/)

The AI service uses LangGraph for orchestrating LLM workflows with an adaptive multi-path agent system:

**Master Agent** (`agents/master_agent.py`):
- Classifies query complexity and routes to appropriate processing path
- 4-way routing: fast_path, medium_path, deep_path, thinking_path
- Uses `ExtendedMasterAgentState` for state management

**Key Components**:
- `agents/nodes/` - LangGraph nodes for each processing step
- `workflows/` - Workflow definitions (RAG, crawler, analytics graphs)
- `services/` - Business logic (OCR, document processing, risk analysis)
- `mcp/` - Model Context Protocol tools and resources
- `routers/v2/` - Main API endpoints (v1 is deprecated)

**RAG Pipeline** (`libs/rag_core/`):
- `embeddings/` - KoreanLegalEmbedder (local) or RemoteEmbedder (API)
- `retrieval/` - HybridRetriever combining semantic search + BM25
- `llm/` - Multi-provider LLM clients (OpenAI, Anthropic, Ollama)
- `llm/constitutional_chatbot.py` - Constitutional AI principles for legal responses

### Django Backend (apps/backend_api/)

Standard Django REST Framework structure:
- `users/` - Authentication, JWT, user management
- `documents/` - Document CRUD, analysis results
- `cases/` - Legal case management
- `precedents/` - Case law storage and search
- `organizations/` - Multi-tenant organization support
- `api/v1/ai_proxy.py` - Proxies requests to AI service

### Frontend (apps/web-frontend/)

React SPA with:
- `pages/AgentHub/` - Main chat interface with streaming SSE
- `components/agent-hub/` - Agent Hub UI components
- `contexts/AuthContext.tsx` - JWT authentication state

## Key Configuration

**Environment Variables** (see `apps/ai_service/config/settings.py`):
- `LLM_PROVIDER`: openai, anthropic, ollama
- `LLM_API_KEY`, `LLM_MODEL`
- `QDRANT_URL`, `QDRANT_COLLECTION` - Vector DB
- `EMBED_MODE`: local (768 dim) or remote (1024 dim)
- `DATABASE_URL` - PostgreSQL connection

**Vector DB**: Qdrant for semantic search, BM25 index for keyword search

## Git Workflow

- `main` - Production releases
- `develop` - Development integration
- `feature/[name]` - Feature branches (PR to develop)
- `hotfix/[name]` - Urgent fixes to main
