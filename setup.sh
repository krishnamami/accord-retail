#!/bin/bash
# Accord Retail - Repository Setup Script
# Run in Git Bash: bash setup.sh

echo "Creating Accord Retail repository structure..."
echo ""

# Create directories
echo "Creating directories..."
mkdir -p backend/app/api/{decisions,evidence,businesses,approvals,audit,scenarios,outcomes}
mkdir -p backend/app/{models,schemas,db,tests,scripts}
mkdir -p frontend/src/{components/{screens,shared,layouts},api,hooks,utils,styles}
mkdir -p frontend/public
mkdir -p database/migrations
mkdir -p docs

echo "OK: All directories created"
echo ""

# Create Python __init__.py files
echo "Creating Python files..."
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/db/__init__.py
touch backend/app/models/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/api/decisions/__init__.py
touch backend/app/api/evidence/__init__.py
touch backend/app/api/businesses/__init__.py
touch backend/app/api/approvals/__init__.py
touch backend/app/api/audit/__init__.py
touch backend/app/api/scenarios/__init__.py
touch backend/app/api/outcomes/__init__.py

echo "OK: All __init__.py files created"
echo ""

# Create .env.example
echo "Creating configuration files..."
cat > .env.example << 'ENV'
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/accord_retail
FASTAPI_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
ENV
echo "OK: .env.example"

# Create .gitignore
cat > .gitignore << 'GIT'
__pycache__/
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
.env.local
