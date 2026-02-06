"""
Knowledge Base - RAG system for progressive learning
Uses ChromaDB for vector storage of game patterns and test strategies.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from ..config import settings


class KnowledgeBase:
    """
    Vector-based knowledge store for game patterns and test strategies.
    Enables progressive learning by storing successful test patterns.
    """
    
    def __init__(self):
        """Initialize the knowledge base."""
        self.rag_dir = settings.RAG_DIR
        self.rag_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = None
        self.collection = None
        
        if CHROMA_AVAILABLE:
            self._init_chroma()
        else:
            # Fallback to file-based storage
            self.patterns_file = self.rag_dir / "patterns.json"
            self.patterns = self._load_patterns()
            
    def _init_chroma(self):
        """Initialize ChromaDB client and collection."""
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.rag_dir / "chroma_db")
            )
            self.collection = self.client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION,
                metadata={"description": "Game testing patterns and strategies"}
            )
        except Exception as e:
            print(f"ChromaDB init failed: {e}, using file-based fallback")
            self.client = None
            self.patterns_file = self.rag_dir / "patterns.json"
            self.patterns = self._load_patterns()
            
    def _load_patterns(self) -> List[Dict]:
        """Load patterns from file."""
        if hasattr(self, 'patterns_file') and self.patterns_file.exists():
            try:
                return json.loads(self.patterns_file.read_text())
            except:
                pass
        return []
        
    def _save_patterns(self):
        """Save patterns to file."""
        if hasattr(self, 'patterns_file'):
            self.patterns_file.write_text(
                json.dumps(self.patterns, indent=2, default=str)
            )
            
    def _generate_id(self, content: str) -> str:
        """Generate a unique ID from content."""
        return hashlib.md5(content.encode()).hexdigest()[:12]
        
    def add_game_pattern(
        self,
        game_type: str,
        pattern_name: str,
        description: str,
        test_strategy: str,
        success_rate: float = 0.0,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add a game pattern to the knowledge base.
        
        Args:
            game_type: Type of game (puzzle, math, matching, etc.)
            pattern_name: Name of the pattern
            description: Description of the pattern
            test_strategy: Recommended testing strategy
            success_rate: Historical success rate (0-1)
            metadata: Additional metadata
            
        Returns:
            ID of the added pattern
        """
        content = f"{game_type} {pattern_name} {description} {test_strategy}"
        doc_id = self._generate_id(content)
        
        doc_metadata = {
            "game_type": game_type,
            "pattern_name": pattern_name,
            "success_rate": success_rate,
            "created_at": datetime.now().isoformat(),
            **(metadata or {})
        }
        
        if self.collection:
            self.collection.add(
                documents=[f"{description}\n\nTest Strategy: {test_strategy}"],
                metadatas=[doc_metadata],
                ids=[doc_id]
            )
        else:
            self.patterns.append({
                "id": doc_id,
                "content": content,
                "description": description,
                "test_strategy": test_strategy,
                "metadata": doc_metadata
            })
            self._save_patterns()
            
        return doc_id
        
    def add_test_result(
        self,
        game_url: str,
        test_case: Dict,
        result: str,
        execution_time: float,
        artifacts: Optional[Dict] = None
    ):
        """
        Add a test execution result for learning.
        
        Args:
            game_url: URL of the tested game
            test_case: The test case that was executed
            result: Result (PASS, FAIL, FLAKY)
            execution_time: Time taken to execute
            artifacts: References to artifacts
        """
        content = f"Test: {test_case.get('name', 'Unknown')} Result: {result}"
        doc_id = self._generate_id(f"{game_url}_{content}_{datetime.now().isoformat()}")
        
        doc_metadata = {
            "type": "test_result",
            "game_url": game_url,
            "test_name": test_case.get("name", "Unknown"),
            "result": result,
            "execution_time": execution_time,
            "created_at": datetime.now().isoformat()
        }
        
        if self.collection:
            self.collection.add(
                documents=[json.dumps(test_case)],
                metadatas=[doc_metadata],
                ids=[doc_id]
            )
        else:
            self.patterns.append({
                "id": doc_id,
                "type": "test_result",
                "test_case": test_case,
                "result": result,
                "metadata": doc_metadata
            })
            self._save_patterns()
            
    def search_patterns(
        self,
        query: str,
        game_type: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict]:
        """
        Search for relevant patterns.
        
        Args:
            query: Search query
            game_type: Optional filter by game type
            n_results: Number of results to return
            
        Returns:
            List of matching patterns
        """
        if self.collection:
            where_filter = {"game_type": game_type} if game_type else None
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            patterns = []
            for i, doc in enumerate(results.get("documents", [[]])[0]):
                patterns.append({
                    "content": doc,
                    "metadata": results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {},
                    "distance": results.get("distances", [[]])[0][i] if results.get("distances") else 0
                })
            return patterns
        else:
            # Simple text-based search
            query_lower = query.lower()
            matches = []
            for pattern in self.patterns:
                content = str(pattern.get("content", "") + str(pattern.get("description", ""))).lower()
                if query_lower in content or any(word in content for word in query_lower.split()):
                    matches.append(pattern)
                    if len(matches) >= n_results:
                        break
            return matches
            
    def get_successful_strategies(
        self,
        game_type: str,
        min_success_rate: float = 0.7
    ) -> List[Dict]:
        """
        Get strategies with high success rates.
        
        Args:
            game_type: Type of game
            min_success_rate: Minimum success rate threshold
            
        Returns:
            List of successful strategies
        """
        if self.collection:
            results = self.collection.query(
                query_texts=[f"{game_type} testing strategies"],
                n_results=20,
                where={"game_type": game_type}
            )
            
            strategies = []
            for i, meta in enumerate(results.get("metadatas", [[]])[0]):
                if meta.get("success_rate", 0) >= min_success_rate:
                    strategies.append({
                        "content": results.get("documents", [[]])[0][i],
                        "metadata": meta
                    })
            return strategies
        else:
            return [
                p for p in self.patterns
                if p.get("metadata", {}).get("game_type") == game_type
                and p.get("metadata", {}).get("success_rate", 0) >= min_success_rate
            ]
            
    def update_success_rate(self, pattern_id: str, new_rate: float):
        """
        Update the success rate of a pattern.
        
        Args:
            pattern_id: ID of the pattern
            new_rate: New success rate
        """
        if self.collection:
            try:
                # ChromaDB doesn't support direct updates, so we get and re-add
                results = self.collection.get(ids=[pattern_id])
                if results["ids"]:
                    metadata = results["metadatas"][0]
                    metadata["success_rate"] = new_rate
                    metadata["updated_at"] = datetime.now().isoformat()
                    
                    self.collection.update(
                        ids=[pattern_id],
                        metadatas=[metadata]
                    )
            except:
                pass
        else:
            for pattern in self.patterns:
                if pattern.get("id") == pattern_id:
                    pattern["metadata"]["success_rate"] = new_rate
                    pattern["metadata"]["updated_at"] = datetime.now().isoformat()
                    break
            self._save_patterns()
            
    def get_stats(self) -> Dict:
        """Get knowledge base statistics."""
        if self.collection:
            return {
                "total_patterns": self.collection.count(),
                "storage_type": "chromadb"
            }
        else:
            return {
                "total_patterns": len(self.patterns),
                "storage_type": "file"
            }
            
    def seed_default_patterns(self):
        """Seed the knowledge base with default game testing patterns."""
        default_patterns = [
            {
                "game_type": "puzzle",
                "pattern_name": "Number Matching",
                "description": "Games where players match numbers that sum to a target",
                "test_strategy": "Test valid matches (sum equals target), invalid matches (sum doesn't equal), edge cases (same number twice, empty selection)"
            },
            {
                "game_type": "puzzle",
                "pattern_name": "Grid Based Interaction",
                "description": "Games with grid-based tile or cell interactions",
                "test_strategy": "Test clicking each cell type, verify state changes, test adjacent cell interactions, test grid boundaries"
            },
            {
                "game_type": "math",
                "pattern_name": "Arithmetic Operations",
                "description": "Games involving basic math calculations",
                "test_strategy": "Test all operation types, boundary values (0, negatives, large numbers), verify score updates"
            },
            {
                "game_type": "ui",
                "pattern_name": "Game Controls",
                "description": "Standard game control elements",
                "test_strategy": "Test start/restart buttons, pause/resume, settings, score display updates"
            },
            {
                "game_type": "ui",
                "pattern_name": "Modal Dialogs",
                "description": "Popup dialogs for settings, game over, etc.",
                "test_strategy": "Test modal appearance, close behaviors, action buttons, overlay click handling"
            }
        ]
        
        for pattern in default_patterns:
            self.add_game_pattern(**pattern, success_rate=0.8)
