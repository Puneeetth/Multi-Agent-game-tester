"""
Report Data Model
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class GameInfo(BaseModel):
    """Game information in report."""
    
    url: str
    game_type: str
    element_count: int = 0
    mechanics: List[str] = Field(default_factory=list)
    analyzed_at: Optional[str] = None


class Summary(BaseModel):
    """Report summary."""
    
    total_tests: int
    passed: int
    failed: int
    flaky: int
    inconclusive: int
    pass_rate: float
    overall_status: str  # HEALTHY, MODERATE, CONCERNING, CRITICAL


class ReproducibilityStats(BaseModel):
    """Reproducibility statistics."""
    
    average_reproducibility: float
    min_reproducibility: float
    max_reproducibility: float
    highly_reproducible: int
    flaky_tests: int


class TriageNote(BaseModel):
    """Triage note for failed/flaky test."""
    
    test_id: int
    test_name: str
    severity: str  # HIGH, MEDIUM, LOW
    issue: str
    recommended_action: str
    cross_validation_result: str
    errors: List[str] = Field(default_factory=list)


class ArtifactsSummary(BaseModel):
    """Summary of captured artifacts."""
    
    total_artifacts: int
    types: Dict[str, int] = Field(default_factory=dict)
    directory: Optional[str] = None


class Report(BaseModel):
    """Complete test report."""
    
    report_id: str
    session_id: str
    generated_at: str
    game_info: GameInfo
    summary: Summary
    test_results: List[Dict[str, Any]] = Field(default_factory=list)
    reproducibility_stats: ReproducibilityStats
    triage_notes: List[TriageNote] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    artifacts_summary: ArtifactsSummary
    report_path: Optional[str] = None
    
    class Config:
        extra = "allow"
