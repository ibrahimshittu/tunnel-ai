"""Core data types and models for Tunnel AI."""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class BrowserType(str, Enum):
    """Supported browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class ActionType(str, Enum):
    """Test action types."""
    CLICK = "click"
    TYPE = "type"
    NAVIGATE = "navigate"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    SELECT = "select"
    HOVER = "hover"
    SCROLL = "scroll"
    ASSERT = "assert"


class AssertionType(str, Enum):
    """Assertion types."""
    VISIBLE = "visible"
    TEXT = "text"
    VALUE = "value"
    URL = "url"
    TITLE = "title"
    COUNT = "count"
    ATTRIBUTE = "attribute"


class TestRequest(BaseModel):
    """Natural language test request."""
    instruction: str = Field(..., description="Natural language test instruction")
    url: str = Field(..., description="URL of the application to test")
    browser: BrowserType = Field(default=BrowserType.CHROMIUM)
    viewport: Optional[Dict[str, int]] = Field(default={"width": 1280, "height": 720})
    timeout: int = Field(default=30000, description="Test timeout in milliseconds")
    headless: bool = Field(default=True)
    session_id: Optional[str] = Field(default=None)


class TestStep(BaseModel):
    """Individual test step."""
    action: ActionType
    selector: Optional[str] = None
    value: Optional[Any] = None
    description: str
    wait_before: Optional[int] = Field(default=None, description="Wait time before action in ms")
    wait_after: Optional[int] = Field(default=None, description="Wait time after action in ms")
    retry: Optional[int] = Field(default=3, description="Number of retries on failure")


class Assertion(BaseModel):
    """Test assertion."""
    type: AssertionType
    selector: Optional[str] = None
    expected: Any
    description: str
    operator: Literal["equals", "contains", "greater", "less"] = "equals"


class TestPlan(BaseModel):
    """Complete test plan."""
    id: str
    name: str
    description: str
    url: str
    steps: List[TestStep]
    assertions: List[Assertion]
    test_data: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)


class StepResult(BaseModel):
    """Result of a single test step."""
    step: TestStep
    success: bool
    error: Optional[str] = None
    screenshot: Optional[str] = None
    duration: float
    timestamp: datetime = Field(default_factory=datetime.now)


class TestResult(BaseModel):
    """Complete test execution result."""
    id: str
    plan_id: str
    success: bool
    execution_time: float
    steps: List[StepResult]
    passed_assertions: int = 0
    failed_assertions: int = 0
    screenshots: List[str] = Field(default_factory=list)
    video_url: Optional[str] = None
    error: Optional[str] = None
    browser_logs: Optional[List[str]] = None
    started_at: datetime
    completed_at: datetime


class AgentState(BaseModel):
    """State for LangGraph agent workflow."""
    request: TestRequest
    plan: Optional[TestPlan] = None
    generated_code: Optional[str] = None
    result: Optional[TestResult] = None
    errors: List[str] = Field(default_factory=list)
    current_step: str = "initialization"
    session_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0


class TestSession(BaseModel):
    """Test session information."""
    id: str
    user_id: Optional[str] = None
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)