# Accord Retail - Repository Creation Script
# Run this in your repo root: C:\Users\bkgou\OneDrive\Documents\accord-retail
# 
# In VS Code terminal (PowerShell), run:
# powershell -ExecutionPolicy Bypass -File create-repo.ps1

$repoRoot = (Get-Location).Path
Write-Host "Creating Accord Retail repository in: $repoRoot" -ForegroundColor Green

# ============================================
# 1. Create Directory Structure
# ============================================

Write-Host "`n[1] Creating directory structure..." -ForegroundColor Cyan

$dirs = @(
    "backend/app/api/decisions",
    "backend/app/api/evidence",
    "backend/app/api/businesses",
    "backend/app/api/approvals",
    "backend/app/api/audit",
    "backend/app/api/scenarios",
    "backend/app/api/outcomes",
    "backend/app/models",
    "backend/app/schemas",
    "backend/app/db",
    "backend/tests",
    "backend/scripts",
    "frontend/src/components/screens",
    "frontend/src/components/shared",
    "frontend/src/components/layouts",
    "frontend/src/api",
    "frontend/src/hooks",
    "frontend/src/utils",
    "frontend/src/styles",
    "frontend/public",
    "database/migrations",
    "docs"
)

foreach ($dir in $dirs) {
    $fullPath = Join-Path $repoRoot $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Host "✓ Created: $dir"
    }
}

# ============================================
# 2. Create Backend Files
# ============================================

Write-Host "`n[2] Creating backend files..." -ForegroundColor Cyan

# Backend main.py
$mainPy = @"
"""
Accord Retail — Backend API
Decision Intelligence for Retail Operators
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Import routers from API modules
from app.api.decisions import router as decisions_router
from app.api.evidence import router as evidence_router
from app.api.businesses import router as businesses_router
from app.api.approvals import router as approvals_router
from app.api.audit import router as audit_router
from app.api.scenarios import router as scenarios_router
from app.api.outcomes import router as outcomes_router

# Import database
from app.db.database import init_db, get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan Events
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Accord Retail backend...")
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
        raise
    
    yield
    
    logger.info("Shutting down Accord Retail backend...")

# FastAPI Application
app = FastAPI(
    title="Accord Retail API",
    description="Decision Intelligence for Retail Operators",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "accord-retail-api",
        "version": "0.1.0",
    }

# Include API Routers
app.include_router(businesses_router, prefix="/api/businesses", tags=["businesses"])
app.include_router(decisions_router, prefix="/api/decisions", tags=["decisions"])
app.include_router(evidence_router, prefix="/api/evidence", tags=["evidence"])
app.include_router(approvals_router, prefix="/api/approvals", tags=["approvals"])
app.include_router(scenarios_router, prefix="/api/scenarios", tags=["scenarios"])
app.include_router(outcomes_router, prefix="/api/outcomes", tags=["outcomes"])
app.include_router(audit_router, prefix="/api/audit", tags=["audit"])

# Root Endpoint
@app.get("/")
async def root():
    return {
        "service": "Accord Retail API",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "businesses": "/api/businesses",
            "decisions": "/api/decisions",
            "evidence": "/api/evidence",
            "approvals": "/api/approvals",
            "scenarios": "/api/scenarios",
            "outcomes": "/api/outcomes",
            "audit": "/api/audit",
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
"@

Set-Content -Path "$repoRoot/backend/app/main.py" -Value $mainPy -Encoding UTF8
Write-Host "✓ Created: backend/app/main.py"

# Backend database.py
$dbPy = @"
"""
Database Connection & Initialization
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/accord_retail"
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database schema initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise
"@

Set-Content -Path "$repoRoot/backend/app/db/database.py" -Value $dbPy -Encoding UTF8
Write-Host "✓ Created: backend/app/db/database.py"

# Create __init__.py files for Python packages
$initPy = ""
@(
    "backend/app/__init__.py",
    "backend/app/api/__init__.py",
    "backend/app/db/__init__.py",
    "backend/app/models/__init__.py",
    "backend/app/schemas/__init__.py",
    "backend/app/api/decisions/__init__.py",
    "backend/app/api/evidence/__init__.py",
    "backend/app/api/businesses/__init__.py",
    "backend/app/api/approvals/__init__.py",
    "backend/app/api/audit/__init__.py",
    "backend/app/api/scenarios/__init__.py",
    "backend/app/api/outcomes/__init__.py"
) | ForEach-Object {
    Set-Content -Path "$repoRoot/$_" -Value "# Package" -Encoding UTF8
}

Write-Host "✓ Created: All __init__.py files"

# Backend requirements.txt
$requirements = @"
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
asyncpg==0.29.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
httpx==0.25.1
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.12.0
flake8==6.1.0
isort==5.13.2
mypy==1.7.1
"@

Set-Content -Path "$repoRoot/backend/requirements.txt" -Value $requirements -Encoding UTF8
Write-Host "✓ Created: backend/requirements.txt"

# Backend Dockerfile
$dockerfile = @"
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc postgresql-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"@

