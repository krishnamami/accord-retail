# Accord Retail - Repository Creation Script (FIXED)
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
        Write-Host "OK: $dir"
    }
}

# ============================================
# 2. Create Backend Files
# ============================================

Write-Host "`n[2] Creating backend files..." -ForegroundColor Cyan

# Backend main.py - using single quotes to avoid PowerShell interpretation
$mainPy = '
"""
Accord Retail - Backend API
Decision Intelligence for Retail Operators
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Accord Retail API",
    description="Decision Intelligence for Retail Operators",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "accord-retail-api",
        "version": "0.1.0",
    }

@app.get("/")
async def root():
    return {
        "service": "Accord Retail API",
        "version": "0.1.0",
        "docs": "/docs",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
'

Set-Content -Path "$repoRoot/backend/app/main.py" -Value $mainPy -Encoding UTF8
Write-Host "OK: backend/app/main.py"

# Backend database.py
$dbPy = '
"""
Database Connection & Initialization
"""

import os
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
        logger.info("OK Database schema initialized")
    except Exception as e:
        logger.error(f"FAIL Database init: {e}")
        raise
'

Set-Content -Path "$repoRoot/backend/app/db/database.py" -Value $dbPy -Encoding UTF8
Write-Host "OK: backend/app/db/database.py"

# Create __init__.py files for Python packages
$initFiles = @(
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
)

foreach ($file in $initFiles) {
    Set-Content -Path "$repoRoot/$file" -Value "" -Encoding UTF8
}
Write-Host "OK: All __init__.py files"

# Backend requirements.txt
$requirements = 'fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
asyncpg==0.29.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
pydantic==2.5.0
pytest==7.4.3
black==23.12.0
'

Set-Content -Path "$repoRoot/backend/requirements.txt" -Value $requirements -Encoding UTF8
Write-Host "OK: backend/requirements.txt"

# Backend Dockerfile
$dockerfile = 'FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc postgresql-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'

Set-Content -Path "$repoRoot/backend/Dockerfile" -Value $dockerfile -Encoding UTF8
Write-Host "OK: backend/Dockerfile"

# ============================================
# 3. Create Frontend Files
# ============================================

Write-Host "`n[3] Creating frontend files..." -ForegroundColor Cyan

# Frontend App.jsx
$appJsx = '/**
 * Accord Retail - Frontend React App
 */

import React, { useState, useEffect } from "react";
import Navigation from "./components/layouts/Navigation";
import TodayScreen from "./components/screens/TodayScreen";
import "./styles/global.css";

function App() {
  const [currentScreen, setCurrentScreen] = useState("TODAY");
  const [businessContext, setBusinessContext] = useState(null);

  useEffect(() => {
    setBusinessContext({
      business_id: "retail-001",
      business_name: "TechCo Inc",
      revenue: 15000000,
      margin: -0.021,
      churn: 0.021,
    });
  }, []);

  return (
    <div className="accord-app">
      <Navigation currentScreen={currentScreen} onNavigate={setCurrentScreen} />
      <main className="accord-main">
        {businessContext ? (
          <TodayScreen businessContext={businessContext} />
        ) : (
          <div>Loading...</div>
        )}
      </main>
    </div>
  );
}

export default App;
'

Set-Content -Path "$repoRoot/frontend/src/App.jsx" -Value $appJsx -Encoding UTF8
Write-Host "OK: frontend/src/App.jsx"

# Frontend Navigation.jsx
$navJsx = '/**
 * Navigation Component
 */

import React from "react";

function Navigation({ currentScreen, onNavigate }) {
  return (
    <nav className="navigation">
      <div className="nav-container">
        <div className="nav-brand">
          <h1>Accord Retail</h1>
        </div>
        <div className="nav-menu">
          <button onClick={() => onNavigate("TODAY")}>Today</button>
          <button onClick={() => onNavigate("DECISIONS")}>Decisions</button>
        </div>
      </div>
    </nav>
  );
}

export default Navigation;
'

Set-Content -Path "$repoRoot/frontend/src/components/layouts/Navigation.jsx" -Value $navJsx -Encoding UTF8
Write-Host "OK: frontend/src/components/layouts/Navigation.jsx"

# Frontend TodayScreen.jsx
$todayJsx = '/**
 * TODAY Screen - Decision Queue
 */

import React from "react";

function TodayScreen({ businessContext }) {
  return (
    <div className="today-screen">
      <h2>What Needs Your Attention Today</h2>
      <p>Business: {businessContext.business_name}</p>
      <p>Revenue: ${businessContext.revenue.toLocaleString()}</p>
      <p>Margin: {(businessContext.margin * 100).toFixed(2)}%</p>
    </div>
  );
}

export default TodayScreen;
'

Set-Content -Path "$repoRoot/frontend/src/components/screens/TodayScreen.jsx" -Value $todayJsx -Encoding UTF8
Write-Host "OK: frontend/src/components/screens/TodayScreen.jsx"

# Frontend package.json
$packageJson = '{
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
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0"
  }
}
'

Set-Content -Path "$repoRoot/frontend/package.json" -Value $packageJson -Encoding UTF8
Write-Host "OK: frontend/package.json"

# Frontend Dockerfile
$frontendDocker = 'FROM node:18-alpine AS build
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
'

Set-Content -Path "$repoRoot/frontend/Dockerfile" -Value $frontendDocker -Encoding UTF8
Write-Host "OK: frontend/Dockerfile"

# ============================================
# 4. Create Config Files
# ============================================

Write-Host "`n[4] Creating configuration files..." -ForegroundColor Cyan

# docker-compose.yml
$dockerCompose = 'version: "3.8"

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
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
'

Set-Content -Path "$repoRoot/docker-compose.yml" -Value $dockerCompose -Encoding UTF8
Write-Host "OK: docker-compose.yml"

# .env.example
$envExample = 'DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/accord_retail
FASTAPI_ENV=development
LOG_LEVEL=INFO
'

Set-Content -Path "$repoRoot/.env.example" -Value $envExample -Encoding UTF8
Write-Host "OK: .env.example"

# .gitignore
$gitignore = '__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
node_modules/
npm-debug.log
.env
.vscode/
.DS_Store
'

Set-Content -Path "$repoRoot/.gitignore" -Value $gitignore -Encoding UTF8
Write-Host "OK: .gitignore"

# Create global.css
$globalCss = 'body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  margin: 0;
  padding: 0;
  background: #f5f5f5;
}

.accord-app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.navigation {
  background: #1a1a1a;
  color: white;
  padding: 1rem;
}

.nav-brand h1 {
  margin: 0;
  font-size: 24px;
}

.nav-menu {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.nav-menu button {
  padding: 0.5rem 1rem;
  background: #0066cc;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.accord-main {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.today-screen,
.decision-workbench {
  max-width: 1200px;
  margin: 0 auto;
}
'

Set-Content -Path "$repoRoot/frontend/src/styles/global.css" -Value $globalCss -Encoding UTF8
Write-Host "OK: frontend/src/styles/global.css"

# README.md
$readme = '# Accord Retail

Decision Intelligence for Retail Operators

## Quick Start

```bash
# 1. Copy environment
copy .env.example .env

# 2. Start Docker
docker-compose up -d

# 3. Access
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Architecture

- Backend: FastAPI + PostgreSQL
- Frontend: React + Vite
- DevOps: Docker Compose

## Project Structure

```
accord-retail/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── db/
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── styles/
│   │   └── App.jsx
│   └── Dockerfile
└── docker-compose.yml
```

## Next Steps

1. Refresh VS Code
2. Run: `docker-compose up -d`
3. Visit: http://localhost:3000

---

Status: Ready to Go
'

Set-Content -Path "$repoRoot/README.md" -Value $readme -Encoding UTF8
Write-Host "OK: README.md"

# ============================================
# 5. Summary
# ============================================

Write-Host "`n" -ForegroundColor Green
Write-Host "SUCCESS! Repository created." -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Press F5 to refresh VS Code"
Write-Host "2. copy .env.example .env"
Write-Host "3. docker-compose up -d"
Write-Host "4. Visit http://localhost:3000"
Write-Host "`nReady!" -ForegroundColor Green
