"""
Test Case Data Model
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class TestCase(BaseModel):
    """Data model for a test case."""
    
    id: int = Field(..., description="Unique test case ID")
    name: str = Field(..., description="Test case name")
    description: str = Field(default="", description="Test description")
    steps: List[str] = Field(default_factory=list, description="Test steps")
    expected_result: str = Field(default="", description="Expected result")
    priority: str = Field(default="medium", description="Priority: high/medium/low")
    category: str = Field(default="functional", description="Test category")
    
    # Ranking fields (populated by RankerAgent)
    impact: Optional[float] = Field(default=None, description="Impact score 0-10")
    coverage: Optional[float] = Field(default=None, description="Coverage score 0-10")
    risk: Optional[float] = Field(default=None, description="Risk score 0-10")
    complexity: Optional[float] = Field(default=None, description="Complexity score 0-10")
    overall_score: Optional[float] = Field(default=None, description="Overall ranking score")
    ranking_reason: Optional[str] = Field(default=None, description="Reason for ranking")
    
    # Metadata
    generated_at: Optional[str] = Field(default=None, description="Generation timestamp")
    
    class Config:
        extra = "allow"
