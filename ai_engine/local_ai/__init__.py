"""
Local engineering AI package.
"""

from ai_engine.local_ai.analysis_result import (
    EngineeringAnalysisResult,
    EngineeringConflict,
    EngineeringProposal,
)
from ai_engine.local_ai.engineering_agent import (
    EngineeringAgent,
    EngineeringAgentError,
)
from ai_engine.local_ai.ollama_client import (
    OllamaClient,
    OllamaResponse,
)


__all__ = [
    "EngineeringAgent",
    "EngineeringAgentError",
    "EngineeringAnalysisResult",
    "EngineeringConflict",
    "EngineeringProposal",
    "OllamaClient",
    "OllamaResponse",
]