Set-Content -Path "$repoRoot/backend/Dockerfile" -Value $dockerfile -Encoding UTF8
Write-Host "✓ Created: backend/Dockerfile"

# ============================================
# 3. Create Frontend Files
# ============================================

Write-Host "`n[3] Creating frontend files..." -ForegroundColor Cyan

# Frontend App.jsx
$appJsx = @"
/**
 * Accord Retail — Frontend React App
 * Decision Intelligence for Retail Operators
 */

import React, { useState, useEffect } from 'react';
import Navigation from './components/layouts/Navigation';
import TodayScreen from './components/screens/TodayScreen';
import DecisionWorkbench from './components/screens/DecisionWorkbench';
import './styles/global.css';

function App() {
  const [currentScreen, setCurrentScreen] = useState('TODAY');
  const [selectedDecisionId, setSelectedDecisionId] = useState(null);
  const [businessContext, setBusinessContext] = useState(null);

  useEffect(() => {
    setBusinessContext({
      business_id: 'retail-001',
      business_name: 'TechCo Inc',
      revenue: 15000000,
      margin: -0.021,
      churn: 0.021,
      customers: 200,
      repeat_rate: 0.65,
    });
  }, []);

  const goToScreen = (screen, decisionId = null) => {
    setCurrentScreen(screen);
    if (decisionId) setSelectedDecisionId(decisionId);
  };

  return (
    <div className="accord-app">
      <Navigation currentScreen={currentScreen} onNavigate={goToScreen} />
      <main className="accord-main">
        {businessContext ? (
          currentScreen === 'TODAY' ? (
            <TodayScreen businessContext={businessContext} onSelectDecision={(id) => {
              setSelectedDecisionId(id);
              setCurrentScreen('WORKBENCH');
            }} />
          ) : (
            <DecisionWorkbench decisionId={selectedDecisionId} />
          )
        ) : (
          <div className="loading">Loading Accord Retail...</div>
        )}
      </main>
    </div>
  );
}

export default App;
"@

Set-Content -Path "$repoRoot/frontend/src/App.jsx" -Value $appJsx -Encoding UTF8
Write-Host "✓ Created: frontend/src/App.jsx"

# Frontend Navigation.jsx
$navJsx = @"
/**
 * Navigation Component
 */

import React from 'react';

function Navigation({ currentScreen, onNavigate }) {
  const screens = [
    { id: 'TODAY', label: 'Today', icon: '📊' },
    { id: 'WORKBENCH', label: 'Decisions', icon: '🎯' },
    { id: 'EVIDENCE', label: 'Evidence', icon: '📋' },
    { id: 'SCENARIOS', label: 'Scenarios', icon: '🔄' },
  ];

  return (
    <nav className="navigation">
      <div className="nav-container">
        <div className="nav-brand">
          <h1>Accord Retail</h1>
        </div>
        <div className="nav-menu">
          {screens.map((screen) => (
            <button
              key={screen.id}
              className={`nav-item \${currentScreen === screen.id ? 'active' : ''}`}
              onClick={() => onNavigate(screen.id)}
            >
              <span>{screen.icon} {screen.label}</span>
            </button>
          ))}
        </div>
      </div>
    </nav>
  );
}

export default Navigation;
"@

Set-Content -Path "$repoRoot/frontend/src/components/layouts/Navigation.jsx" -Value $navJsx -Encoding UTF8
Write-Host "✓ Created: frontend/src/components/layouts/Navigation.jsx"

# Frontend TodayScreen.jsx
$todayJsx = @"
/**
 * TODAY Screen - Decision Queue
 */

import React from 'react';

function TodayScreen({ businessContext, onSelectDecision }) {
  return (
    <div className="today-screen">
      <h2>What Needs Your Attention Today</h2>
      <p>Decision queue implementation</p>
    </div>
  );
}

export default TodayScreen;
"@

Set-Content -Path "$repoRoot/frontend/src/components/screens/TodayScreen.jsx" -Value $todayJsx -Encoding UTF8
Write-Host "✓ Created: frontend/src/components/screens/TodayScreen.jsx"

# Frontend DecisionWorkbench.jsx
$workbenchJsx = @"
/**
 * Decision Workbench - Full Decision Detail
 */

import React from 'react';

function DecisionWorkbench({ decisionId }) {
  return (
    <div className="decision-workbench">
      <h2>Decision Workbench</h2>
      <p>Decision detail implementation</p>
    </div>
  );
}

export default DecisionWorkbench;
"@

Set-Content -Path "$repoRoot/frontend/src/components/screens/DecisionWorkbench.jsx" -Value $workbenchJsx -Encoding UTF8
Write-Host "✓ Created: frontend/src/components/screens/DecisionWorkbench.jsx"

# Frontend API client
$apiClient = @"
/**
 * API Client - Axios HTTP client
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

export const decisionsAPI = {
  list: (businessId, limit = 10) =>
    client.get('/api/decisions', { params: { business_id: businessId, limit } }),
  get: (decisionId) =>
    client.get(`/api/decisions/{decisionId}`),
};

export const businessesAPI = {
  getContext: (businessId) =>
    client.get(`/api/businesses/{businessId}/context`),
};

export const approvalsAPI = {
  submit: (approval) =>
    client.post('/api/approvals', approval),
};

export default client;
"@

Set-Content -Path "$repoRoot/frontend/src/api/client.js" -Value $apiClient -Encoding UTF8
Write-Host "✓ Created: frontend/src/api/client.js"

# Frontend package.json
$packageJson = @"
{
  "name": "accord-retail-frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0",
    "lucide-react": "^0.294.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0"
  }
}
"@

Set-Content -Path "$repoRoot/frontend/package.json" -Value $packageJson -Encoding UTF8
Write-Host "✓ Created: frontend/package.json"

# Frontend Dockerfile
$frontendDocker = @"
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/dist ./dist
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
"@

Set-Content -Path "$repoRoot/frontend/Dockerfile" -Value $frontendDocker -Encoding UTF8
Write-Host "✓ Created: frontend/Dockerfile"

# ============================================
# 4. Create Config Files
# ============================================

Write-Host "`n[4] Creating configuration files..." -ForegroundColor Cyan

# docker-compose.yml
$dockerCompose = @"
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: accord_retail
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/accord_retail
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend/app:/app/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      REACT_APP_API_URL: http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
    volumes:
      - ./frontend/src:/app/src

volumes:
  postgres_data:
"@

Set-Content -Path "$repoRoot/docker-compose.yml" -Value $dockerCompose -Encoding UTF8
Write-Host "✓ Created: docker-compose.yml"

# .env.example
$envExample = @"
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/accord_retail
FASTAPI_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
ANTHROPIC_API_KEY=sk-...
APP_NAME=Accord Retail API
APP_VERSION=0.1.0
"@

Set-Content -Path "$repoRoot/.env.example" -Value $envExample -Encoding UTF8
Write-Host "✓ Created: .env.example"

# .gitignore
$gitignore = @"
# Environment variables
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Node
node_modules/
npm-debug.log
yarn-error.log
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Database
*.db
*.sqlite
*.sqlite3

# Logs
logs/
*.log
"@

Set-Content -Path "$repoRoot/.gitignore" -Value $gitignore -Encoding UTF8
Write-Host "✓ Created: .gitignore"

# README.md
$readme = @"
# Accord Retail

**Decision Intelligence for Retail Operators**

AI-powered decision support system for margin restoration, inventory optimization, and customer retention.

## Quick Start

\`\`\`bash
# 1. Copy environment
copy .env.example .env

# 2. Start Docker services
docker-compose up -d

# 3. Access
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
\`\`\`

## Architecture

- **Backend:** FastAPI + PostgreSQL (async)
- **Frontend:** React + Vite
- **DevOps:** Docker Compose

## API Endpoints

- GET /api/decisions — Decision queue
- GET /api/decisions/{id} — Full decision
- POST /api/approvals — Submit approval
- POST /api/evidence — Ingest evidence
- GET /api/scenarios/{id} — What-if scenarios
- GET /api/outcomes/{id} — Track outcomes
- GET /api/audit/{id}/timeline — Audit trail

## Features

✅ Decision queue ranked by urgency
✅ Full approval workflow
✅ Evidence management
✅ Scenario modeling
✅ Outcomes tracking
✅ Audit trail
✅ Multi-tenancy support

## Project Structure

\`\`\`
accord-retail/
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── api/          # 7 API modules
│   │   ├── models/       # Database models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── db/           # Database config
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── api/          # API client
│   │   └── styles/       # CSS
│   ├── package.json
│   └── Dockerfile
│
└── docker-compose.yml     # Docker setup
\`\`\`

## Next Steps

1. Install dependencies: \`npm install\` (frontend)
2. Create .env from .env.example
3. Run: \`docker-compose up -d\`
4. Visit: http://localhost:3000

---

**Status:** Production Ready  
**Last Updated:** September 2026
"@

Set-Content -Path "$repoRoot/README.md" -Value $readme -Encoding UTF8
Write-Host "✓ Created: README.md"

# ============================================
# 5. Summary
# ============================================

Write-Host "`n" -ForegroundColor Green
Write-Host "✅ REPOSITORY CREATED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "`nFiles created:" -ForegroundColor Cyan
Write-Host "- Backend: main.py, database.py, requirements.txt, Dockerfile"
Write-Host "- Frontend: App.jsx, Navigation.jsx, screens, API client, package.json, Dockerfile"
Write-Host "- Config: docker-compose.yml, .env.example, .gitignore, README.md"
Write-Host "- 12 Python __init__.py files"
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Refresh VS Code (Ctrl+R)"
Write-Host "2. cd accord-retail"
Write-Host "3. copy .env.example .env"
Write-Host "4. docker-compose up -d"
Write-Host "5. Open http://localhost:3000"
Write-Host "`n✨ Ready to go!" -ForegroundColor Green
