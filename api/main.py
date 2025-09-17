"""Main FastAPI application."""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any
from loguru import logger
import uuid

from core.types import TestRequest, TestResult
from orchestrator import TestAutomationWorkflow
from config.settings import settings

# Configure logging
logger.add("logs/tunnel_ai.log", rotation="500 MB")

# Create FastAPI app
app = FastAPI(
    title="Tunnel AI API",
    description="Natural language to automated frontend test execution using AI agents",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize workflow
workflow = TestAutomationWorkflow()

# Store test results in memory (use Redis/DB in production)
test_results: Dict[str, TestResult] = {}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Tunnel AI API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/test/run")
async def run_test(request: TestRequest, background_tasks: BackgroundTasks):
    """Run a test from natural language instruction."""
    try:
        # Generate session ID if not provided
        if not request.session_id:
            request.session_id = str(uuid.uuid4())

        logger.info(f"Received test request: {request.instruction}")

        # Run workflow in background
        background_tasks.add_task(execute_test_async, request)

        return JSONResponse(
            status_code=202,
            content={
                "message": "Test execution started",
                "session_id": request.session_id,
                "status_url": f"/test/status/{request.session_id}"
            }
        )

    except Exception as e:
        logger.error(f"Failed to start test: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test/run-sync")
async def run_test_sync(request: TestRequest) -> TestResult:
    """Run a test synchronously and wait for results."""
    try:
        # Generate session ID if not provided
        if not request.session_id:
            request.session_id = str(uuid.uuid4())

        logger.info(f"Running synchronous test: {request.instruction}")

        # Execute the workflow
        result = await workflow.run(request)

        # Store result
        test_results[request.session_id] = result

        return result

    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test/status/{session_id}")
async def get_test_status(session_id: str):
    """Get test execution status."""
    if session_id in test_results:
        result = test_results[session_id]
        return {
            "status": "completed",
            "result": result.dict()
        }

    return {
        "status": "pending",
        "message": "Test is still running"
    }


@app.get("/test/results/{session_id}")
async def get_test_results(session_id: str) -> TestResult:
    """Get test results by session ID."""
    if session_id not in test_results:
        raise HTTPException(status_code=404, detail="Test results not found")

    return test_results[session_id]


@app.post("/test/plan")
async def create_test_plan(request: TestRequest):
    """Create a test plan without executing it."""
    try:
        from agents import TestPlanningAgent

        planner = TestPlanningAgent()
        plan = await planner.plan(request)

        return plan

    except Exception as e:
        logger.error(f"Failed to create test plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test/generate")
async def generate_test_code(request: TestRequest):
    """Generate test code from a request."""
    try:
        from agents import TestPlanningAgent, TestGenerationAgent

        # Create plan
        planner = TestPlanningAgent()
        plan = await planner.plan(request)

        # Generate code
        generator = TestGenerationAgent()
        code = await generator.generate(plan)

        return {
            "plan": plan.dict(),
            "code": code
        }

    except Exception as e:
        logger.error(f"Failed to generate test code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "openai_configured": bool(settings.openai_api_key),
        "browserbase_configured": bool(settings.browserbase_api_key)
    }


async def execute_test_async(request: TestRequest):
    """Execute test asynchronously."""
    try:
        result = await workflow.run(request)
        test_results[request.session_id] = result
        logger.success(f"Test completed: {request.session_id}")
    except Exception as e:
        logger.error(f"Async test execution failed: {e}")
        # Store error result
        test_results[request.session_id] = TestResult(
            id=f"error_{request.session_id}",
            plan_id="unknown",
            success=False,
            execution_time=0,
            steps=[],
            error=str(e),
            started_at=None,
            completed_at=None
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )