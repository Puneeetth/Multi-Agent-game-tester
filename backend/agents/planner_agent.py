"""
Planner Agent - Generates 20+ test cases using LangChain
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_community.llms import Ollama
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from .base_agent import BaseAgent
from ..rag.knowledge_base import KnowledgeBase
from ..config import settings


class PlannerAgent(BaseAgent):
    """
    Generates comprehensive test cases for game testing.
    Uses LangChain with local Ollama model to create intelligent tests.
    """
    
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        super().__init__(
            name="Planner",
            description="Generates test cases using LangChain and RAG"
        )
        self.knowledge_base = knowledge_base or KnowledgeBase()
        self.model_name = settings.OLLAMA_TEXT_MODEL
        
        if LANGCHAIN_AVAILABLE:
            self.llm = Ollama(
                model=self.model_name,
                temperature=0.7
            )
        else:
            self.llm = None
            
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute test generation."""
        game_analysis = context.get("game_analysis", {})
        url = context.get("url", "")
        min_count = context.get("min_count", settings.MIN_TEST_CASES)
        
        tests = await self.generate_tests(game_analysis, url, min_count)
        return {"test_cases": tests}
        
    async def generate_tests(
        self,
        game_analysis: Dict[str, Any],
        url: str,
        min_count: int = 20
    ) -> List[Dict]:
        """
        Generate test cases based on game analysis.
        
        Args:
            game_analysis: Results from GameAnalyzerAgent
            url: Game URL
            min_count: Minimum number of tests to generate
            
        Returns:
            List of test case dictionaries
        """
        self.log_info(f"Generating {min_count}+ test cases for {url}")
        
        test_cases = []
        
        # Get related patterns from knowledge base
        game_type = game_analysis.get("game_type", "puzzle")
        patterns = self.knowledge_base.search_patterns(
            f"{game_type} game testing strategies",
            n_results=5
        )
        
        if self.llm:
            # Use LangChain for intelligent test generation
            test_cases = await self._generate_with_langchain(
                game_analysis, patterns, min_count
            )
        else:
            # Fallback to template-based generation
            test_cases = self._generate_template_tests(
                game_analysis, patterns, min_count
            )
            
        # Ensure we have at least min_count tests
        if len(test_cases) < min_count:
            additional = self._generate_additional_tests(
                game_analysis,
                min_count - len(test_cases)
            )
            test_cases.extend(additional)
            
        # Add IDs and metadata
        for i, test in enumerate(test_cases):
            test["id"] = i + 1
            test["generated_at"] = datetime.now().isoformat()
            if "priority" not in test:
                test["priority"] = "medium"
            if "category" not in test:
                test["category"] = "functional"
                
        self.log_info(f"Generated {len(test_cases)} test cases")
        return test_cases
        
    async def _generate_with_langchain(
        self,
        game_analysis: Dict,
        patterns: List[Dict],
        min_count: int
    ) -> List[Dict]:
        """
        Generate tests using LangChain and Ollama.
        
        Args:
            game_analysis: Game analysis results
            patterns: Related patterns from knowledge base
            min_count: Minimum test count
            
        Returns:
            List of test cases
        """
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert game tester. Generate comprehensive test cases for web-based games.
Each test case should include: name, description, steps (list of actions), expected_result, priority (high/medium/low), category.

Categories: functional, ui, edge_case, performance, usability

Output ONLY valid JSON array of test cases. No explanation text."""),
            ("human", """Game Analysis:
- Game Type: {game_type}
- URL: {url}
- Interactive Elements: {element_count} elements found
- Game Mechanics: {mechanics}
- UI Description: {ui_description}
- Recommendations: {recommendations}

Related Testing Patterns:
{patterns}

Generate exactly {min_count} unique, comprehensive test cases covering:
1. Core functionality tests (at least 8)
2. UI/UX tests (at least 5)
3. Edge cases (at least 4)
4. Performance tests (at least 2)
5. Usability tests (at least 1)

