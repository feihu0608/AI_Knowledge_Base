from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    name: str
    version: str
    prompt_version: str
    output_schema: type[BaseModel]
    tool_allowlist: frozenset[str] = field(default_factory=frozenset)
    max_model_calls: int = 2
    timeout_seconds: int = 30


@dataclass(frozen=True, slots=True)
class AgentResult:
    agent_name: str
    agent_version: str
    provider_mode: str
    output: BaseModel


ModelInvoker = Callable[[AgentDefinition, dict[str, Any]], dict[str, Any]]

