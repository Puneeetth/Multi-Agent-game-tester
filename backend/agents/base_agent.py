"""
Base Agent - Abstract base class for all agents in the system
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Provides common functionality and interface definition.
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize the base agent.
        
        Args:
            name: Unique name for the agent
            description: Description of the agent's purpose
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"agent.{name}")
        
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's main task.
        
        Args:
            context: Dictionary containing all necessary context for execution
            
        Returns:
            Dictionary containing the results of execution
        """
        pass
    
    def log_info(self, message: str):
        """Log an info message"""
        self.logger.info(f"[{self.name}] {message}")
    
    def log_error(self, message: str):
        """Log an error message"""
        self.logger.error(f"[{self.name}] {message}")
    
    def log_debug(self, message: str):
        """Log a debug message"""
        self.logger.debug(f"[{self.name}] {message}")
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.name}')>"
