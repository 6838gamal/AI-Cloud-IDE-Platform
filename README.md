# CodeForge AI

A lightweight AI-powered Cloud IDE platform built as a single Modular Monolith.

## Quick Start

```bash
cp .env.example .env
docker compose up
```

Then open http://localhost:8000

## Features

- Google OAuth 2.0 login (optional — platform works without it)
- AI Agent with tools (read/write/edit/delete files, search, git diff)
- RAG for project understanding (lightweight, incremental indexing)
- Code Editor (CodeMirror with syntax highlighting)
- File Explorer
- Terminal (WebSocket-based)
- Preview (Run/Stop with status)
- Git integration
- Arabic/English with RTL/LTR support
- Dark/Light theme
- Python and Flutter project support
- Docker isolation for workspaces
- Graceful degradation for optional services

## Architecture

Single FastAPI application with modular structure:

- `app/modules/auth` — Google OAuth, sessions
- `app/modules/users` — User management
- `app/modules/projects` — Project CRUD
- `app/modules/files` — File operations
- `app/modules/ai` — AI Agent + tools
- `app/modules/rag` — RAG indexer + retriever
- `app/modules/terminal` — WebSocket terminal
- `app/modules/docker` — Container management
- `app/modules/git` — Git operations
- `app/modules/workspace` — Workspace lifecycle

## Environment Variables

See `.env.example` for all configuration options. All settings have defaults that work for development.

## Tech Stack

Python 3.13+, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Jinja2, Docker, WebSocket
