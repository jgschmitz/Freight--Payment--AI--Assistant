"""
Freight Payment AI Assistant - FastAPI Web Application
"""
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import asyncio
import uvicorn

from config import get_settings, Settings
from services.vector_search import VectorSearchService
from services.analytics import AnalyticsService
from utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Freight Payment AI Assistant",
    description="AI-powered freight payment analysis using vector search and embeddings",
    version="1.0.0"
)

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models for API
class SearchQuery(BaseModel):
    query: str = Field(..., description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Number of results to return")

class SearchResult(BaseModel):
    score: float = Field(..., description="Similarity score")
    reason: str = Field(..., description="Reason text from the document")
    document_id: Optional[str] = Field(None, description="Document ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_results: int
    query: str
    execution_time_ms: float

class AnalyticsResponse(BaseModel):
    total_documents: int
    top_reasons: List[Dict[str, Any]]
    score_distribution: Dict[str, int]
    timestamp: datetime

# Dependency injection
def get_vector_search_service() -> VectorSearchService:
    settings = get_settings()
    return VectorSearchService(settings)

def get_analytics_service() -> AnalyticsService:
    settings = get_settings()
    return AnalyticsService(settings)

# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

@app.post("/api/search", response_model=SearchResponse)
async def search_events(
    search_query: SearchQuery,
    vector_service: VectorSearchService = Depends(get_vector_search_service)
):
    """
    Search for similar freight payment events using vector search
    """
    try:
        start_time = datetime.utcnow()
        
        results = await vector_service.search(
            query=search_query.query,
            limit=search_query.limit
        )
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds() * 1000
        
        return SearchResponse(
            results=[
                SearchResult(
                    score=result.get("score", 0.0),
                    reason=result.get("reason", ""),
                    document_id=str(result.get("_id", "")),
                    metadata=result.get("metadata", {})
                )
                for result in results
            ],
            total_results=len(results),
            query=search_query.query,
            execution_time_ms=execution_time
        )
    
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/api/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get analytics data about freight payment events
    """
    try:
        analytics_data = await analytics_service.get_analytics()
        
        return AnalyticsResponse(
            total_documents=analytics_data.get("total_documents", 0),
            top_reasons=analytics_data.get("top_reasons", []),
            score_distribution=analytics_data.get("score_distribution", {}),
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")

@app.get("/api/similar/{document_id}")
async def find_similar_documents(
    document_id: str,
    limit: int = 10,
    vector_service: VectorSearchService = Depends(get_vector_search_service)
):
    """
    Find documents similar to a specific document
    """
    try:
        results = await vector_service.find_similar_by_id(
            document_id=document_id,
            limit=limit
        )
        
        return {
            "document_id": document_id,
            "similar_documents": results,
            "count": len(results)
        }
    
    except Exception as e:
        logger.error(f"Similar documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Similar documents search failed: {str(e)}")

@app.get("/api/trends")
async def get_trends(
    days: int = 30,
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get trending patterns in freight payment events
    """
    try:
        trends = await analytics_service.get_trends(days=days)
        return trends
    
    except Exception as e:
        logger.error(f"Trends error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Trends analysis failed: {str(e)}")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return {"error": "Internal server error", "detail": str(exc)}

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )