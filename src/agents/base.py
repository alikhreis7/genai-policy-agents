"""
Base agent class with common patterns.

All agents inherit from BaseAgent to ensure consistent:
- Logging and observability
- Error handling
- Structured output validation
- LLM client management
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic
import logging
from pydantic import BaseModel

from ..config import get_settings

# Generic type for agent output
T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC, Generic[T]):
    """
    Abstract base class for all agents in the system.
    
    Agents are specialized components that:
    1. Take structured input
    2. Perform a specific task (often involving LLM calls)
    3. Return structured, validated output
    
    This base class provides common functionality for:
    - Configuration management
    - Logging
    - Error handling
    - Output validation
    """
    
    def __init__(self, name: str):
        """
        Initialize the agent.
        
        Args:
            name: Human-readable name for logging and tracking
        """
        self.name = name
        self.settings = get_settings()
        self.logger = logging.getLogger(f"agent.{name}")
        self._call_count = 0
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of what this agent does."""
        pass
    
    @abstractmethod
    async def run(self, *args, **kwargs) -> T:
        """
        Execute the agent's main logic.
        
        Returns:
            Structured output of type T
        """
        pass
    
    def _log_start(self, input_summary: str) -> None:
        """Log the start of agent execution."""
        self._call_count += 1
        self.logger.info(
            f"[{self.name}] Starting execution #{self._call_count}: {input_summary}"
        )
    
    def _log_complete(self, output_summary: str) -> None:
        """Log successful completion."""
        self.logger.info(
            f"[{self.name}] Completed: {output_summary}"
        )
    
    def _log_error(self, error: Exception) -> None:
        """Log an error."""
        self.logger.error(
            f"[{self.name}] Error: {type(error).__name__}: {str(error)}"
        )
    
    def get_stats(self) -> dict[str, Any]:
        """Return execution statistics for this agent."""
        return {
            "name": self.name,
            "call_count": self._call_count,
        }


class LLMAgent(BaseAgent[T]):
    """
    Base class for agents that use LLM APIs.
    
    Provides:
    - OpenAI client setup
    - Gemini client setup (optional)
    - Structured output parsing
    - Retry logic for API calls
    """
    
    def __init__(self, name: str, use_openai: bool = True, use_gemini: bool = False):
        """
        Initialize the LLM agent.
        
        Args:
            name: Agent name
            use_openai: Whether to initialize OpenAI client
            use_gemini: Whether to initialize Gemini client
        """
        super().__init__(name)
        self._openai_client = None
        self._gemini_model = None
        self._use_openai = use_openai
        self._use_gemini = use_gemini
        
    @property
    def openai_client(self):
        """Lazy initialization of OpenAI client."""
        if self._openai_client is None and self._use_openai:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=self.settings.openai_api_key)
        return self._openai_client
    
    @property
    def gemini_model(self):
        """Lazy initialization of Gemini model."""
        if self._gemini_model is None and self._use_gemini:
            import google.generativeai as genai
            genai.configure(api_key=self.settings.google_api_key)
            self._gemini_model = genai.GenerativeModel(self.settings.gemini_model)
        return self._gemini_model
    
    def _call_openai_structured(
        self, 
        messages: list[dict], 
        response_model: type[BaseModel],
        temperature: float = 0.0
    ) -> BaseModel:
        """
        Call OpenAI API with structured output parsing.
        
        Args:
            messages: Chat messages
            response_model: Pydantic model for response parsing
            temperature: Sampling temperature
            
        Returns:
            Parsed response as Pydantic model
        """
        from openai import OpenAI
        
        client = self.openai_client
        
        # Use function calling for structured output
        response = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        
        # Parse the response
        content = response.choices[0].message.content
        import json
        data = json.loads(content)
        return response_model.model_validate(data)
    
    async def _call_openai_structured_async(
        self, 
        messages: list[dict], 
        response_model: type[BaseModel],
        temperature: float = 0.0
    ) -> BaseModel:
        """Async version of structured OpenAI call."""
        # For simplicity, using sync client in async context
        # In production, use AsyncOpenAI
        return self._call_openai_structured(messages, response_model, temperature)


class ToolAgent(LLMAgent[T]):
    """
    Agent that uses tools/function calling.
    
    Tools are defined as methods decorated with @tool or as
    structured tool definitions passed to the LLM.
    """
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        self._tools: list[dict] = []
    
    def register_tool(self, tool_def: dict) -> None:
        """Register a tool for this agent to use."""
        self._tools.append(tool_def)
    
    @property
    def tools(self) -> list[dict]:
        """Return registered tools."""
        return self._tools
