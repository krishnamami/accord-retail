from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import router
from app.api.decisions.routes import router as decisions_router

app = FastAPI(
    title="Accord Retail API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(decisions_router, prefix="/api/decisions", tags=["decisions"])

@app.get("/health")
async def health():
    return {"status": "healthy", "database": "AWS RDS"}

@app.get("/")
async def root():
    return {
        "service": "Accord Retail API",
        "version": "0.1.0",
        "database": "AWS RDS",
        "docs": "/docs",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
