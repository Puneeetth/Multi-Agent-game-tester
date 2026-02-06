"""
Analyzer Agent - Validates results and generates comprehensive reports
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_agent import BaseAgent
from ..config import settings


class AnalyzerAgent(BaseAgent):
    """
    Analyzes test execution results and generates comprehensive reports.
    Provides:
    - Result validation
    - Reproducibility analysis
    - Triage notes
    - JSON report generation
    """
    
    def __init__(self):
        super().__init__(
            name="Analyzer",
            description="Analyzes results and generates reports"
        )
        
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analysis and report generation."""
        return await self.generate_report(
            session_id=context.get("session_id"),
            game_analysis=context.get("game_analysis", {}),
            test_cases=context.get("test_cases", []),
            execution_results=context.get("execution_results", [])
        )
        
    async def generate_report(
        self,
        session_id: str,
        game_analysis: Dict,
        test_cases: List[Dict],
        execution_results: List[Dict]
    ) -> Dict:
        """
        Generate comprehensive test report.
        
        Args:
            session_id: Session identifier
            game_analysis: Game analysis data
            test_cases: List of test cases
            execution_results: Execution results
            
        Returns:
            Complete report dictionary
        """
        self.log_info(f"Generating report for session {session_id}")
        
        report = {
            "report_id": f"report_{session_id}",
            "session_id": session_id,
            "generated_at": datetime.now().isoformat(),
            "game_info": self._extract_game_info(game_analysis),
            "summary": self._generate_summary(execution_results),
            "test_results": self._format_test_results(execution_results),
            "reproducibility_stats": self._calculate_reproducibility_stats(execution_results),
            "triage_notes": self._generate_triage_notes(execution_results),
            "recommendations": self._generate_recommendations(execution_results),
            "artifacts_summary": self._get_artifacts_summary(session_id)
        }
        
        # Save report to file
        report_path = settings.REPORTS_DIR / f"{session_id}_report.json"
        report_path.write_text(
            json.dumps(report, indent=2, default=str),
            encoding='utf-8'
        )
        report["report_path"] = str(report_path)
        
        self.log_info(f"Report generated: {report_path}")
        return report
        
    def _extract_game_info(self, game_analysis: Dict) -> Dict:
        """Extract relevant game information for report."""
        return {
            "url": game_analysis.get("url", ""),
            "game_type": game_analysis.get("game_type", "unknown"),
            "element_count": game_analysis.get("element_count", 0),
            "mechanics": game_analysis.get("mechanics", []),
            "analyzed_at": game_analysis.get("timestamp", "")
        }
        
    def _generate_summary(self, results: List[Dict]) -> Dict:
        """Generate executive summary of test results."""
        total = len(results)
        
        if total == 0:
            return {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "flaky": 0,
                "inconclusive": 0,
                "pass_rate": 0,
                "overall_status": "NO_TESTS"
            }
            
        passed = sum(1 for r in results if r.get("verdict", {}).get("result") == "PASS")
        failed = sum(1 for r in results if r.get("verdict", {}).get("result") == "FAIL")
        flaky = sum(1 for r in results if r.get("verdict", {}).get("result") == "FLAKY")
        inconclusive = total - passed - failed - flaky
        
        pass_rate = round((passed / total) * 100, 2) if total > 0 else 0
        
        # Determine overall status
        if pass_rate >= 90:
            overall_status = "HEALTHY"
        elif pass_rate >= 70:
            overall_status = "MODERATE"
        elif pass_rate >= 50:
            overall_status = "CONCERNING"
        else:
            overall_status = "CRITICAL"
            
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "flaky": flaky,
            "inconclusive": inconclusive,
            "pass_rate": pass_rate,
            "overall_status": overall_status
        }
        
    def _format_test_results(self, results: List[Dict]) -> List[Dict]:
        """Format individual test results for report."""
        formatted = []
        
        for result in results:
            formatted.append({
                "test_id": result.get("test_id"),
                "test_name": result.get("test_name"),
                "verdict": result.get("verdict", {}),
                "reproducibility": result.get("reproducibility", 0),
                "run_count": len(result.get("runs", [])),
                "cross_validation_agrees": result.get("cross_validation", {}).get("agrees_with_primary", False),
                "executed_at": result.get("executed_at", "")
            })
            
        return formatted
        
    def _calculate_reproducibility_stats(self, results: List[Dict]) -> Dict:
        """Calculate overall reproducibility statistics."""
        if not results:
            return {
                "average_reproducibility": 0,
                "min_reproducibility": 0,
                "max_reproducibility": 0,
                "highly_reproducible": 0,
                "flaky_tests": 0
            }
            
        reproducibilities = [r.get("reproducibility", 0) for r in results]
        
        avg = sum(reproducibilities) / len(reproducibilities)
        highly_reproducible = sum(1 for r in reproducibilities if r >= 90)
        flaky_count = sum(1 for r in reproducibilities if r < 70)
        
        return {
            "average_reproducibility": round(avg, 2),
            "min_reproducibility": min(reproducibilities),
            "max_reproducibility": max(reproducibilities),
            "highly_reproducible": highly_reproducible,
            "flaky_tests": flaky_count
        }
        
    def _generate_triage_notes(self, results: List[Dict]) -> List[Dict]:
        """Generate triage notes for failed/flaky tests."""
        notes = []
        
        for result in results:
            verdict = result.get("verdict", {})
            verdict_result = verdict.get("result", "")
            
            if verdict_result in ["FAIL", "FLAKY"]:
                note = {
                    "test_id": result.get("test_id"),
                    "test_name": result.get("test_name"),
                    "severity": "HIGH" if verdict_result == "FAIL" else "MEDIUM",
                    "issue": verdict.get("reason", "Unknown issue"),
                    "recommended_action": self._get_recommended_action(result),
                    "cross_validation_result": result.get("cross_validation", {}).get("status", "unknown")
                }
                
                # Add error details if available
                runs = result.get("runs", [])
                errors = [r.get("error") for r in runs if r.get("error")]
                if errors:
                    note["errors"] = list(set(errors))[:3]  # Unique errors, max 3
                    
                notes.append(note)
                
        # Sort by severity
        notes.sort(key=lambda x: 0 if x["severity"] == "HIGH" else 1)
        
        return notes
        
    def _get_recommended_action(self, result: Dict) -> str:
        """Get recommended action for a failed/flaky test."""
        verdict = result.get("verdict", {})
        verdict_result = verdict.get("result", "")
        reproducibility = result.get("reproducibility", 0)
        
        if verdict_result == "FAIL":
            if reproducibility == 100:
                return "Consistent failure - investigate root cause immediately"
            else:
                return "Intermittent failure - check for race conditions or async issues"
        elif verdict_result == "FLAKY":
            if reproducibility >= 50:
                return "Mostly passing - tighten test conditions or add waits"
            else:
                return "Highly unstable - review test design and environment"
        else:
            return "Review test execution logs"
            
    def _generate_recommendations(self, results: List[Dict]) -> List[str]:
        """Generate overall recommendations based on results."""
        recommendations = []
        
        summary = self._generate_summary(results)
        repro_stats = self._calculate_reproducibility_stats(results)
        
        # Pass rate recommendations
        if summary["pass_rate"] < 50:
            recommendations.append(
                "Critical: Pass rate is below 50%. Prioritize fixing core functionality tests."
            )
        elif summary["pass_rate"] < 80:
            recommendations.append(
                "Warning: Pass rate is below 80%. Review and fix failing tests."
            )
            
        # Flaky test recommendations
        if repro_stats["flaky_tests"] > 0:
            recommendations.append(
                f"Found {repro_stats['flaky_tests']} flaky tests. Consider adding explicit waits or stabilizing test environment."
            )
            
        # Reproducibility recommendations
        if repro_stats["average_reproducibility"] < 80:
            recommendations.append(
                "Average reproducibility is low. Tests may be affected by timing issues or external factors."
            )
            
        # General recommendations
        if summary["inconclusive"] > 0:
            recommendations.append(
                f"{summary['inconclusive']} tests were inconclusive. Review test execution logs for errors."
            )
            
        if not recommendations:
            recommendations.append(
                "Test suite is healthy! Consider expanding test coverage."
            )
            
        return recommendations
        
    def _get_artifacts_summary(self, session_id: str) -> Dict:
        """Get summary of captured artifacts."""
        artifacts_dir = settings.ARTIFACTS_DIR / session_id
        
        if not artifacts_dir.exists():
            return {"total_artifacts": 0, "types": {}}
            
        artifacts = list(artifacts_dir.glob("**/*"))
        files = [f for f in artifacts if f.is_file()]
        
        # Count by type
        type_counts = {}
        for f in files:
            ext = f.suffix[1:] if f.suffix else "other"
            type_counts[ext] = type_counts.get(ext, 0) + 1
            
        return {
            "total_artifacts": len(files),
            "types": type_counts,
            "directory": str(artifacts_dir)
        }