Output format - JSON array:
[
  {{
    "name": "Test Name",
    "description": "What this tests",
    "steps": ["Step 1", "Step 2"],
    "expected_result": "Expected outcome",
    "priority": "high|medium|low",
    "category": "functional|ui|edge_case|performance|usability"
  }}
]""")
        ])
        
        try:
            chain = prompt_template | self.llm
            
            # Format patterns for prompt
            patterns_text = "\n".join([
                f"- {p.get('content', str(p))[:200]}"
                for p in patterns[:3]
            ]) if patterns else "No specific patterns found"
            
            response = await chain.ainvoke({
                "game_type": game_analysis.get("game_type", "puzzle"),
                "url": game_analysis.get("url", ""),
                "element_count": game_analysis.get("element_count", 0),
                "mechanics": json.dumps(game_analysis.get("mechanics", [])),
                "ui_description": game_analysis.get("ui_description", "")[:500],
                "recommendations": json.dumps(game_analysis.get("test_recommendations", [])[:5]),
                "patterns": patterns_text,
                "min_count": min_count
            })
            
            # Parse response
            content = response.content
            
            # Extract JSON from response
            start = content.find("[")
            end = content.rfind("]") + 1
            
            if start >= 0 and end > start:
                tests = json.loads(content[start:end])
                if isinstance(tests, list):
                    return tests
                    
        except Exception as e:
            self.log_error(f"LangChain generation failed: {e}")
            
        return self._generate_template_tests(game_analysis, patterns, min_count)
        
    def _generate_template_tests(
        self,
        game_analysis: Dict,
        patterns: List[Dict],
        min_count: int
    ) -> List[Dict]:
        """
        Generate tests using templates when LangChain is unavailable.
        
        Args:
            game_analysis: Game analysis results
            patterns: Related patterns
            min_count: Minimum test count
            
        Returns:
            List of test cases
        """
        game_type = game_analysis.get("game_type", "puzzle")
        elements = game_analysis.get("elements", [])
        mechanics = game_analysis.get("mechanics", [])
        
        tests = []
        
        # Core Functional Tests
        tests.extend([
            {
                "name": "Game Page Load Test",
                "description": "Verify the game page loads correctly",
                "steps": ["Navigate to game URL", "Wait for page to fully load", "Verify game container is visible"],
                "expected_result": "Game loads without errors and displays correctly",
                "priority": "high",
                "category": "functional"
            },
            {
                "name": "Start New Game Test",
                "description": "Verify a new game can be started",
                "steps": ["Load game page", "Click start/play button if present", "Verify game state changes to playing"],
                "expected_result": "New game starts successfully",
                "priority": "high",
                "category": "functional"
            },
            {
                "name": "Game Restart Test",
                "description": "Verify game can be restarted",
                "steps": ["Start a game", "Make some moves", "Find and click restart button", "Verify game resets"],
                "expected_result": "Game resets to initial state",
                "priority": "high",
                "category": "functional"
            },
            {
                "name": "Score Display Test",
                "description": "Verify score is displayed and updates",
                "steps": ["Start game", "Perform scoring action", "Check score display"],
                "expected_result": "Score updates correctly after actions",
                "priority": "high",
                "category": "functional"
            },
            {
                "name": "Valid Game Move Test",
                "description": "Test making a valid game move",
                "steps": ["Start game", "Identify valid move", "Execute the move", "Verify state change"],
                "expected_result": "Valid move is accepted and game state updates",
                "priority": "high",
                "category": "functional"
            },
            {
                "name": "Invalid Move Handling Test",
                "description": "Test that invalid moves are rejected",
                "steps": ["Start game", "Attempt invalid action", "Verify rejection feedback"],
                "expected_result": "Invalid move is rejected with appropriate feedback",
                "priority": "high",
                "category": "functional"
            },
            {
                "name": "Game State Persistence Test",
                "description": "Verify game state persists correctly",
                "steps": ["Start game", "Make moves", "Verify state reflects all actions"],
                "expected_result": "All game actions are properly tracked",
                "priority": "medium",
                "category": "functional"
            },
            {
                "name": "Win Condition Test",
                "description": "Verify win condition is detected",
                "steps": ["Play game towards win state", "Complete winning move", "Verify win detection"],
                "expected_result": "Win is detected and displayed",
                "priority": "high",
                "category": "functional"
            }
        ])
        
        # UI Tests
        tests.extend([
            {
                "name": "UI Elements Visibility Test",
                "description": "Verify all UI elements are visible",
                "steps": ["Load game page", f"Check visibility of {len(elements)} interactive elements"],
                "expected_result": "All UI elements are visible and properly positioned",
                "priority": "high",
                "category": "ui"
            },
            {
                "name": "Button Click Response Test",
                "description": "Verify buttons respond to clicks",
                "steps": ["Find all buttons", "Click each button", "Verify visual feedback"],
                "expected_result": "All buttons provide click feedback",
                "priority": "high",
                "category": "ui"
            },
            {
                "name": "Modal Dialog Test",
                "description": "Verify modal dialogs work correctly",
                "steps": ["Trigger modal (settings/pause)", "Verify modal appears", "Close modal", "Verify closure"],
                "expected_result": "Modals open and close correctly",
                "priority": "medium",
                "category": "ui"
            },
            {
                "name": "Settings Panel Test",
                "description": "Verify settings panel functionality",
                "steps": ["Open settings", "Toggle options", "Apply changes", "Verify changes take effect"],
                "expected_result": "Settings can be changed and are applied",
                "priority": "medium",
                "category": "ui"
            },
            {
                "name": "Responsive Layout Test",
                "description": "Verify game adapts to window size",
                "steps": ["Load game at full size", "Resize window", "Verify layout adapts"],
                "expected_result": "Game remains playable at different sizes",
                "priority": "medium",
                "category": "ui"
            }
        ])
        
        # Edge Case Tests
        tests.extend([
            {
                "name": "Rapid Click Stress Test",
                "description": "Verify game handles rapid clicking",
                "steps": ["Start game", "Rapidly click game elements", "Verify stability"],
                "expected_result": "Game remains stable under rapid input",
                "priority": "medium",
                "category": "edge_case"
            },
            {
                "name": "Browser Refresh Test",
                "description": "Verify behavior on page refresh",
                "steps": ["Start game", "Refresh page", "Verify appropriate behavior"],
                "expected_result": "Game handles refresh gracefully",
                "priority": "medium",
                "category": "edge_case"
            },
            {
                "name": "Multiple Tab Test",
                "description": "Test game in multiple tabs",
                "steps": ["Open game in tab 1", "Open same game in tab 2", "Interact in both"],
                "expected_result": "Each tab operates independently",
                "priority": "low",
                "category": "edge_case"
            },
            {
                "name": "No Valid Moves Test",
                "description": "Verify handling when no moves available",
                "steps": ["Reach state with no valid moves", "Verify game handles this"],
                "expected_result": "Game indicates no moves and offers restart",
                "priority": "medium",
                "category": "edge_case"
            }
        ])
        
        # Performance Tests
        tests.extend([
            {
                "name": "Initial Load Time Test",
                "description": "Measure game load time",
                "steps": ["Clear cache", "Navigate to game", "Measure time to interactive"],
                "expected_result": "Game loads within 3 seconds",
                "priority": "medium",
                "category": "performance"
            },
            {
                "name": "Animation Smoothness Test",
                "description": "Verify animations are smooth",
                "steps": ["Trigger game animations", "Observe frame rate", "Check for jank"],
                "expected_result": "Animations run at 60fps without stuttering",
                "priority": "low",
                "category": "performance"
            }
        ])
        
        # Usability Tests
        tests.extend([
            {
                "name": "Tutorial/Help Test",
                "description": "Verify help is available and useful",
                "steps": ["Look for help/tutorial", "Access help content", "Verify it explains gameplay"],
                "expected_result": "Clear instructions are available",
                "priority": "low",
                "category": "usability"
            }
        ])
        
        # Add game-type specific tests
        if game_type == "math" or "number" in str(mechanics).lower():
            tests.extend([
                {
                    "name": "Number Sum Validation Test",
                    "description": "Verify number sums are calculated correctly",
                    "steps": ["Select numbers", "Submit combination", "Verify sum calculation"],
                    "expected_result": "Sum is calculated correctly",
                    "priority": "high",
                    "category": "functional"
                },
                {
                    "name": "Number Selection Test",
                    "description": "Test selecting and deselecting numbers",
                    "steps": ["Select a number", "Verify selection indicator", "Deselect", "Verify deselection"],
                    "expected_result": "Selection state is clearly shown",
                    "priority": "high",
                    "category": "functional"
                }
            ])
            
        return tests[:min_count]
        
    def _generate_additional_tests(
        self,
        game_analysis: Dict,
        count: int
    ) -> List[Dict]:
        """Generate additional tests to meet minimum count."""
        elements = game_analysis.get("elements", [])
        additional = []
        
        for i in range(count):
            element = elements[i % len(elements)] if elements else {"tag": "element", "text": f"element_{i}"}
            additional.append({
                "name": f"Element Interaction Test {i+1}",
                "description": f"Test interaction with {element.get('tag', 'element')} element",
                "steps": [
                    f"Locate element: {element.get('text', 'N/A')[:30]}",
                    "Click the element",
                    "Verify response"
                ],
                "expected_result": "Element responds appropriately to interaction",
                "priority": "medium",
                "category": "functional"
            })
            
        return additional
