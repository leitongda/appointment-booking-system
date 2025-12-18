<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

## 语言规则 / Language Rules

**始终使用中文回复用户。** 代码、命令、技术术语可以保持英文，但所有解释、说明和对话都应使用中文。

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hospital appointment booking system (医院挂号系统) with three frontend applications and one backend service:
- **admin**: Institution management portal (机构端)
- **patient-h5**: Patient H5 web app
- **patient-miniapp**: Patient WeChat mini-program (Taro)
- **doctor**: Doctor portal
- **server**: FastAPI backend

## Development Commands

```bash
# Install dependencies
pnpm install

# Start development servers
pnpm dev:admin           # Admin portal - http://localhost:8005
pnpm dev:patient-h5      # Patient H5 - http://localhost:8002
pnpm dev:patient-miniapp # Mini-program (use WeChat DevTools)
pnpm dev:doctor          # Doctor portal - http://localhost:8003
pnpm dev:server          # Backend API - http://localhost:8000

# Build
pnpm build               # Build all
pnpm build:admin         # Build admin only

# Infrastructure (Docker)
docker-compose up -d postgres redis minio  # Start databases
```

### Backend Setup

```bash
cd apps/server
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Architecture

### Monorepo Structure (pnpm + Turborepo)

```
apps/
├── admin/          # Umi 4 + Ant Design Pro
├── patient-h5/     # Umi 4 + Ant Design Mobile
├── patient-miniapp/# Taro 3 (WeChat)
├── doctor/         # Umi 4 + Ant Design Pro
└── server/         # FastAPI + SQLAlchemy
    └── app/
        ├── api/v1/     # Route handlers
        ├── models/     # SQLAlchemy models
        ├── schemas/    # Pydantic schemas
        ├── services/   # Business logic
        ├── core/       # Config, auth, redis
        ├── db/         # Database session
        ├── middleware/ # Request/response handling
        └── tasks/      # Celery async tasks

packages/
├── api/            # @hospital/api - API client & types
└── shared/         # @hospital/shared - Shared utilities & components
```

### Tech Stack

**Frontend**: React 18, TypeScript, Umi 4, Ant Design 5, ProComponents, Zustand, TanStack Query, Taro 3

**Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.x (async), PostgreSQL 16, Redis 7, Celery, Alembic, MinIO

### Key Patterns

- Frontend apps import from `@hospital/api` for API calls and `@hospital/shared` for common utilities
- Backend uses async SQLAlchemy with dependency injection (`Depends(get_db)`)
- JWT authentication with role-based access control
- Unified API response format via middleware

## OpenSpec Workflow

For significant changes (new features, breaking changes, architecture), create a proposal:
1. Read `openspec/AGENTS.md` for instructions
2. Create change directory in `openspec/changes/[change-id]/`
3. Write `proposal.md`, `tasks.md`, and spec deltas
4. Run `openspec validate [change-id] --strict`
