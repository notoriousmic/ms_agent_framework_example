"""Domain interfaces and abstract base classes."""

from .agent_interface import IAgent, IAgentFactory
from .conversation_repository_interface import IConversationRepository
from .repository_interface import IRepository
from .service_interface import IService
from .tool_interface import ITool, IToolProvider

__all__ = [
    "IAgent",
    "IAgentFactory",
    "ITool",
    "IToolProvider",
    "IService",
    "IRepository",
    "IConversationRepository",
]
