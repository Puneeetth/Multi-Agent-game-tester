"""
Ranker Agent - Ranks test cases and selects top N
"""
import json
from typing import Dict, List, Any
from datetime import datetime

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_community.llms import Ollama
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from .base_agent import BaseAgent
from ..config import settings


class RankerAgent(BaseAgent):
    """
    Ranks test cases by importance and selects the top N for execution.
    Uses criteria like impact, coverage, complexity, and risk.
    """
    
    def __init__(self):
        super().__init__(
            name="Ranker",
            description="Ranks and prioritizes test cases"
        )
        self.model_name = settings.OLLAMA_TEXT_MODEL
        
        if LANGCHAIN_AVAILABLE:
            self.llm = Ollama(
                model=self.model_name,
                temperature=0.3  # Lower temperature for more consistent ranking
            )
        else:
            self.llm = None
            
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute test ranking."""
        test_cases = context.get("test_cases", [])
        game_analysis = context.get("game_analysis", {})
        top_n = context.get("top_n", settings.TOP_TEST_CASES)
        
        ranked = await self.rank_tests(test_cases, game_analysis, top_n)
        return {"ranked_tests": ranked}
        
    async def rank_tests(
        self,
        test_cases: List[Dict],
        game_analysis: Dict[str, Any],
        top_n: int = 10
    ) -> List[Dict]:
        """
        Rank test cases and select top N.
        
        Args:
            test_cases: List of test cases to rank
            game_analysis: Game analysis for context
            top_n: Number of top tests to select
            
        Returns:
            List of top N ranked test cases with scores
        """
        self.log_info(f"Ranking {len(test_cases)} tests, selecting top {top_n}")
        
        if self.llm:
            ranked = await self._rank_with_langchain(test_cases, game_analysis, top_n)
        else:
            ranked = self._rank_with_heuristics(test_cases, game_analysis, top_n)
            
        self.log_info(f"Selected {len(ranked)} top tests")
        return ranked[:top_n]
        
    async def _rank_with_langchain(
        self,
        test_cases: List[Dict],
        game_analysis: Dict,
        top_n: int
    ) -> List[Dict]:
        """
        Rank tests using LangChain and Ollama.
        """
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert test prioritization system. Rank test cases by these criteria:
- Impact (0-10): How critical is this test for game functionality?
- Coverage (0-10): How much of the game does this test cover?
- Risk (0-10): How likely is this area to have bugs?
- Complexity (0-10): How complex is the test? (higher = harder to execute)

Calculate overall score: (Impact * 3 + Coverage * 2 + Risk * 2 - Complexity) / 8

Output ONLY valid JSON array with ranked tests. No explanation."""),
            ("human", """Game Type: {game_type}
Key Mechanics: {mechanics}

Test Cases to Rank:
{test_cases}

Rank all tests and output JSON array with scores:
[
  {{
    "id": original_id,
    "name": "test name",
    "impact": 0-10,
    "coverage": 0-10,
    "risk": 0-10,
    "complexity": 0-10,
    "overall_score": calculated_score,
    "ranking_reason": "brief reason"
  }}
]

Sort by overall_score descending.""")
        ])
        
        try:
            chain = prompt_template | self.llm
            
            # Prepare test cases summary
            test_summary = json.dumps([
                {
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "category": t.get("category"),
                    "priority": t.get("priority"),
                    "description": t.get("description", "")[:100]
                }
                for t in test_cases[:30]  # Limit to avoid token limits
            ], indent=2)
            
            response = await chain.ainvoke({
                "game_type": game_analysis.get("game_type", "puzzle"),
                "mechanics": json.dumps(game_analysis.get("mechanics", [])),
                "test_cases": test_summary
            })
            
            content = response.content
            
            # Extract JSON from response
            start = content.find("[")
            end = content.rfind("]") + 1
            
            if start >= 0 and end > start:
                ranked_data = json.loads(content[start:end])
                
                # Merge ranking data with original test cases
                ranked_tests = []
                for rank_item in ranked_data:
                    original = next(
                        (t for t in test_cases if t.get("id") == rank_item.get("id")),
                        None
                    )
                    if original:
                        merged = {**original, **rank_item}
                        ranked_tests.append(merged)
                        
                # Sort by overall score
                ranked_tests.sort(
                    key=lambda x: x.get("overall_score", 0),
                    reverse=True
                )
                
                if ranked_tests:
                    return ranked_tests
                    
        except Exception as e:
            self.log_error(f"LangChain ranking failed: {e}")
            
        return self._rank_with_heuristics(test_cases, game_analysis, top_n)
        
    def _rank_with_heuristics(
        self,
        test_cases: List[Dict],
        game_analysis: Dict,
        top_n: int
    ) -> List[Dict]:
        """
        Rank tests using heuristic scoring.
        """
        scored_tests = []
        
        for test in test_cases:
            score = self._calculate_heuristic_score(test, game_analysis)
            scored_test = {
                **test,
                "overall_score": score["total"],
                "impact": score["impact"],
                "coverage": score["coverage"],
                "risk": score["risk"],
                "complexity": score["complexity"],
                "ranking_reason": score["reason"]
            }
            scored_tests.append(scored_test)
            
        # Sort by score descending
        scored_tests.sort(key=lambda x: x["overall_score"], reverse=True)
        
        return scored_tests[:top_n]
        
    def _calculate_heuristic_score(
        self,
        test: Dict,
        game_analysis: Dict
    ) -> Dict:
        """
        Calculate heuristic score for a test case.
        """
        scores = {
            "impact": 5,
            "coverage": 5,
            "risk": 5,
            "complexity": 3,
            "reason": ""
        }
        
        category = test.get("category", "").lower()
        priority = test.get("priority", "").lower()
        name = test.get("name", "").lower()
        
        # Priority-based impact
        if priority == "high":
            scores["impact"] = 9
        elif priority == "medium":
            scores["impact"] = 6
        else:
            scores["impact"] = 4
            
        # Category-based scoring
        if category == "functional":
            scores["impact"] += 1
            scores["risk"] = 7
            scores["reason"] = "Core functionality test"
        elif category == "ui":
            scores["coverage"] = 7
            scores["reason"] = "UI coverage test"
        elif category == "edge_case":
            scores["risk"] = 8
            scores["complexity"] = 6
            scores["reason"] = "Edge case for robustness"
        elif category == "performance":
            scores["impact"] = 6
            scores["risk"] = 5
            scores["reason"] = "Performance verification"
        else:
            scores["reason"] = "General test case"
            
        # Name-based adjustments
        important_keywords = ["start", "restart", "score", "load", "main", "core"]
        if any(kw in name for kw in important_keywords):
            scores["impact"] = min(10, scores["impact"] + 2)
            scores["reason"] += " (contains important keyword)"
            
        # Ensure scores are in range
        for key in ["impact", "coverage", "risk", "complexity"]:
            scores[key] = max(0, min(10, scores[key]))
            
        # Calculate total
        scores["total"] = round(
            (scores["impact"] * 3 + scores["coverage"] * 2 + 
             scores["risk"] * 2 - scores["complexity"]) / 8,
            2
        )
        
        return scores
