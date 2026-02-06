"""
Orchestrator Agent - Coordinates multi-agent test execution
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_agent import BaseAgent
from .executor_agent import ExecutorAgent
from .analyzer_agent import AnalyzerAgent
from ..browser.controller import BrowserController
from ..browser.artifact_capture import ArtifactCapture
from ..rag.knowledge_base import KnowledgeBase
from ..config import settings


class OrchestratorAgent(BaseAgent):
    """
    Orchestrates the test execution workflow:
    - Manages multiple ExecutorAgents
    - Coordinates parallel/sequential execution
    - Handles retry logic
    - Implements repeat validation
    - Aggregates results
    """
    
    def __init__(self, num_executors: int = 2):
        super().__init__(
            name="Orchestrator",
            description="Coordinates multi-agent test execution"
        )
        self.num_executors = num_executors
        self.knowledge_base = KnowledgeBase()
        
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute orchestration."""
        return await self.execute_tests(
            session_id=context.get("session_id"),
            url=context.get("url"),
            tests=context.get("tests", []),
            game_analysis=context.get("game_analysis", {})
        )
        
    async def execute_tests(
        self,
        session_id: str,
        url: str,
        tests: List[Dict],
        game_analysis: Dict
    ) -> List[Dict]:
        """
        Execute all tests with orchestration.
        
        Args:
            session_id: Session identifier
            url: Game URL
            tests: List of test cases to execute
            game_analysis: Game analysis data
            
        Returns:
            List of execution results
        """
        self.log_info(f"Starting execution of {len(tests)} tests for session {session_id}")
        
        all_results = []
        
        # Create artifact capture for session
        artifact_capture = ArtifactCapture(session_id)
        
        # Execute tests with repeat validation
        for test in tests:
            test_results = await self._execute_with_validation(
                test=test,
                url=url,
                game_analysis=game_analysis,
                artifact_capture=artifact_capture,
                session_id=session_id
            )
            all_results.append(test_results)
            
            # Store results in knowledge base for learning
            self._record_for_learning(url, test, test_results)
            
        self.log_info(f"Completed execution of {len(all_results)} tests")
        return all_results
        
    async def _execute_with_validation(
        self,
        test: Dict,
        url: str,
        game_analysis: Dict,
        artifact_capture: ArtifactCapture,
        session_id: str
    ) -> Dict:
        """
        Execute a test with repeat validation.
        
        Args:
            test: Test case to execute
            url: Game URL
            game_analysis: Game analysis
            artifact_capture: Artifact capture instance
            session_id: Session ID
            
        Returns:
            Test result with validation data
        """
        test_id = test.get("id", 0)
        test_name = test.get("name", "Unknown")
        
        self.log_info(f"Executing test {test_id} with repeat validation")
        
        runs = []
        repeat_count = settings.REPEAT_VALIDATION_COUNT
        
        # Perform repeat validation (run same test multiple times)
        for run_idx in range(repeat_count):
            self.log_info(f"  Run {run_idx + 1}/{repeat_count} for test {test_id}")
            
            browser = BrowserController()
            executor = ExecutorAgent(agent_id=f"exec_{run_idx}")
            
            try:
                await browser.start()
                
                # Navigate to game first
                await browser.navigate(url)
                await browser.wait_for_timeout(2000)
                
                # Execute test
                result = await executor.execute_test(
                    test_case=test,
                    browser=browser,
                    artifact_capture=artifact_capture,
                    game_analysis=game_analysis
                )
                
                result["run_index"] = run_idx
                runs.append(result)
                
            except Exception as e:
                self.log_error(f"Run {run_idx} failed: {e}")
                runs.append({
                    "run_index": run_idx,
                    "status": "error",
                    "error": str(e)
                })
                
            finally:
                await browser.stop()
                
            # Small delay between runs
            await asyncio.sleep(1)
            
        # Cross-agent validation (use different executor)
        cross_validation = await self._cross_agent_validate(
            test=test,
            url=url,
            game_analysis=game_analysis,
            artifact_capture=artifact_capture,
            primary_results=runs
        )
        
        # Determine final verdict
        verdict = self._determine_verdict(runs, cross_validation)
        
        return {
            "test_id": test_id,
            "test_name": test_name,
            "runs": runs,
            "cross_validation": cross_validation,
            "verdict": verdict,
            "reproducibility": self._calculate_reproducibility(runs),
            "executed_at": datetime.now().isoformat()
        }
        
    async def _cross_agent_validate(
        self,
        test: Dict,
        url: str,
        game_analysis: Dict,
        artifact_capture: ArtifactCapture,
        primary_results: List[Dict]
    ) -> Dict:
        """
        Perform cross-agent validation using a different executor.
        
        Args:
            test: Test case
            url: Game URL
            game_analysis: Game analysis
            artifact_capture: Artifact capture
            primary_results: Results from primary executor
            
        Returns:
            Cross-validation result
        """
        self.log_info(f"Performing cross-agent validation for test {test.get('id')}")
        
        browser = BrowserController()
        cross_executor = ExecutorAgent(agent_id="cross_validator")
        
        try:
            await browser.start()
            await browser.navigate(url)
            await browser.wait_for_timeout(2000)
            
            result = await cross_executor.execute_test(
                test_case=test,
                browser=browser,
                artifact_capture=artifact_capture,
                game_analysis=game_analysis
            )
            
            # Compare with primary results
            primary_status = [r.get("status") for r in primary_results]
            cross_status = result.get("status")
            
            agreement = all(s == cross_status for s in primary_status)
            
            return {
                "status": cross_status,
                "agrees_with_primary": agreement,
                "primary_statuses": primary_status,
                "agent_id": "cross_validator"
            }
            
        except Exception as e:
            self.log_error(f"Cross validation failed: {e}")
            return {
                "status": "error",
                "agrees_with_primary": False,
                "error": str(e)
            }
            
        finally:
            await browser.stop()
            
    def _determine_verdict(
        self,
        runs: List[Dict],
        cross_validation: Dict
    ) -> Dict:
        """
        Determine final test verdict based on all runs.
        
        Args:
            runs: Results from repeat runs
            cross_validation: Cross-validation result
            
        Returns:
            Final verdict dictionary
        """
        statuses = [r.get("status") for r in runs if r.get("status")]
        
        if not statuses:
            return {
                "result": "INCONCLUSIVE",
                "confidence": 0,
                "reason": "No valid runs completed"
            }
            
        passed = statuses.count("passed")
        failed = statuses.count("failed")
        total = len(statuses)
        
        # Determine result
        if passed == total:
            result = "PASS"
            confidence = 100
            reason = f"All {total} runs passed"
        elif failed == total:
            result = "FAIL"
            confidence = 100
            reason = f"All {total} runs failed"
        elif passed > failed:
            result = "FLAKY"
            confidence = int((passed / total) * 100)
            reason = f"Inconsistent: {passed}/{total} passed"
        else:
            result = "FAIL"
            confidence = int((failed / total) * 100)
            reason = f"Majority failed: {failed}/{total}"
            
        # Adjust based on cross-validation
        if cross_validation.get("agrees_with_primary"):
            confidence = min(100, confidence + 10)
        else:
            confidence = max(0, confidence - 20)
            if result == "PASS":
                result = "FLAKY"
                reason += " (cross-validation disagreement)"
                
        return {
            "result": result,
            "confidence": confidence,
            "reason": reason,
            "pass_count": passed,
            "fail_count": failed,
            "total_runs": total
        }
        
    def _calculate_reproducibility(self, runs: List[Dict]) -> float:
        """
        Calculate reproducibility score.
        
        Args:
            runs: List of test runs
            
        Returns:
            Reproducibility percentage (0-100)
        """
        if not runs:
            return 0.0
            
        statuses = [r.get("status") for r in runs]
        if not statuses:
            return 0.0
            
        # Count most common status
        from collections import Counter
        counts = Counter(statuses)
        most_common_count = counts.most_common(1)[0][1]
        
        return round((most_common_count / len(statuses)) * 100, 2)
        
    def _record_for_learning(
        self,
        url: str,
        test: Dict,
        results: Dict
    ):
        """
        Record test results for progressive learning.
        
        Args:
            url: Game URL
            test: Test case
            results: Execution results
        """
        try:
            verdict = results.get("verdict", {}).get("result", "UNKNOWN")
            reproducibility = results.get("reproducibility", 0)
            
            # Only record successful patterns for learning
            if verdict == "PASS" and reproducibility >= 80:
                self.knowledge_base.add_test_result(
                    game_url=url,
                    test_case=test,
                    result=verdict,
                    execution_time=0,  # Could calculate from results
                    artifacts=None
                )
        except Exception as e:
            self.log_error(f"Failed to record for learning: {e}")
