"""
Game Analyzer Agent - Uses vision model to understand game mechanics
"""
import base64
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from .base_agent import BaseAgent
from ..browser.controller import BrowserController
from ..rag.knowledge_base import KnowledgeBase
from ..config import settings


class GameAnalyzerAgent(BaseAgent):
    """
    Analyzes games using vision-based AI to understand:
    - Game layout and UI elements
    - Game mechanics and rules
    - Interactive elements and their purposes
    - Current game state
    """
    
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        super().__init__(
            name="GameAnalyzer",
            description="Analyzes games using vision AI to understand mechanics"
        )
        self.knowledge_base = knowledge_base or KnowledgeBase()
        self.ollama_model = settings.OLLAMA_MODEL
        
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute game analysis."""
        browser = context.get("browser")
        url = context.get("url")
        session_id = context.get("session_id")
        
        return await self.analyze(browser, url, session_id)
        
    async def analyze(
        self,
        browser: BrowserController,
        url: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Perform comprehensive game analysis.
        
        Args:
            browser: Browser controller instance
            url: Game URL
            session_id: Session identifier
            
        Returns:
            Dictionary with game analysis results
        """
        self.log_info(f"Starting analysis of {url}")
        
        analysis = {
            "url": url,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "game_type": "unknown",
            "elements": [],
            "mechanics": [],
            "ui_description": "",
            "test_recommendations": [],
            "element_count": 0
        }
        
        try:
            # Navigate to game
            await browser.navigate(url)
            await browser.wait_for_timeout(2000)  # Wait for game to load
            
            # Capture initial screenshot
            screenshot_path = settings.ARTIFACTS_DIR / session_id
            screenshot_path.mkdir(parents=True, exist_ok=True)
            initial_screenshot = str(screenshot_path / "initial_analysis.png")
            await browser.screenshot(initial_screenshot)
            
            # Get interactive elements
            interactive_elements = await browser.find_interactive_elements()
            analysis["elements"] = interactive_elements
            analysis["element_count"] = len(interactive_elements)
            
            # Get game state
            game_state = await browser.get_game_state()
            analysis["initial_state"] = game_state
            
            # Get DOM structure
            dom = await browser.get_dom()
            analysis["dom_size"] = len(dom)
            
            # Use vision model to analyze screenshot
            if OLLAMA_AVAILABLE:
                vision_analysis = await self._analyze_screenshot(initial_screenshot)
                analysis.update(vision_analysis)
            else:
                # Fallback to heuristic analysis
                analysis.update(self._heuristic_analysis(interactive_elements, game_state, dom))
            
            # Search knowledge base for similar patterns
            patterns = self.knowledge_base.search_patterns(
                f"{analysis['game_type']} game testing",
                n_results=3
            )
            if patterns:
                analysis["related_patterns"] = [p.get("content", str(p)) for p in patterns]
            
            # Generate test recommendations
            analysis["test_recommendations"] = self._generate_recommendations(analysis)
            
            self.log_info(f"Analysis complete: {analysis['game_type']} game with {analysis['element_count']} elements")
            
        except Exception as e:
            self.log_error(f"Analysis failed: {e}")
            analysis["error"] = str(e)
            # Provide fallback analysis
            analysis["game_type"] = "puzzle"
            analysis["test_recommendations"] = self._get_default_recommendations()
            
        return analysis
        
    async def _analyze_screenshot(self, screenshot_path: str) -> Dict[str, Any]:
        """
        Use vision model to analyze game screenshot.
        
        Args:
            screenshot_path: Path to screenshot file
            
        Returns:
            Dictionary with vision analysis results
        """
        try:
            # Read and encode image
            with open(screenshot_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            prompt = """Analyze this game screenshot and provide:
1. Game Type: What type of game is this? (puzzle, math, matching, card, etc.)
2. Game Mechanics: How does the game appear to work? What are the rules?
3. Interactive Elements: What can the player interact with?
4. Current State: What state is the game in? (menu, playing, paused, game over)
5. UI Description: Describe the overall UI layout.

Respond in JSON format:
{
    "game_type": "type of game",
    "mechanics": ["list of game mechanics"],
    "ui_description": "description of the UI",
    "game_state": "current state",
    "key_elements": ["list of key interactive elements"]
}"""
            
            response = ollama.chat(
                model=self.ollama_model,
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": [image_data]
                }]
            )
            
            # Parse response
            content = response["message"]["content"]
            
            # Try to extract JSON from response
            try:
                # Find JSON in response
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    parsed = json.loads(content[start:end])
                    return parsed
            except:
                pass
            
            # Return raw analysis if JSON parsing fails
            return {
                "game_type": "puzzle",
                "mechanics": ["visual analysis available"],
                "ui_description": content[:500],
                "vision_raw": content
            }
            
        except Exception as e:
            self.log_error(f"Vision analysis failed: {e}")
            return {
                "game_type": "puzzle",
                "mechanics": ["vision analysis unavailable"],
                "vision_error": str(e)
            }
            
    def _heuristic_analysis(
        self,
        elements: List[Dict],
        game_state: Dict,
        dom: str
    ) -> Dict[str, Any]:
        """
        Perform heuristic-based game analysis when vision is unavailable.
        
        Args:
            elements: Interactive elements found
            game_state: Current game state
            dom: Page DOM
            
        Returns:
            Dictionary with heuristic analysis
        """
        analysis = {
            "game_type": "puzzle",
            "mechanics": [],
            "ui_description": ""
        }
        
        dom_lower = dom.lower()
        
        # Detect game type from DOM content
        if "number" in dom_lower or "sum" in dom_lower or "math" in dom_lower:
            analysis["game_type"] = "math"
            analysis["mechanics"].append("number-based gameplay")
            
        if "match" in dom_lower or "pair" in dom_lower:
            analysis["mechanics"].append("matching elements")
            
        if "score" in dom_lower:
            analysis["mechanics"].append("scoring system")
            
        if "timer" in dom_lower or "time" in dom_lower:
            analysis["mechanics"].append("time-based challenge")
            
        if "level" in dom_lower or "stage" in dom_lower:
            analysis["mechanics"].append("level progression")
            
        # Analyze elements
        button_count = sum(1 for e in elements if e.get("tag") == "button")
        if button_count > 5:
            analysis["mechanics"].append("multiple interactive buttons/tiles")
            
        # Check for canvas (often used in games)
        if "canvas" in dom_lower:
            analysis["mechanics"].append("canvas-based rendering")
            
        analysis["ui_description"] = (
            f"Found {len(elements)} interactive elements including "
            f"{button_count} buttons. "
            f"Game appears to be a {analysis['game_type']} type."
        )
        
        return analysis
        
    def _generate_recommendations(self, analysis: Dict) -> List[Dict]:
        """
        Generate test recommendations based on analysis.
        
        Args:
            analysis: Game analysis results
            
        Returns:
            List of test recommendations
        """
        recommendations = []
        
        game_type = analysis.get("game_type", "puzzle")
        mechanics = analysis.get("mechanics", [])
        elements = analysis.get("elements", [])
        
        # UI element tests
        recommendations.append({
            "category": "UI",
            "name": "Verify all interactive elements are clickable",
            "priority": "high",
            "description": f"Test clicking each of the {len(elements)} interactive elements"
        })
        
        # Based on mechanics
        if "scoring system" in str(mechanics).lower():
            recommendations.append({
                "category": "Functionality",
                "name": "Verify score updates correctly",
                "priority": "high",
                "description": "Perform game actions and verify score changes"
            })
            
        if "number" in str(mechanics).lower() or game_type == "math":
            recommendations.append({
                "category": "Functionality",
                "name": "Test number matching/calculation",
                "priority": "high",
                "description": "Test valid and invalid number combinations"
            })
            
        # Always include
        recommendations.append({
            "category": "UI",
            "name": "Test game start/restart",
            "priority": "high",
            "description": "Verify game can be started and restarted"
        })
        
        recommendations.append({
            "category": "Edge Case",
            "name": "Test rapid clicking",
            "priority": "medium",
            "description": "Rapidly click elements to test debouncing"
        })
        
        recommendations.append({
            "category": "UI",
            "name": "Test modal dialogs",
            "priority": "medium",
            "description": "Verify popups and modals work correctly"
        })
        
        return recommendations
        
    def _get_default_recommendations(self) -> List[Dict]:
        """Get default test recommendations when analysis fails."""
        return [
            {"category": "UI", "name": "Test page load", "priority": "high", "description": "Verify game loads correctly"},
            {"category": "UI", "name": "Test interactive elements", "priority": "high", "description": "Click all visible buttons"},
            {"category": "Functionality", "name": "Test game mechanics", "priority": "high", "description": "Perform basic game actions"},
            {"category": "UI", "name": "Test navigation", "priority": "medium", "description": "Test any navigation elements"},
            {"category": "Edge Case", "name": "Test error handling", "priority": "low", "description": "Verify graceful error handling"}
        ]
