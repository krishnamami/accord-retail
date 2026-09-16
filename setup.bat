@echo off
REM Accord Retail - Repository Setup Script
REM Run this in VS Code terminal in your repo folder

setlocal enabledelayedexpansion

echo Creating Accord Retail repository structure...

REM Create directories
echo Creating directories...
for %%D in (
    backend\app\api\decisions
    backend\app\api\evidence
    backend\app\api\businesses
    backend\app\api\approvals
    backend\app\api\audit
    backend\app\api\scenarios
    backend\app\api\outcomes
    backend\app\models
    backend\app\schemas
    backend\app\db
    frontend\src\components\screens
    frontend\src\components\shared
    frontend\src\components\layouts
    frontend\src\api
    frontend\src\hooks
    frontend\src\utils
    frontend\src\styles
    database\migrations
    docs
) do (
    if not exist "%%D" mkdir "%%D"
    echo OK: %%D
)

echo.
echo Creating Python files...

REM Create __init__.py files
for %%F in (
    backend\app\__init__.py
    backend\app\api\__init__.py
    backend\app\db\__init__.py
    backend\app\models\__init__.py
    backend\app\schemas\__init__.py
    backend\app\api\decisions\__init__.py
    backend\app\api\evidence\__init__.py
    backend\app\api\businesses\__init__.py
    backend\app\api\approvals\__init__.py
    backend\app\api\audit\__init__.py
    backend\app\api\scenarios\__init__.py
    backend\app\api\outcomes\__init__.py
) do (
    type nul > "%%F"
    echo OK: %%F
)

echo.
echo Creating configuration files...

REM Create .env.example
(
echo DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/accord_retail
echo FASTAPI_ENV=development
echo LOG_LEVEL=INFO
) > .env.example
echo OK: .env.example

REM Create .gitignore
(
echo __pycache__/
echo *.pyc
echo *.pyo
echo *.egg-info/
echo dist/
echo build/
echo node_modules/
echo npm-debug.log
echo .env
echo .vscode/
echo .DS_Store
) > .gitignore
echo OK: .gitignore

REM Create README.md
(
echo # Accord Retail
echo.
echo Decision Intelligence for Retail Operators
echo.
echo ## Quick Start
echo.
echo ```bash
echo docker-compose up -d
echo ```
echo.
echo Then visit:
echo - Frontend: http://localhost:3000
echo - Backend: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
) > README.md
echo OK: README.md

echo.
echo Creating docker-compose.yml...

(
echo version: '3.8'
echo.
echo services:
echo   postgres:
echo     image: postgres:15-alpine
echo     environment:
echo       POSTGRES_USER: postgres
echo       POSTGRES_PASSWORD: postgres
echo       POSTGRES_DB: accord_retail
echo     ports:
echo       - "5432:5432"
echo     volumes:
echo       - postgres_data:/var/lib/postgresql/data
echo.
echo   backend:
echo     build: ./backend
echo     environment:
echo       DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/accord_retail
echo     ports:
echo       - "8000:8000"
echo     depends_on:
echo       - postgres
echo.
echo   frontend:
echo     build: ./frontend
echo     ports:
echo       - "3000:3000"
echo     depends_on:
echo       - backend
echo.
echo volumes:
echo   postgres_data:
) > docker-compose.yml
echo OK: docker-compose.yml

echo.
echo SUCCESS! Repository created.
echo.
echo Next steps:
echo 1. Refresh VS Code (F5)
echo 2. Copy .env.example to .env
echo 3. Run: docker-compose up -d
echo 4. Visit: http://localhost:3000
echo.
pause
