"""
FastAPI Main Application - Multi-Agent Game Tester
"""
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from .config import settings
from .agents.orchestrator_agent import OrchestratorAgent
from .agents.game_analyzer_agent import GameAnalyzerAgent
from .agents.planner_agent import PlannerAgent
from .agents.ranker_agent import RankerAgent
from .agents.executor_agent import ExecutorAgent
from .agents.analyzer_agent import AnalyzerAgent
from .browser.controller import BrowserController
from .rag.knowledge_base import KnowledgeBase


app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-agent system for automated game testing",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# Session storage (in-memory for POC)
sessions = {}


# Request/Response Models
class GameAnalysisRequest(BaseModel):
    url: str
    
class TestGenerationRequest(BaseModel):
    session_id: str
    
class TestExecutionRequest(BaseModel):
    session_id: str
    test_ids: Optional[list[int]] = None  # If None, execute all ranked tests
    
class SessionResponse(BaseModel):
    session_id: str
    status: str
    message: str


# API Endpoints
@app.get("/")
async def root():
    """Serve the frontend"""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Multi-Agent Game Tester API", "docs": "/docs"}


@app.post("/api/analyze-game", response_model=SessionResponse)
async def analyze_game(request: GameAnalysisRequest):
    """
    Analyze a game from the given URL.
    Creates a new session and returns game analysis.
    """
    session_id = str(uuid.uuid4())[:8]
    
    try:
        # Initialize components
        browser = BrowserController()
        knowledge_base = KnowledgeBase()
        game_analyzer = GameAnalyzerAgent(knowledge_base)
        
        # Create session
        sessions[session_id] = {
            "id": session_id,
            "url": request.url,
            "status": "analyzing",
            "created_at": datetime.now().isoformat(),
            "game_analysis": None,
            "test_cases": [],
            "ranked_tests": [],
            "execution_results": [],
            "report": None
        }
        
        # Analyze game
        await browser.start()
        analysis = await game_analyzer.analyze(browser, request.url, session_id)
        await browser.stop()
        
        sessions[session_id]["game_analysis"] = analysis
        sessions[session_id]["status"] = "analyzed"
        
        return SessionResponse(
            session_id=session_id,
            status="analyzed",
            message=f"Game analyzed successfully. Found {analysis.get('element_count', 0)} interactive elements."
        )
        
    except Exception as e:
        if session_id in sessions:
            sessions[session_id]["status"] = "error"
            sessions[session_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-tests")
async def generate_tests(request: TestGenerationRequest):
    """
    Generate 20+ test cases based on game analysis.
    """
    session_id = request.session_id
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not session.get("game_analysis"):
        raise HTTPException(status_code=400, detail="Game not analyzed yet")
    
    try:
        session["status"] = "generating_tests"
        
        knowledge_base = KnowledgeBase()
        planner = PlannerAgent(knowledge_base)
        
        test_cases = await planner.generate_tests(
            session["game_analysis"],
            session["url"],
            min_count=settings.MIN_TEST_CASES
        )
        
        session["test_cases"] = test_cases
        session["status"] = "tests_generated"
        
        return {
            "session_id": session_id,
            "status": "tests_generated",
            "test_count": len(test_cases),
            "test_cases": test_cases
        }
        
    except Exception as e:
        session["status"] = "error"
        session["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rank-tests")
async def rank_tests(request: TestGenerationRequest):
    """
    Rank test cases and select top 10.
    """
    session_id = request.session_id
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not session.get("test_cases"):
        raise HTTPException(status_code=400, detail="No test cases generated yet")
    
    try:
        session["status"] = "ranking_tests"
        
        ranker = RankerAgent()
        ranked_tests = await ranker.rank_tests(
            session["test_cases"],
            session["game_analysis"],
            top_n=settings.TOP_TEST_CASES
        )
        
        session["ranked_tests"] = ranked_tests
        session["status"] = "tests_ranked"
        
        return {
            "session_id": session_id,
            "status": "tests_ranked",
            "ranked_count": len(ranked_tests),
            "ranked_tests": ranked_tests
        }
        
    except Exception as e:
        session["status"] = "error"
        session["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/execute-tests")
async def execute_tests(request: TestExecutionRequest):
    """
    Execute the ranked test cases.
    """
    session_id = request.session_id
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not session.get("ranked_tests"):
        raise HTTPException(status_code=400, detail="No ranked tests available")
    
    try:
        session["status"] = "executing_tests"
        
        # Initialize orchestrator
        orchestrator = OrchestratorAgent()
        
        # Execute tests
        results = await orchestrator.execute_tests(
            session_id=session_id,
            url=session["url"],
            tests=session["ranked_tests"],
            game_analysis=session["game_analysis"]
        )
        
        session["execution_results"] = results
        session["status"] = "tests_executed"
        
        return {
            "session_id": session_id,
            "status": "tests_executed",
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        session["status"] = "error"
        session["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/report/{session_id}")
async def get_report(session_id: str):
    """
    Get the comprehensive test report.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not session.get("execution_results"):
        raise HTTPException(status_code=400, detail="No execution results available")
    
    try:
        # Generate report if not already generated
        if not session.get("report"):
            analyzer = AnalyzerAgent()
            report = await analyzer.generate_report(
                session_id=session_id,
                game_analysis=session["game_analysis"],
                test_cases=session["ranked_tests"],
                execution_results=session["execution_results"]
            )
            session["report"] = report
        
        return session["report"]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """
    Get full session data.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return sessions[session_id]


@app.get("/api/artifacts/{session_id}")
async def get_artifacts(session_id: str):
    """
    Get list of artifacts for a session.
    """
    artifacts_path = settings.ARTIFACTS_DIR / session_id
    
    if not artifacts_path.exists():
        return {"artifacts": []}
    
    artifacts = []
    for file in artifacts_path.glob("**/*"):
        if file.is_file():
            artifacts.append({
                "name": file.name,
                "path": str(file.relative_to(settings.ARTIFACTS_DIR)),
                "size": file.stat().st_size,
                "type": file.suffix[1:] if file.suffix else "unknown"
            })
    
    return {"artifacts": artifacts}


@app.get("/api/artifacts/{session_id}/{filename:path}")
async def get_artifact_file(session_id: str, filename: str):
    """
    Get a specific artifact file.
    """
    file_path = settings.ARTIFACTS_DIR / session_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    return FileResponse(str(file_path))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
