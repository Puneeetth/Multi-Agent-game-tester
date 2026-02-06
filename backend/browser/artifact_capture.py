"""
Artifact Capture - Captures screenshots, DOM, logs, and network data
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..config import settings
from .controller import BrowserController


class ArtifactCapture:
    """
    Captures and stores test artifacts including:
    - Screenshots (PNG)
    - DOM snapshots (HTML)
    - Console logs (JSON)
    - Network logs (JSON)
    """
    
    def __init__(self, session_id: str):
        """
        Initialize artifact capture for a session.
        
        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.artifacts_dir = settings.ARTIFACTS_DIR / session_id
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_index: List[Dict] = []
        
    async def capture_all(
        self,
        browser: BrowserController,
        step_name: str,
        step_index: int
    ) -> Dict[str, str]:
        """
        Capture all artifacts for a test step.
        
        Args:
            browser: Browser controller instance
            step_name: Name of the test step
            step_index: Index of the step
            
        Returns:
            Dictionary with paths to all captured artifacts
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"step_{step_index:03d}_{step_name}_{timestamp}"
        
        artifacts = {}
        
        # Capture screenshot
        screenshot_path = await self.capture_screenshot(browser, prefix)
        artifacts["screenshot"] = screenshot_path
        
        # Capture DOM
        dom_path = await self.capture_dom(browser, prefix)
        artifacts["dom"] = dom_path
        
        # Capture console logs
        console_path = self.capture_console_logs(browser, prefix)
        artifacts["console_logs"] = console_path
        
        # Capture network logs
        network_path = self.capture_network_logs(browser, prefix)
        artifacts["network_logs"] = network_path
        
        # Update artifact index
        self.artifact_index.append({
            "step_index": step_index,
            "step_name": step_name,
            "timestamp": timestamp,
            "artifacts": artifacts
        })
        
        # Save index
        self._save_index()
        
        return artifacts
        
    async def capture_screenshot(
        self,
        browser: BrowserController,
        prefix: str,
        full_page: bool = False
    ) -> str:
        """
        Capture a screenshot.
        
        Args:
            browser: Browser controller instance
            prefix: File prefix
            full_page: Whether to capture full page
            
        Returns:
            Path to saved screenshot
        """
        filename = f"{prefix}_screenshot.png"
        path = str(self.artifacts_dir / filename)
        await browser.screenshot(path, full_page=full_page)
        return filename
        
    async def capture_dom(self, browser: BrowserController, prefix: str) -> str:
        """
        Capture DOM snapshot.
        
        Args:
            browser: Browser controller instance
            prefix: File prefix
            
        Returns:
            Path to saved DOM file
        """
        filename = f"{prefix}_dom.html"
        path = self.artifacts_dir / filename
        
        dom = await browser.get_dom()
        path.write_text(dom, encoding='utf-8')
        
        return filename
        
    def capture_console_logs(self, browser: BrowserController, prefix: str) -> str:
        """
        Capture console logs.
        
        Args:
            browser: Browser controller instance
            prefix: File prefix
            
        Returns:
            Path to saved logs file
        """
        filename = f"{prefix}_console.json"
        path = self.artifacts_dir / filename
        
        logs = browser.get_console_logs()
        path.write_text(json.dumps(logs, indent=2), encoding='utf-8')
        
        return filename
        
    def capture_network_logs(self, browser: BrowserController, prefix: str) -> str:
        """
        Capture network logs.
        
        Args:
            browser: Browser controller instance
            prefix: File prefix
            
        Returns:
            Path to saved logs file
        """
        filename = f"{prefix}_network.json"
        path = self.artifacts_dir / filename
        
        logs = browser.get_network_logs()
        path.write_text(json.dumps(logs, indent=2), encoding='utf-8')
        
        return filename
        
    def save_custom_artifact(
        self,
        name: str,
        data: Any,
        file_type: str = "json"
    ) -> str:
        """
        Save a custom artifact.
        
        Args:
            name: Artifact name
            data: Data to save
            file_type: File type (json, txt, html)
            
        Returns:
            Path to saved file
        """
        filename = f"{name}.{file_type}"
        path = self.artifacts_dir / filename
        
        if file_type == "json":
            path.write_text(json.dumps(data, indent=2, default=str), encoding='utf-8')
        else:
            path.write_text(str(data), encoding='utf-8')
            
        return filename
        
    def _save_index(self):
        """Save the artifact index."""
        index_path = self.artifacts_dir / "index.json"
        index_path.write_text(
            json.dumps(self.artifact_index, indent=2),
            encoding='utf-8'
        )
        
    def get_artifacts_summary(self) -> Dict:
        """
        Get a summary of all captured artifacts.
        
        Returns:
            Dictionary with artifact summary
        """
        return {
            "session_id": self.session_id,
            "artifacts_dir": str(self.artifacts_dir),
            "total_steps": len(self.artifact_index),
            "steps": self.artifact_index
        }
