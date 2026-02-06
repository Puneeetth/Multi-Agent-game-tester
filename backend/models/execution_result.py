"""
Execution Result Data Model
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class StepResult(BaseModel):
    """Result of a single test step."""
    
    index: int
    description: str
    status: str = "pending"
    action_taken: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None
    error: Optional[str] = None


class RunResult(BaseModel):
    """Result of a single test run."""
    
    run_index: int
    status: str
    steps: List[StepResult] = Field(default_factory=list)
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None


class CrossValidation(BaseModel):
    """Cross-agent validation result."""
    
    status: str
    agrees_with_primary: bool
    primary_statuses: List[str] = Field(default_factory=list)
    agent_id: str = "cross_validator"
    error: Optional[str] = None


class Verdict(BaseModel):
    """Final test verdict."""
    
    result: str  # PASS, FAIL, FLAKY, INCONCLUSIVE
    confidence: int = 0  # 0-100
    reason: str = ""
    pass_count: int = 0
    fail_count: int = 0
    total_runs: int = 0


class ExecutionResult(BaseModel):
    """Complete execution result for a test case."""
    
    test_id: int
    test_name: str
    runs: List[RunResult] = Field(default_factory=list)
    cross_validation: Optional[CrossValidation] = None
    verdict: Optional[Verdict] = None
    reproducibility: float = 0.0
    executed_at: Optional[str] = None
    
    class Config:
        extra = "allow"
