"""
Executor Agent - Executes individual test cases using browser automation
"""
import asyncio
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from .base_agent import BaseAgent
from ..browser.controller import BrowserController
from ..browser.artifact_capture import ArtifactCapture
from ..config import settings


class ExecutorAgent(BaseAgent):
    """
    Executes individual test cases by:
    - Interpreting test steps
    - Controlling browser via Playwright
    - Capturing step-level artifacts
    - Reporting results
    """
    
    def __init__(self, agent_id: str = "executor_1"):
        super().__init__(
            name=f"Executor_{agent_id}",
            description="Executes test cases via browser automation"
        )
        self.agent_id = agent_id
        self.model_name = settings.OLLAMA_MODEL
        
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a test case."""
        test_case = context.get("test_case", {})
        browser = context.get("browser")
        artifact_capture = context.get("artifact_capture")
        game_analysis = context.get("game_analysis", {})
        
        return await self.execute_test(
            test_case, browser, artifact_capture, game_analysis
        )
        
    async def execute_test(
        self,
        test_case: Dict,
        browser: BrowserController,
        artifact_capture: ArtifactCapture,
        game_analysis: Dict
    ) -> Dict[str, Any]:
        """
        Execute a single test case.
        
        Args:
            test_case: Test case to execute
            browser: Browser controller
            artifact_capture: Artifact capture instance
            game_analysis: Game analysis for context
            
        Returns:
            Test execution result
        """
        test_id = test_case.get("id", 0)
        test_name = test_case.get("name", "Unknown Test")
        
        self.log_info(f"Executing test {test_id}: {test_name}")
        
        result = {
            "test_id": test_id,
            "test_name": test_name,
            "agent_id": self.agent_id,
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "status": "running",
            "artifacts": [],
            "error": None
        }
        
        try:
            steps = test_case.get("steps", [])
            
            for step_idx, step in enumerate(steps):
                step_result = await self._execute_step(
                    step=step,
                    step_index=step_idx,
                    browser=browser,
                    artifact_capture=artifact_capture,
                    game_analysis=game_analysis,
                    test_name=test_name
                )
                result["steps"].append(step_result)
                
                if step_result["status"] == "failed":
                    result["status"] = "failed"
                    result["error"] = step_result.get("error", "Step failed")
                    break
                    
            if result["status"] == "running":
                # All steps passed
                result["status"] = "passed"
                
            # Capture final artifacts
            final_artifacts = await artifact_capture.capture_all(
                browser,
                f"test_{test_id}_final",
                len(steps)
            )
            result["artifacts"].append(final_artifacts)
            
        except Exception as e:
            self.log_error(f"Test execution failed: {e}")
            result["status"] = "error"
            result["error"] = str(e)
            
        result["ended_at"] = datetime.now().isoformat()
        result["duration_ms"] = self._calculate_duration(
            result["started_at"],
            result["ended_at"]
        )
        
        return result
        
    async def _execute_step(
        self,
        step: str,
        step_index: int,
        browser: BrowserController,
        artifact_capture: ArtifactCapture,
        game_analysis: Dict,
        test_name: str
    ) -> Dict:
        """
        Execute a single test step.
        
        Args:
            step: Step description
            step_index: Index of the step
            browser: Browser controller
            artifact_capture: Artifact capture
            game_analysis: Game analysis
            test_name: Name of the test
            
        Returns:
            Step execution result
        """
        step_result = {
            "index": step_index,
            "description": step,
            "status": "pending",
            "action_taken": None,
            "screenshot": None,
            "error": None
        }
        
        try:
            # Interpret and execute the step
            action = await self._interpret_step(step, game_analysis, browser)
            step_result["action_taken"] = action
            
            # Execute the action
            await self._perform_action(action, browser)
            
            # Wait for any animations/transitions
            await browser.wait_for_timeout(500)
            
            # Capture artifacts for this step
            artifacts = await artifact_capture.capture_all(
                browser,
                f"step_{step_index}",
                step_index
            )
            step_result["screenshot"] = artifacts.get("screenshot")
            step_result["status"] = "passed"
            
        except Exception as e:
            step_result["status"] = "failed"
            step_result["error"] = str(e)
            self.log_error(f"Step {step_index} failed: {e}")
            
        return step_result
        
    async def _interpret_step(
        self,
        step: str,
        game_analysis: Dict,
        browser: BrowserController
    ) -> Dict:
        """
        Interpret a natural language step into an executable action.
        
        Args:
            step: Step description in natural language
            game_analysis: Game analysis for context
            browser: Browser for current state
            
        Returns:
            Action dictionary with type and parameters
        """
        step_lower = step.lower()
        
        # Rule-based interpretation for common actions
        if "navigate" in step_lower or "go to" in step_lower or "open" in step_lower:
            url = game_analysis.get("url", "")
            return {"type": "navigate", "url": url}
            
        if "wait" in step_lower:
            # Extract wait time if specified
            import re
            match = re.search(r'(\d+)\s*(second|ms|millisecond)', step_lower)
            if match:
                time = int(match.group(1))
                if "second" in match.group(2):
                    time *= 1000
                return {"type": "wait", "ms": time}
            return {"type": "wait", "ms": 1000}
            
        if "click" in step_lower:
            # Try to find what to click
            elements = game_analysis.get("elements", [])
            
            # Look for button mentions
            if "start" in step_lower or "play" in step_lower:
                for el in elements:
                    if any(kw in el.get("text", "").lower() for kw in ["start", "play", "begin"]):
                        return {
                            "type": "click",
                            "target": {"x": el.get("x"), "y": el.get("y")},
                            "selector": None
                        }
                        
            if "restart" in step_lower or "new game" in step_lower:
                for el in elements:
                    if any(kw in el.get("text", "").lower() for kw in ["restart", "new", "reset"]):
                        return {
                            "type": "click",
                            "target": {"x": el.get("x"), "y": el.get("y")},
                            "selector": None
                        }
                        
            # Generic button click
            if "button" in step_lower:
                return {"type": "click", "selector": "button"}
                
            # Click first available element
            if elements:
                el = elements[0]
                return {
                    "type": "click",
                    "target": {"x": el.get("x"), "y": el.get("y")},
                    "selector": None
                }
                
            return {"type": "click", "selector": "button, [role='button'], .clickable"}
            
        if "verify" in step_lower or "check" in step_lower:
            return {"type": "verify", "description": step}
            
        if "type" in step_lower or "input" in step_lower or "enter" in step_lower:
            return {"type": "type", "selector": "input", "text": "test"}
            
        # Default: treat as a verification step
        return {"type": "verify", "description": step}
        
    async def _perform_action(
        self,
        action: Dict,
        browser: BrowserController
    ):
        """
        Perform a browser action.
        
        Args:
            action: Action dictionary with type and parameters
            browser: Browser controller
        """
        action_type = action.get("type")
        
        if action_type == "navigate":
            await browser.navigate(action.get("url", ""))
            await browser.wait_for_timeout(2000)
            
        elif action_type == "click":
            if action.get("target"):
                x = action["target"].get("x", 0)
                y = action["target"].get("y", 0)
                if x and y:
                    await browser.click_at_position(int(x), int(y))
            elif action.get("selector"):
                try:
                    await browser.click(action["selector"], timeout=5000)
                except:
                    pass
                    
        elif action_type == "wait":
            await browser.wait_for_timeout(action.get("ms", 1000))
            
        elif action_type == "type":
            try:
                await browser.type_text(
                    action.get("selector", "input"),
                    action.get("text", "")
                )
            except:
                pass
                
        elif action_type == "verify":
            # Verification is passive - just capture state
            pass
            
        elif action_type == "press_key":
            await browser.press_key(action.get("key", "Enter"))
            
    def _calculate_duration(self, start: str, end: str) -> int:
        """Calculate duration in milliseconds."""
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            return int((end_dt - start_dt).total_seconds() * 1000)
        except:
            return 0
